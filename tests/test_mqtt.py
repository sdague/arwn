#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_mqtt
----------------------------------

Tests for MQTT functionality using a simple test broker.
These tests use a SimpleMQTTBroker that implements basic MQTT protocol
without requiring an external mosquitto instance.
"""

import time

import paho.mqtt.client as mqtt
import pytest

from arwn import engine
from tests.mqtt_broker import SimpleMQTTBroker


@pytest.fixture
def mqtt_broker():
    """Create a simple MQTT broker for testing."""
    broker = SimpleMQTTBroker()
    broker.start()
    yield broker
    broker.stop()


def test_mqtt_basic_connection(mqtt_broker):
    """Test basic MQTT connection with real client and test broker."""
    connected = False

    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        connected = True

    # Create client and connect
    client = mqtt.Client()
    client.on_connect = on_connect

    # Connect client
    client.connect("localhost", mqtt_broker.port)
    client.loop_start()

    # Wait for connection
    timeout = 2
    start = time.time()
    while not connected and (time.time() - start) < timeout:
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()

    assert connected, "Client did not connect to broker"


def test_mqtt_engine_initialization(mqtt_broker):
    """Test MQTT engine initialization with test broker."""
    config = dict(mqtt={})

    # Create MQTT engine
    mq = engine.MQTT("localhost", config, port=mqtt_broker.port)

    # Start client loop to allow connection
    mq.client.loop_start()
    time.sleep(0.3)

    # Verify engine was created
    assert mq is not None
    assert mq.client is not None
    assert mq.root == "arwn"

    mq.client.loop_stop()
    mq.client.disconnect()


def test_mqtt_engine_send(mqtt_broker):
    """Test MQTT engine send method."""
    config = dict(mqtt={})

    # Create MQTT engine
    mq = engine.MQTT("localhost", config, port=mqtt_broker.port)

    # Start client loop
    mq.client.loop_start()
    time.sleep(0.3)

    # Send a message (just verify it doesn't crash)
    mq.send("test/topic", {"value": 42})
    time.sleep(0.2)

    mq.client.loop_stop()
    mq.client.disconnect()


def test_mqtt_status_messages(mqtt_broker):
    """Test MQTT status topic configuration."""
    config = dict(mqtt={})

    # Create MQTT engine
    mq = engine.MQTT("localhost", config, port=mqtt_broker.port)

    # Verify status topic is set correctly
    assert mq.root == "arwn"
    status_topic = f"{mq.root}/status"
    assert status_topic == "arwn/status"


def test_mqtt_connection_lifecycle(mqtt_broker):
    """Test MQTT connection lifecycle (connect, verify, disconnect)."""
    config = dict(mqtt={})
    mq = engine.MQTT("localhost", config, port=mqtt_broker.port)

    # Start MQTT engine
    mq.client.loop_start()
    time.sleep(0.5)

    # Verify client is connected
    assert mq.client.is_connected()

    # Disconnect
    mq.client.loop_stop()
    mq.client.disconnect()
    time.sleep(0.2)

    # Verify disconnected
    assert not mq.client.is_connected()
