import logging
import re
import urllib.parse as urllib
import urllib.request as request

import arwn
from arwn.rain import RainAccumulator, RainEventTracker, RainStateStore

logger = logging.getLogger(__name__)

HANDLERS = []
_rain_accumulator = None
_rain_event_tracker = None


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


class WeatherUnderground(MQTTAction):
    regex = r"^\w+/(wind|temperature/Outside|rain/today|barometer)$"
    temp = None
    dewpoint = None
    rain = 0
    pressure = None
    winddir = 0
    windspeed = 0
    windgust = 0

    def is_ready(self):
        return (
            self.temp is not None
            and self.dewpoint is not None
            and self.rain is not None
            and self.winddir is not None
            and self.windspeed is not None
            and self.windgust is not None
        )

    def action(self, client, topic, payload):
        if "wind" in topic:
            self.winddir = payload["direction"]
            self.windspeed = payload["speed"]
            self.windgust = payload["gust"]
        if "temperature" in topic:
            self.temp = payload["temp"]
            self.dewpoint = payload["dewpoint"]
            self.humid = payload["humid"]
        if "barometer" in topic:
            self.pressure = payload["pressure"]
        if "rain" in topic:
            self.rain = payload["since_midnight"]

        if self.is_ready():
            self.send_to_wunderground(client)
        else:
            logger.info("Wunderground not ready yet: %s" % self)

    def send_to_wunderground(self, client):
        hpa2inhg = 0.0295301
        BASEURL = (
            "http://weatherstation.wunderground.com/"
            "weatherstation/updateweatherstation.php"
        )
        data = {
            "ID": client.config["wunderground"]["station"],
            "PASSWORD": client.config["wunderground"]["passwd"],
            "dateutc": "now",
            "action": "updateraw",
            "software": "arwn %s" % (arwn.__version__),
            "tempf": self.temp,
            "dewptf": self.dewpoint,
            "humidity": self.humid,
            "dailyrainin": self.rain,
            "winddir": self.winddir,
            "windspeedmph": self.windspeed,
            "windgustmph": self.windgust,
        }

        if self.pressure:
            data["baromin"] = self.pressure * hpa2inhg

        params = urllib.urlencode(data)
        resp = request.urlopen("%s?%s" % (BASEURL, params))
        logger.info(
            "Reported to WUnderground: %(tempf)sF / %(dewptf)sF - "
            "%(dailyrainin)sin - "
            "%(windgustmph)smph / %(windspeedmph)smph %(winddir)s",
            data,
        )

        if resp.getcode() != 200:
            logger.error(
                "Failed to upload to wunderground: %s - %s" % (params, resp.info())
            )

    def __repr__(self):
        return (
            "Wunderground((temp: %s, dewpoint: %s, rain: %s "
            "pressure: %s, winddir: %s, windspeed: %s, windgust: %s))"
            % (
                self.temp,
                self.dewpoint,
                self.rain,
                self.pressure,
                self.winddir,
                self.windspeed,
                self.windgust,
            )
        )


def setup(state_path=None):
    global HANDLERS, _rain_accumulator, _rain_event_tracker
    store = RainStateStore(path=state_path)
    _rain_accumulator = RainAccumulator(store)
    _rain_event_tracker = RainEventTracker(store)
    HANDLERS = [_rain_accumulator, _rain_event_tracker, WeatherUnderground()]


def run(client, topic, payload):
    global HANDLERS
    for h in HANDLERS:
        h.run(client, topic, payload)
