#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import json
import sys
import time
import unittest

import paho.mqtt.client as mqtt
import testtools

import arwn
from . import arwn_fixtures


class TestMqttSpawn(testtools.TestCase):

    def test_mqtt_fixture(self):
        self.connected = False
        self.received = ""
        self.done = False

        def on_connect(client, userdata, flags, rc):
            client.subscribe("foo/#")
            self.connected = True

        def on_message(client, userdata, message):
            self.received = message
            self.done = True

        try:
            mos = arwn_fixtures.MosquittoReal()
            self.useFixture(mos)
        except arwn_fixtures.MosquittoSetupFail:
            self.skipTest("Can't start mosquitto")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect("localhost", mos.port)
        client.loop_start()
        client.publish("foo/start", "foo", retain=True)
        while not self.done:
            # forces a flush of all messages
            time.sleep(0.1)
            client.loop_read()
        self.assertTrue(self.connected, "Did not seem to connect")
        self.assertEqual("foo", self.received.payload.decode(encoding='UTF-8'))
        self.assertEqual("foo/start", self.received.topic)


class TestMQTTLifecycle(testtools.TestCase):

    def test_mqtt_disconnect(self):
        self.received = []
        try:
            mos = arwn_fixtures.MosquittoReal()
            self.useFixture(mos)
        except arwn_fixtures.MosquittoSetupFail:
            self.skipTest("Can't start mosquitto")

        mq = arwn.engine.MQTT('localhost', mos.port)

        def on_connect(client, userdata, flags, rc):
            client.subscribe("%s/#" % mq.root, qos=2)

        def on_message(client, userdata, message):
            self.received.append(
                {message.topic:
                 json.loads(message.payload.decode(encoding='UTF-8'))})
            print("Got a message!")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect("localhost", mos.port)
        client.loop_start()
        # force a failure, this triggers the will. We have to force a
        # sleep before the socket close otherwise the will can
        # actually process as the first message because of the lack of
        # order guaruntees.
        time.sleep(0.1)
        mq.client.socket().close()
        mq.client.reconnect()
        time.sleep(0.1)

        self.assertEqual(3, len(self.received), self.received)

        self.assertEqual(
            self.received[0]["%s/status" % mq.root]['status'],
            'alive',
            self.received[0]
        )
        self.assertEqual(
            self.received[1]["%s/status" % mq.root]['status'],
            'dead',
            self.received[1]
        )
        self.assertEqual(
            self.received[2]["%s/status" % mq.root]['status'],
            'alive',
            self.received[2]
        )


if __name__ == '__main__':
    sys.exit(unittest.main())
