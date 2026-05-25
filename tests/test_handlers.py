"""Tests for rain handler logic."""

import datetime
import time

import pytest

from arwn import handlers


class FakeClient:
    def __init__(self):
        self.log = []

    def send(self, topic, payload, retain=False):
        self.log.append([topic, payload])
        handlers.run(self, "arwn/" + topic, payload)


def mktime(year=1970, mon=1, day=1, hour=0, minute=0, sec=0):
    epoch = datetime.datetime(1970, 1, 1)
    now = datetime.datetime(year, mon, day, hour, minute, sec, 0, tzinfo=None)
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


@pytest.fixture(autouse=True)
def setup_handlers(tmp_path):
    """Setup handlers with temporary state file before each test."""
    handlers.setup(state_path=tmp_path / "rain_state.json")


def test_called_for_rain(tmp_path):
    """First rain packet initializes baseline when none exists."""
    from unittest import mock

    client = mock.MagicMock()
    rain_data = {"total": 10.0}

    handlers.run(client, "arwn/rain", rain_data)
    assert handlers._rain_accumulator.last_rain == rain_data
    assert handlers._rain_accumulator.baseline is None
    client.send.assert_called_once_with("totals/rain", rain_data, retain=True)


def test_updates_rain_total():
    """LAST_RAIN_TOTAL is initialized on first rain packet via loopback."""
    client = FakeClient()

    rain_data = {"total": 10.0, "timestamp": DAY1}
    rain_data2 = {"total": 11.0, "timestamp": DAY1H1}

    handlers.run(client, "arwn/rain", rain_data)
    assert handlers._rain_accumulator.last_rain == rain_data
    assert handlers._rain_accumulator.baseline == rain_data
    handlers.run(client, "arwn/rain", rain_data2)
    assert handlers._rain_accumulator.last_rain == rain_data2
    assert handlers._rain_accumulator.baseline == rain_data


def test_updates_rain_total_retain():
    """Retained totals/rain sets baseline without needing a rain packet."""
    client = FakeClient()

    rain_data = {"total": 10.0, "timestamp": DAY1}
    rain_data2 = {"total": 11.0, "timestamp": DAY1H1}

    handlers.run(client, "arwn/totals/rain", rain_data)
    assert handlers._rain_accumulator.last_rain is None
    assert handlers._rain_accumulator.baseline == rain_data
    handlers.run(client, "arwn/rain", rain_data2)
    assert handlers._rain_accumulator.last_rain == rain_data2
    assert handlers._rain_accumulator.baseline == rain_data


def rain_today_messages(client):
    """Extract rain/today messages from client log."""
    return [m for m in client.log if m[0] == "rain/today"]


def test_updates_rain_total_overmidnight():
    """Rollover updates baseline to yesterday's last reading."""
    client = FakeClient()

    rain_data = {"total": 10.0, "timestamp": DAY1}
    rain_data2 = {"total": 10.7, "timestamp": DAY1H1}
    rain_data3 = {"total": 11.0, "timestamp": DAY2}

    handlers.run(client, "arwn/totals/rain", rain_data)
    assert handlers._rain_accumulator.last_rain is None
    assert handlers._rain_accumulator.baseline == rain_data
    assert client.log == []
    handlers.run(client, "arwn/rain", rain_data2)
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=0.7, timestamp=DAY1H1),
    ]
    handlers.run(client, "arwn/rain", rain_data3)
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=0.3, timestamp=DAY2),
    ]
    assert handlers._rain_accumulator.last_rain == rain_data3
    totals = rain_data2.copy()
    totals.update(timestamp=rain_data3["timestamp"])
    assert handlers._rain_accumulator.baseline == totals


def test_updates_just_after_midnight():
    client = FakeClient()

    rain_data = {"total": 10.0, "timestamp": DAY2}
    rain_data2 = {"total": 11.0, "timestamp": DAY2_1159}
    rain_data3 = {"total": 12.0, "timestamp": DAY3_1200}
    rain_data4 = {"total": 12.0, "timestamp": DAY3_1201}
    rain_data5 = {"total": 12.004, "timestamp": DAY3_1202}

    handlers.run(client, "arwn/rain", rain_data)
    assert handlers._rain_accumulator.last_rain == rain_data
    assert handlers._rain_accumulator.baseline == rain_data
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=0.0, timestamp=DAY2),
    ]

    handlers.run(client, "arwn/rain", rain_data2)
    assert handlers._rain_accumulator.last_rain == rain_data2
    assert handlers._rain_accumulator.baseline == rain_data
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=1.0, timestamp=DAY2_1159),
    ]

    handlers.run(client, "arwn/rain", rain_data3)
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=1.0, timestamp=DAY3_1200),
    ]
    assert handlers._rain_accumulator.last_rain == rain_data3
    totals = rain_data2.copy()
    totals.update(timestamp=rain_data3["timestamp"])
    assert handlers._rain_accumulator.baseline == totals

    handlers.run(client, "arwn/rain", rain_data4)
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=1.0, timestamp=DAY3_1201),
    ]
    assert handlers._rain_accumulator.last_rain == rain_data4
    assert handlers._rain_accumulator.baseline == totals

    handlers.run(client, "arwn/rain", rain_data5)
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=1.004, timestamp=DAY3_1202),
    ]


def test_updates_over_new_years():
    client = FakeClient()

    rain_data = {"total": 10.0, "timestamp": Y1D365}
    rain_data2 = {"total": 11.0, "timestamp": Y1D365_1}
    rain_data3 = {"total": 12.0, "timestamp": DAY1}
    rain_data4 = {"total": 13.0, "timestamp": DAY1H1}

    handlers.run(client, "arwn/rain", rain_data)
    assert handlers._rain_accumulator.last_rain == rain_data
    assert handlers._rain_accumulator.baseline == rain_data
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=0.0, timestamp=Y1D365),
    ]

    handlers.run(client, "arwn/rain", rain_data2)
    assert handlers._rain_accumulator.last_rain == rain_data2
    assert handlers._rain_accumulator.baseline == rain_data
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=1.0, timestamp=Y1D365_1),
    ]

    handlers.run(client, "arwn/rain", rain_data3)
    assert handlers._rain_accumulator.last_rain == rain_data3
    totals = rain_data2.copy()
    totals.update(timestamp=rain_data3["timestamp"])
    assert handlers._rain_accumulator.baseline == totals
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=1.0, timestamp=DAY1),
    ]

    handlers.run(client, "arwn/rain", rain_data4)
    assert handlers._rain_accumulator.last_rain == rain_data4
    assert handlers._rain_accumulator.baseline == totals
    assert rain_today_messages(client)[-1] == [
        "rain/today",
        dict(since_midnight=2.0, timestamp=DAY1H1),
    ]


def test_persists_state_to_disk(tmp_path):
    """State survives a simulated restart."""
    state_file = tmp_path / "rain_state.json"
    handlers.setup(state_path=state_file)
    client = FakeClient()
    handlers.run(client, "arwn/rain", {"total": 5.0, "timestamp": DAY1})
    assert handlers._rain_accumulator.baseline["total"] == 5.0

    handlers.setup(state_path=state_file)
    assert handlers._rain_accumulator.baseline is not None
    assert handlers._rain_accumulator.baseline["total"] == 5.0


def test_corrupt_state_file(tmp_path):
    """Corrupt state file logs warning and starts fresh."""
    state_file = tmp_path / "rain_state.json"
    state_file.write_text("not json {{{")
    handlers.setup(state_path=state_file)
    assert handlers._rain_accumulator.baseline is None


def test_rain_event_starts_on_increment(tmp_path):
    """RainEventTracker publishes active event on total increase."""
    state_file = tmp_path / "rain_state.json"
    handlers.setup(state_path=state_file)
    client = FakeClient()

    handlers.run(client, "arwn/rain", {"total": 5.0, "timestamp": DAY1})
    handlers.run(client, "arwn/rain", {"total": 5.2, "timestamp": DAY1 + 120})

    event_msgs = [m for m in client.log if m[0] == "rain/event"]
    assert len(event_msgs) == 1
    assert event_msgs[0][1]["active"] is True
    assert event_msgs[0][1]["event_total"] == 0.2


def test_rain_event_continues_on_increment(tmp_path):
    """RainEventTracker continues existing event on subsequent increases."""
    state_file = tmp_path / "rain_state.json"
    handlers.setup(state_path=state_file)
    client = FakeClient()

    handlers.run(client, "arwn/rain", {"total": 5.0, "timestamp": DAY1})
    handlers.run(client, "arwn/rain", {"total": 5.2, "timestamp": DAY1 + 120})
    handlers.run(client, "arwn/rain", {"total": 5.5, "timestamp": DAY1 + 240})

    event_msgs = [m for m in client.log if m[0] == "rain/event"]
    assert len(event_msgs) == 2
    assert event_msgs[1][1]["active"] is True
    assert event_msgs[1][1]["event_total"] == 0.5


def test_rain_event_ends_after_12h_gap(tmp_path):
    """RainEventTracker ends event after 12h of no increase."""
    state_file = tmp_path / "rain_state.json"
    handlers.setup(state_path=state_file)
    client = FakeClient()

    handlers.run(client, "arwn/rain", {"total": 5.0, "timestamp": DAY1})
    handlers.run(client, "arwn/rain", {"total": 5.5, "timestamp": DAY1 + 120})

    gap_ts = DAY1 + 120 + (12 * 3600)
    handlers.run(client, "arwn/rain", {"total": 5.5, "timestamp": gap_ts})

    event_msgs = [m for m in client.log if m[0] == "rain/event"]
    last_event = event_msgs[-1]
    assert last_event[1]["active"] is False


def test_rain_event_persists_across_restart(tmp_path):
    """Event state survives restart."""
    state_file = tmp_path / "rain_state.json"
    handlers.setup(state_path=state_file)
    client = FakeClient()

    handlers.run(client, "arwn/rain", {"total": 5.0, "timestamp": DAY1})
    handlers.run(client, "arwn/rain", {"total": 5.5, "timestamp": DAY1 + 120})
    assert handlers._rain_event_tracker.event_active is True

    handlers.setup(state_path=state_file)
    assert handlers._rain_event_tracker.event_active is True
    assert handlers._rain_event_tracker.event_start_total == 5.0
