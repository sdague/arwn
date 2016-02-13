#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import sys
import unittest

import paho.mqtt.client as mqtt
import testtools

from . import arwn_fixtures


class TestMqttSpawn(testtools.TestCase):

    def test_mqtt_fixture(self):
        try:
            mos = arwn_fixtures.MosquittoReal()
            self.useFixture(mos)
        except arwn_fixtures.MosquittoSetupFail:
            self.skipTest("Can't start mosquitto")
        client = mqtt.Client()
        client.connect("localhost", mos.port)
        client.publish("foo/start", "foo")


if __name__ == '__main__':
    sys.exit(unittest.main())
