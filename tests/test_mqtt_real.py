#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_mqtt_real
----------------------------------

Tests for MQTT connection lifecycle and disconnect/reconnect behavior.
Previously relied on an external mosquitto process; now uses SimpleMQTTBroker.
"""

import json
import socket
import time

import paho.mqtt.client as mqtt
import pytest

from arwn import engine
from tests.conftest import wait_for_message


def test_mqtt_fixture(sim_broker, sim_broker_clean):
    """Test MQTT pub/sub round-trip via SimpleMQTTBroker."""
    connected = False
    received = None
    done = False

    def on_connect(client, userdata, connect_flags, reason_code, properties):
        client.subscribe("foo/#")
        nonlocal connected
        connected = True

    def on_message(client, userdata, message):
        nonlocal received, done
        received = message
        done = True

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(sim_broker.host, sim_broker.port)
    client.loop_start()

    # Wait for connection before publishing
    start = time.time()
    while not connected and (time.time() - start) < 5:
        time.sleep(0.1)

    client.publish("foo/start", "foo", retain=True)

    # Wait for message with timeout
    timeout = 5
    start = time.time()
    while not done and (time.time() - start) < timeout:
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()

    assert connected, "Did not seem to connect"
    assert received is not None, "Did not receive message"
    assert received.payload.decode(encoding="UTF-8") == "foo"
    assert received.topic == "foo/start"


def test_mqtt_disconnect(sim_broker, sim_broker_clean):
    """Test MQTT disconnect and reconnect behavior of the engine MQTT class.

    Verifies the lifecycle: alive (initial connect) → dead (will on unclean
    disconnect) → alive (reconnect publishes status again).
    """
    received = []

    config = dict(mqtt={})
    mq = engine.MQTT(sim_broker.host, config, port=sim_broker.port)

    def on_connect(client, userdata, connect_flags, reason_code, properties):
        client.subscribe("%s/#" % mq.root, qos=2)

    def on_message(client, userdata, message):
        received.append(
            {message.topic: json.loads(message.payload.decode(encoding="UTF-8"))}
        )

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(sim_broker.host, sim_broker.port)
    client.loop_start()

    # Wait for the engine client to connect before force-closing its socket.
    start = time.time()
    while not mq.client.is_connected() and (time.time() - start) < 5:
        time.sleep(0.1)

    # Wait for the initial "alive" to arrive before simulating the crash.
    wait_for_message(sim_broker.broker, "%s/status" % mq.root, timeout=2.0)

    # Force an unclean disconnect so the broker fires the will.
    # Shut down the socket BEFORE stopping paho's loop so paho cannot send
    # a clean DISCONNECT (which would suppress the will on the broker side).
    try:
        mq.client._sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    mq.client.loop_stop()

    # Wait for the broker to deliver the will ("dead") before reconnecting.
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if len(received) >= 2:
            break
        time.sleep(0.05)

    # Reconnect: fresh TCP connection → broker processes CONNECT and paho's
    # on_connect fires, publishing status=alive again.
    mq.client.connect(sim_broker.host, sim_broker.port)
    mq.client.loop_start()

    # Wait for the third message (alive after reconnect).
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if len(received) >= 3:
            break
        time.sleep(0.05)

    client.loop_stop()
    client.disconnect()
    mq.client.loop_stop()
    mq.client.disconnect()

    assert len(received) == 3, received

    assert received[0]["%s/status" % mq.root]["status"] == "alive", received[0]
    assert received[1]["%s/status" % mq.root]["status"] == "dead", received[1]
    assert received[2]["%s/status" % mq.root]["status"] == "alive", received[2]
