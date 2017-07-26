#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import datetime
import mock
import time
import unittest

from arwn import engine  # noqa
from arwn import handlers  # noqa


class FakeClient(object):
    def __init__(self):
        super(FakeClient, self).__init__()
        self.log = []

    def send(self, topic, payload, retain=False):
        self.log.append([topic, payload])
        handlers.run(self, "arwn/" + topic, payload)


def mktime(year=1970, mon=1, day=1, hour=0, minute=0, sec=0):
    epoch = datetime.datetime(1970, 1, 1)
    now = datetime.datetime(year, mon, day, hour, minute, sec, 0, tzinfo=None)
    # we also need to account for timezones, because we play this game
    # with january dates, we hopefully don't trigger any tz
    # boundaries.
    return (now - epoch).total_seconds() + time.timezone


DAY1 = mktime(2017, 1, 1, 7)
DAY1H1 = mktime(2017, 1, 1, 8)
DAY2 = mktime(2017, 1, 2, 7)
DAY2_1159 = mktime(2017, 1, 2, 23, 59, 59)
DAY3_1200 = mktime(2017, 1, 3, 0, 0, 0)
DAY3_1201 = mktime(2017, 1, 3, 0, 0, 1)
DAY3_1202 = mktime(2017, 1, 3, 0, 0, 2)

Y1D365 = mktime(2016, 12, 31, 12)
Y1D365_1 = mktime(2016, 12, 31, 20)


class TestArwnHandlers(unittest.TestCase):

    def setUp(self):
        handlers.setup()

    def test_called_for_rain(self):
        client = mock.MagicMock()

        rain_data = {"total": 10.0}

        handlers.run(client, "arwn/rain", rain_data)
        self.assertEqual(handlers.LAST_RAIN, rain_data)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, None)
        # just making sure we call across this boundary
        client.called_once_with("totals/rain", rain_data)

    def test_updates_rain_total(self):
        """Test that we initialize LAST_RAIN_TOTAL.

        LAST_RAIN_TOTAL needs to be initialized if it wasn't initially
        on the first packet into the system if it's never been before.

        This handles the case of a completely new environment where
        there was no retain message.
        """

        client = FakeClient()

        rain_data = {"total": 10.0, "timestamp": DAY1}
        rain_data2 = {"total": 11.0, "timestamp": DAY1H1}

        handlers.run(client, "arwn/rain", rain_data)
        self.assertEqual(handlers.LAST_RAIN, rain_data)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        handlers.run(client, "arwn/rain", rain_data2)
        self.assertEqual(handlers.LAST_RAIN, rain_data2)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)

    def test_updates_rain_total_retain(self):
        """Test that we initialize LAST_RAIN_TOTAL.

        LAST_RAIN_TOTAL needs to be initialized if it wasn't initially
        on the first packet into the system if it's never been before.

        This handles the case of a completely new environment where
        there was no retain message.
        """

        client = FakeClient()

        rain_data = {"total": 10.0, "timestamp": DAY1}
        rain_data2 = {"total": 11.0, "timestamp": DAY1H1}

        handlers.run(client, "arwn/totals/rain", rain_data)
        self.assertEqual(handlers.LAST_RAIN, None)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        handlers.run(client, "arwn/rain", rain_data2)
        self.assertEqual(handlers.LAST_RAIN, rain_data2)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)

    def test_updates_rain_total_overmidnight(self):
        """Test that we initialize LAST_RAIN_TOTAL.

        LAST_RAIN_TOTAL needs to be initialized if it wasn't initially
        on the first packet into the system if it's never been before.

        This handles the case of a completely new environment where
        there was no retain message.
        """

        client = FakeClient()

        rain_data = {"total": 10.0, "timestamp": DAY1}
        rain_data2 = {"total": 10.7, "timestamp": DAY1H1}
        rain_data3 = {"total": 11.0, "timestamp": DAY2}

        handlers.run(client, "arwn/totals/rain", rain_data)
        self.assertEqual(handlers.LAST_RAIN, None)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        self.assertEqual(client.log, [])
        handlers.run(client, "arwn/rain", rain_data2)
        self.assertEqual(
            client.log[-1],
            ["rain/today", dict(since_midnight=0.7, timestamp=DAY1H1)]
        )
        handlers.run(client, "arwn/rain", rain_data3)
        self.assertEqual(
            client.log[-1],
            ["rain/today", dict(since_midnight=0.3, timestamp=DAY2)]
        )
        self.assertEqual(handlers.LAST_RAIN, rain_data3)
        totals = rain_data2.copy()
        totals.update(timestamp=rain_data3['timestamp'])
        self.assertEqual(handlers.LAST_RAIN_TOTAL, totals)

    def test_updates_just_after_midnight(self):
        client = FakeClient()

        rain_data = {"total": 10.0, "timestamp": DAY2}
        rain_data2 = {"total": 11.0, "timestamp": DAY2_1159}
        rain_data3 = {"total": 12.0, "timestamp": DAY3_1200}
        rain_data4 = {"total": 12.0, "timestamp": DAY3_1201}
        rain_data5 = {"total": 12.004, "timestamp": DAY3_1202}

        handlers.run(client, "arwn/rain", rain_data)
        self.assertEqual(handlers.LAST_RAIN, rain_data)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        self.assertEqual(len(client.log), 2, client.log)
        self.assertEqual(
            client.log[-1],
            ['rain/today', dict(since_midnight=0.0, timestamp=DAY2)])

        handlers.run(client, "arwn/rain", rain_data2)
        self.assertEqual(handlers.LAST_RAIN, rain_data2)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        self.assertEqual(len(client.log), 3, client.log)
        self.assertEqual(
            client.log[-1],
            ['rain/today', dict(since_midnight=1.0, timestamp=DAY2_1159)])

        handlers.run(client, "arwn/rain", rain_data3)
        self.assertEqual(len(client.log), 6, client.log)
        self.assertEqual(
            client.log[-1],
            ["rain/today", dict(since_midnight=1.0, timestamp=DAY3_1200)]
        )
        self.assertEqual(handlers.LAST_RAIN, rain_data3)
        totals = rain_data2.copy()
        totals.update(timestamp=rain_data3['timestamp'])
        self.assertEqual(handlers.LAST_RAIN_TOTAL, totals)

        handlers.run(client, "arwn/rain", rain_data4)
        self.assertEqual(len(client.log), 7, client.log)
        self.assertEqual(
            client.log[-1],
            ["rain/today", dict(since_midnight=1.0, timestamp=DAY3_1201)]
        )
        self.assertEqual(handlers.LAST_RAIN, rain_data4)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, totals)

        handlers.run(client, "arwn/rain", rain_data5)
        self.assertEqual(
            client.log[-1],
            ["rain/today", dict(since_midnight=1.004, timestamp=DAY3_1202)]
        )

    def test_updates_over_new_years(self):
        client = FakeClient()

        rain_data = {"total": 10.0, "timestamp": Y1D365}
        rain_data2 = {"total": 11.0, "timestamp": Y1D365_1}
        rain_data3 = {"total": 12.0, "timestamp": DAY1}
        rain_data4 = {"total": 13.0, "timestamp": DAY1H1}

        handlers.run(client, "arwn/rain", rain_data)
        self.assertEqual(handlers.LAST_RAIN, rain_data)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        self.assertEqual(len(client.log), 2, client.log)
        self.assertEqual(
            client.log[-1],
            ['rain/today', dict(since_midnight=0.0, timestamp=Y1D365)])

        handlers.run(client, "arwn/rain", rain_data2)
        self.assertEqual(handlers.LAST_RAIN, rain_data2)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, rain_data)
        self.assertEqual(len(client.log), 3, client.log)
        self.assertEqual(
            client.log[-1],
            ['rain/today', dict(since_midnight=1.0, timestamp=Y1D365_1)])

        handlers.run(client, "arwn/rain", rain_data3)
        self.assertEqual(handlers.LAST_RAIN, rain_data3)
        totals = rain_data2.copy()
        totals.update(timestamp=rain_data3['timestamp'])
        self.assertEqual(handlers.LAST_RAIN_TOTAL, totals)
        self.assertEqual(len(client.log), 6, client.log)
        self.assertEqual(
            client.log[-1],
            ['rain/today', dict(since_midnight=1.0, timestamp=DAY1)])

        handlers.run(client, "arwn/rain", rain_data4)
        self.assertEqual(handlers.LAST_RAIN, rain_data4)
        self.assertEqual(handlers.LAST_RAIN_TOTAL, totals)
        self.assertEqual(len(client.log), 7, client.log)
        self.assertEqual(
            client.log[-1],
            ['rain/today', dict(since_midnight=2.0, timestamp=DAY1H1)])

    # TODO(sdague): test case for what happens when the data on the
    # rain guage gets reset due to battery replacement. I have one of
    # these events coming up this year.


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
