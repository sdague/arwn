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

import datetime
import logging
import re

import six.moves.urllib.parse as urllib
import six.moves.urllib.request as request

logger = logging.getLogger(__name__)

LAST_RAIN_TOTAL = None
LAST_RAIN = None
HANDLERS = []


class MQTTAction(object):
    regex = None

    def action(self, topic, payload):
        pass

    def run(self, client, topic, payload):
        if self.regex and re.search(self.regex, topic):
            try:
                logger.debug("Running handler %s" % self)
                self.action(client, topic, payload)
            except Exception as e:
                logger.error(e)


class RecordRainTotal(MQTTAction):
    regex = "^\w+/totals/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN_TOTAL
        LAST_RAIN_TOTAL = payload


class UpdateTodayRain(MQTTAction):
    regex = "^\w+/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN
        LAST_RAIN = payload


class InitializeLastRainIfNotThere(MQTTAction):
    regex = "^\w+/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN_TOTAL
        if not LAST_RAIN_TOTAL:
            client.send("totals/rain", payload, retain=True)


class ComputeRainTotal(MQTTAction):
    regex = "^\w+/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN_TOTAL
        global LAST_RAIN
        if not LAST_RAIN or not LAST_RAIN_TOTAL:
            return

        lastr = LAST_RAIN_TOTAL
        last_day = datetime.datetime.fromtimestamp(
            lastr['timestamp']).strftime('%j')
        newr = payload
        today = datetime.datetime.fromtimestamp(
            newr['timestamp']).strftime('%j')
        delta_days = (int(today) - int(last_day))

        if delta_days > 1 or delta_days < -300:
            client.send("totals/rain", LAST_RAIN, retain=True)

        since_midnight = {
            "timestamp": newr["timestamp"],
            "since_midnight": newr["total"] - lastr["total"]}
        client.send("rain/today", since_midnight)


class WeatherUnderground(MQTTAction):
    regex = "^\w+/(wind|temperature/Outside|rain/today|barometer)$"
    temp = None
    dewpoint = None
    rain = None
    pressure = None
    winddir = None
    windspeed = None
    windgust = None

    def is_ready(self):
        return (self.temp is not None and
                self.dewpoint is not None and
                self.rain is not None and
                self.pressure is not None and
                self.winddir is not None and
                self.windspeed is not None and
                self.windgust is not None)

    def action(self, client, topic, payload):
        if 'wind' in topic:
            self.winddir = payload['direction']
            self.windspeed = payload['speed']
            self.windgust = payload['gust']
        if 'temperature' in topic:
            self.temp = payload['temp']
            self.dewpoint = payload['dewpoint']
            self.humid = payload['humid']
        if 'barometer' in topic:
            self.pressure = payload['pressure']
        if 'rain' in topic:
            self.rain = payload['since_midnight']

        if self.is_ready():
            self.send_to_wunderground(client)
        else:
            logger.info("Wunderground not ready yet: %s" % self)

    def send_to_wunderground(self, client):
        hpa2inhg = 0.0295301
        BASEURL = "http://weatherstation.wunderground.com/" \
                  "weatherstation/updateweatherstation.php"
        data = {
            'ID': client.config['wunderground']['station'],
            'PASSWORD': client.config['wunderground']['passwd'],
            'dateutc': 'now',
            'action': 'updateraw',
            'software': 'pyhome 0.1',
            'tempf': self.temp,
            'dewptf': self.dewpoint,
            'humidity': self.humid,
            'dailyrainin': self.rain,
            'baromin': self.pressure * hpa2inhg,
            'winddir': self.winddir,
            'windspeedmph': self.windspeed,
            'windgustmph': self.windgust
        }

        params = urllib.urlencode(data)
        # print data
        resp = request.urlopen("%s?%s" % (BASEURL, params))
        if resp.getcode() != 200:
            logger.error("Failed to upload to wunderground: %s - %s" %
                         (params, resp.info()))

    def __repr__(self):
        return ("Wunderground((temp: %s, dewpoint: %s, rain: %s "
                "pressure: %s, winddir: %s, windspeed: %s, windgust: %s))" %
                (self.temp, self.dewpoint, self.rain, self.pressure,
                 self.winddir, self.windspeed, self.windgust))


def setup():
    global HANDLERS
    HANDLERS = [
        RecordRainTotal(),
        UpdateTodayRain(),
        InitializeLastRainIfNotThere(),
        ComputeRainTotal(),
        WeatherUnderground()
    ]


def run(client, topic, payload):
    global HANDLERS
    for h in HANDLERS:
        h.run(client, topic, payload)
