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

import urllib.parse as urllib
import urllib.request as request

import arwn

logger = logging.getLogger(__name__)

LAST_RAIN_TOTAL = None
LAST_RAIN = None
PREV_RAIN = None
HANDLERS = []

"""Handlers are a way to put statefullness and logic into the MQTT bus
itself. ARWN monitors the root topic, and can react to messages to do
more complex logic. We use this to do things like report to weather
underground, or to do the rain totals calculations."""

# How rain since midnight should work.
#
# 1. when a rain packet comes in, if it still in the same day,
# LAST_RAIN == current total.
#
# 2. if its past midnight, update the LAST_RAIN_TOTAL to what
# LAST_RAIN was.
#
# 3. Set LAST_RAIN to new rain.


class MQTTAction(object):
    regex = None

    def action(self, topic, payload):
        pass

    def run(self, client, topic, payload):
        if self.regex and re.search(self.regex, topic):
            try:
                self.action(client, topic, payload)
            except Exception as e:
                logger.error(e)


class RecordRainTotal(MQTTAction):
    regex = r"^\w+/totals/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN_TOTAL
        LAST_RAIN_TOTAL = payload


class UpdateTodayRain(MQTTAction):
    regex = r"^\w+/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN, PREV_RAIN
        PREV_RAIN = LAST_RAIN or payload
        LAST_RAIN = payload


class InitializeLastRainIfNotThere(MQTTAction):
    regex = r"^\w+/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN_TOTAL
        if not LAST_RAIN_TOTAL:
            client.send("totals/rain", payload, retain=True)


class ComputeRainTotal(MQTTAction):
    regex = r"^\w+/"
    ts = None
    topic = None

    def is_rollover(self, ts):
        # the last day we're keeping state for
        global LAST_RAIN_TOTAL
        return not self.is_sameday(ts, LAST_RAIN_TOTAL['timestamp'])

    def is_sameday(self, ts1, ts2):
        d1 = datetime.datetime.fromtimestamp(ts1).strftime('%j')
        d2 = datetime.datetime.fromtimestamp(ts2).strftime('%j')
        delta_days = (int(d1) - int(d2))
        return delta_days == 0

    def should_proceed(self, topic, payload):
        # don't retrigger on our own topic that we know we are sending
        # on.
        if re.search("rain/today", topic) or re.search("totals/rain", topic):
            return False

        # we do want to trigger on any timestamped message
        ts = payload.get('timestamp')
        if not ts:
            return False

        global LAST_RAIN_TOTAL
        global PREV_RAIN
        if not PREV_RAIN or not LAST_RAIN_TOTAL:
            return False
        return True

    def yesterdays_totals(self):
        global PREV_RAIN, LAST_RAIN, LAST_RAIN_TOTAL
        if self.is_sameday(LAST_RAIN_TOTAL['timestamp'],
                           LAST_RAIN['timestamp']):
            total = LAST_RAIN
        else:
            total = PREV_RAIN
        return total.copy()

    def action(self, client, topic, payload):

        if not self.should_proceed(topic, payload):
            return

        global PREV_RAIN, LAST_RAIN, LAST_RAIN_TOTAL

        ts = payload.get('timestamp')
        if self.is_rollover(ts):
            print("Rollover event!")
            # we need to emit yesterday's updated totals
            totals = self.yesterdays_totals()
            totals['timestamp'] = ts
            client.send("totals/rain", totals, retain=True)

            delta_rain = LAST_RAIN["total"] - totals["total"]
            if delta_rain < 0:
                delta_rain = 0

            since_midnight = {
                "timestamp": ts,
                "since_midnight": round(delta_rain, 3)}
            client.send("rain/today", since_midnight)


class TodaysRain(MQTTAction):
    regex = r"^\w+/rain$"

    def action(self, client, topic, payload):
        global LAST_RAIN_TOTAL

        delta_rain = payload["total"] - LAST_RAIN_TOTAL["total"]
        if delta_rain < 0:
            delta_rain = 0
        since_midnight = {
            "timestamp": payload["timestamp"],
            "since_midnight": round(delta_rain, 3)}
        client.send("rain/today", since_midnight)


class WeatherUnderground(MQTTAction):
    regex = r"^\w+/(wind|temperature/Outside|rain/today|barometer)$"
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
                self.windgust is not None)  # noqa

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
            'software': 'arwn %s' % (arwn.__version__),
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
        resp = request.urlopen("%s?%s" % (BASEURL, params))
        logger.info("Reported to WUnderground: %(tempf)sF / %(dewptf)sF - "
                    "%(baromin)sinhg - %(dailyrainin)sin - "
                    "%(windgustmph)smph / %(windspeedmph)smph %(winddir)s",
                    data)

        if resp.getcode() != 200:
            logger.error("Failed to upload to wunderground: %s - %s" %
                         (params, resp.info()))

    def __repr__(self):
        return ("Wunderground((temp: %s, dewpoint: %s, rain: %s "
                "pressure: %s, winddir: %s, windspeed: %s, windgust: %s))" %
                (self.temp, self.dewpoint, self.rain, self.pressure,
                 self.winddir, self.windspeed, self.windgust))


def setup():
    global LAST_RAIN_TOTAL, LAST_RAIN, PREV_RAIN, HANDLERS
    LAST_RAIN_TOTAL = None  # noqa
    LAST_RAIN = None  # noqa
    PREV_RAIN = None  # noqa
    HANDLERS = [
        RecordRainTotal(),
        UpdateTodayRain(),
        InitializeLastRainIfNotThere(),
        ComputeRainTotal(),
        TodaysRain(),
        WeatherUnderground()
    ]


def run(client, topic, payload):
    global HANDLERS
    for h in HANDLERS:
        h.run(client, topic, payload)
