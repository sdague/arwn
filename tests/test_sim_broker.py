"""Unit tests for SimpleMQTTBroker enhancements."""

import json
import time

import paho.mqtt.client as mqtt
import pytest

from tests.mqtt_broker import SimpleMQTTBroker


@pytest.fixture
def broker():
    b = SimpleMQTTBroker()
    b.start()
    yield b
    b.stop()


def connect_client(port):
    """Return a connected, looping paho client."""
    c = mqtt.Client()
    c.connect("localhost", port)
    c.loop_start()
    time.sleep(0.15)
    return c


def test_retained_message_stored(broker):
    """Publishing with retain=True stores payload in broker.retained."""
    c = connect_client(broker.port)
    c.publish("arwn/status", json.dumps({"status": "alive"}), retain=True)
    time.sleep(0.2)
    c.loop_stop()
    c.disconnect()

    assert "arwn/status" in broker.retained
    payload = json.loads(broker.retained["arwn/status"])
    assert payload["status"] == "alive"


def test_retained_message_replayed_on_subscribe(broker):
    """A subscriber receives retained messages immediately on subscribe."""
    # Publish retained before subscriber connects
    pub = connect_client(broker.port)
    pub.publish("arwn/totals/rain", json.dumps({"total": 1.5}), retain=True)
    time.sleep(0.2)
    pub.loop_stop()
    pub.disconnect()

    received = []

    def on_message(client, userdata, msg):
        received.append((msg.topic, json.loads(msg.payload)))

    sub = mqtt.Client()
    sub.on_message = on_message
    sub.connect("localhost", broker.port)
    sub.subscribe("arwn/#")
    sub.loop_start()
    time.sleep(0.3)
    sub.loop_stop()
    sub.disconnect()

    assert any(
        t == "arwn/totals/rain" for t, _ in received
    ), f"Retained message not replayed. Received: {received}"


def test_empty_retained_clears_topic(broker):
    """Publishing empty payload with retain=True removes the stored message."""
    c = connect_client(broker.port)
    c.publish("arwn/status", json.dumps({"status": "alive"}), retain=True)
    time.sleep(0.15)
    c.publish("arwn/status", b"", retain=True)
    time.sleep(0.15)
    c.loop_stop()
    c.disconnect()

    assert "arwn/status" not in broker.retained


def test_will_published_on_unclean_disconnect(broker):
    """Will message is published when client socket is force-closed."""
    import socket as _socket

    will_received = []

    # Observer subscribes to arwn/status before the will fires
    obs = mqtt.Client()
    obs.on_message = lambda c, u, m: will_received.append(
        (m.topic, json.loads(m.payload))
    )
    obs.connect("localhost", broker.port)
    obs.subscribe("arwn/#")
    obs.loop_start()
    time.sleep(0.15)

    # Connect a client with a will
    victim = mqtt.Client()
    victim.will_set("arwn/status", json.dumps({"status": "dead"}), retain=True)
    victim.connect("localhost", broker.port)
    victim.loop_start()
    time.sleep(0.15)

    # Force-close without DISCONNECT: shut down socket first, then stop loop
    try:
        victim._sock.shutdown(_socket.SHUT_RDWR)
    except Exception:
        pass
    try:
        victim._sock.close()
    except Exception:
        pass
    victim.loop_stop()

    time.sleep(0.5)

    obs.loop_stop()
    obs.disconnect()

    assert any(
        t == "arwn/status" and p.get("status") == "dead" for t, p in will_received
    ), f"Will not received. Got: {will_received}"
    assert "arwn/status" in broker.retained


def test_will_not_published_on_clean_disconnect(broker):
    """Will message is NOT published when client disconnects cleanly."""
    c = mqtt.Client()
    c.will_set("arwn/status", json.dumps({"status": "dead"}), retain=True)
    c.connect("localhost", broker.port)
    c.loop_start()
    time.sleep(0.15)
    c.disconnect()  # clean disconnect
    time.sleep(0.3)

    assert "arwn/status" not in broker.retained
