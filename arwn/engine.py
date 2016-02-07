# Copyright 2016 Sean Dague
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import logging
import time

import paho.mqtt.client as paho

from arwn import temperature
from arwn.vendor.RFXtrx import lowlevel as ll
from arwn.vendor.RFXtrx.pyserial import PySerialTransport

logger = logging.getLogger()


# Utility functions for making the code easier to read below
def is_temp_sensor(packet):
    return (isinstance(packet, ll.TempHumid) or
            isinstance(packet, ll.TempHumidBaro))


def is_barometer(packet):
    return isinstance(packet, ll.TempHumidBaro)


def is_rainguage(packet):
    return isinstance(packet, ll.RainGauge)


def is_wind(packet):
    return isinstance(packet, ll.Wind)


class MQTT(object):
    def __init__(self, server):
        client = paho.Client()
        # client.on_connect = on_connect
        # client.on_message = on_message
        client.connect(server, 1883)
        client.loop_start()
        self.client = client
        self.root = "arwn2"

    def _base_packet(self, packet):
        payload = dict(
            timestamp=int(time.time()),
            bat=packet.battery,
            sig=packet.rssi,
            sensor_id=packet.id_string)
        return payload

    def send(self, topic, payload):
        topic = "%s/%s" % (self.root, topic)
        self.client.publish(topic, json.dumps(payload))

    def temperature(self, name, packet):
        temp = temperature.Temperature("%sC" % packet.temp).as_F()
        topic = "temperature/%s" % name
        data = self._base_packet(packet)
        data['temp'] = round(temp.to_F(), 1)
        data['dewpoint'] = round(temp.dewpoint(packet.humidity), 1)
        data['units'] = 'F'
        self.send(topic, data)

    def wind(self, packet):
        mps2mph = 2.23694
        speed = round(float(packet.average_speed) * mps2mph, 1)
        gust = round(float(packet.gust) * mps2mph, 1)
        topic = "wind"
        data = self._base_packet(packet)
        data['direction'] = packet.direction
        data['speed'] = speed
        data['gust'] = gust
        data['units'] = 'mph'
        self.send(topic, data)

    def rain(self, packet):
        topic = "rain"
        data = self._base_packet(packet)
        data['total'] = round(packet.raintotal / 25.4, 2)
        data['rate'] = round(packet.rainrate / 25.4, 2)
        data['units'] = 'in'
        self.send(topic, data)

    def barometer(self, packet):
        topic = "barometer"
        data = self._base_packet(packet)
        data['pressure'] = packet.baro
        data['units'] = 'mbar'
        self.send(topic, data)

    def unknown(self, packet):
        topic = "unknown/%s" % packet.id_string
        data = self._base_packet(packet)
        data['dump'] = str(packet)
        self.send(topic, data)


class Dispatcher(object):
    def __init__(self, device, names, server):
        self.transport = PySerialTransport(device, debug=True)
        self.transport.reset()
        self.names = names
        self.mqtt = MQTT(server)

    def loopforever(self):
        while True:
            event = self.transport.receive_blocking()
            logger.debug(event)

            if event is None:
                continue
            packet = event.device.pkt

            if is_temp_sensor(packet):
                name = self.names.get(packet.id_string)
                if name:
                    self.mqtt.temperature(name, packet)
                else:
                    # report unlabeled temp sensors
                    self.mqtt.unknown(packet)

            if is_barometer(packet):
                self.mqtt.barometer(packet)

            if is_wind(packet):
                self.mqtt.wind(packet)

            if is_rainguage(packet):
                self.mqtt.rain(packet)
