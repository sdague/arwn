
import datetime
import logging
import re

logger = logging.getLogger()

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


def setup():
    global HANDLERS
    HANDLERS = [
        RecordRainTotal(),
        UpdateTodayRain(),
        InitializeLastRainIfNotThere(),
        ComputeRainTotal()
    ]


def run(client, topic, payload):
    global HANDLERS
    for h in HANDLERS:
        h.run(client, topic, payload)
