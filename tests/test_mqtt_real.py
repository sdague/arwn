#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import json
import time

import paho.mqtt.client as mqtt
import pytest

from arwn import engine


def test_mqtt_fixture(mosquitto_real):
    """Test MQTT fixture with real mosquitto broker."""
    connected = False
    received = None
    done = False

    def on_connect(client, userdata, flags, rc):
        client.subscribe("foo/#")
        nonlocal connected
        connected = True

    def on_message(client, userdata, message):
        nonlocal received, done
        received = message
        done = True

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", mosquitto_real)
    client.loop_start()
    client.publish("foo/start", "foo", retain=True)

    # Wait for message with timeout
    timeout = 5
    start = time.time()
    while not done and (time.time() - start) < timeout:
        time.sleep(0.1)
        client.loop_read()

    client.loop_stop()
    client.disconnect()

    assert connected, "Did not seem to connect"
    assert received is not None, "Did not receive message"
    assert received.payload.decode(encoding="UTF-8") == "foo"
    assert received.topic == "foo/start"


def test_mqtt_disconnect(mosquitto_real):
    """Test MQTT disconnect and reconnect behavior."""
    received = []

    config = dict(mqtt={})
    mq = engine.MQTT("localhost", config, port=mosquitto_real)

    def on_connect(client, userdata, flags, rc):
        client.subscribe("%s/#" % mq.root, qos=2)

    def on_message(client, userdata, message):
        received.append(
            {message.topic: json.loads(message.payload.decode(encoding="UTF-8"))}
        )
        print("Got a message!")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", mosquitto_real)
    client.loop_start()

    # force a failure, this triggers the will. We have to force a
    # sleep before the socket close otherwise the will can
    # actually process as the first message because of the lack of
    # order guaruntees.
    time.sleep(0.1)
    mq.client.socket().close()
    mq.client.reconnect()
    time.sleep(0.1)

    client.loop_stop()
    client.disconnect()

    assert len(received) == 3, received

    assert received[0]["%s/status" % mq.root]["status"] == "alive", received[0]
    assert received[1]["%s/status" % mq.root]["status"] == "dead", received[1]
    assert received[2]["%s/status" % mq.root]["status"] == "alive", received[2]
