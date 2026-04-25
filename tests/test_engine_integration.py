"""Integration tests: engine <-> SimpleMQTTBroker roundtrip."""

import json
import socket
import time

import pytest

from arwn import engine, handlers
from tests.conftest import wait_for_message


def make_config(port):
    return {
        "mqtt": {"server": "localhost", "port": port},
        "names": {},
        "collector": {"type": "rfxcom", "device": "/dev/null"},
    }


def test_status_alive_published_with_retain(sim_broker, sim_broker_clean):
    """engine.MQTT publishes arwn/status with retain=True on connect."""
    handlers.setup()
    mq = engine.MQTT("localhost", make_config(sim_broker.port), port=sim_broker.port)
    try:
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        assert "arwn/status" in sim_broker.broker.retained
        payload = json.loads(sim_broker.broker.retained["arwn/status"])
        assert payload["status"] == "alive"
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()


def test_will_published_on_unclean_disconnect(sim_broker, sim_broker_clean):
    """Will message arwn/status=dead is published when engine socket is force-closed."""
    handlers.setup()
    mq = engine.MQTT("localhost", make_config(sim_broker.port), port=sim_broker.port)

    # Wait for initial status=alive
    wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
    sim_broker.broker.messages.clear()

    # Force-close without DISCONNECT
    mq.client.loop_stop()
    try:
        mq.client._sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    try:
        mq.client._sock.close()
    except Exception:
        pass

    # Broker should detect EOF and fire the will
    wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
    payload = json.loads(sim_broker.broker.retained["arwn/status"])
    assert payload["status"] == "dead"
