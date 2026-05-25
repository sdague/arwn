import datetime
import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path.home() / ".local" / "share" / "arwn"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "rain_state.json"


class RainStateStore:
    """Persists rain state to disk as a sectioned JSON dict."""

    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_STATE_FILE
        self._state = self._load_from_disk()

    def _load_from_disk(self):
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            logger.info("Loaded rain state from %s", self.path)
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Corrupt rain state file %s (%s), starting fresh", self.path, e
            )
            return {}

    def get(self, section):
        return self._state.get(section)

    def update(self, section, data):
        self._state[section] = data
        self._flush()

    def _flush(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self._state, f, indent=2)
        os.replace(tmp, self.path)


class RainAccumulator:
    """Tracks rain baseline and computes since-midnight totals.

    Watches:
      - {root}/rain (raw rain gauge readings)
      - {root}/totals/rain (retained baseline)

    Publishes:
      - rain/today (since_midnight computation)
      - totals/rain (retained, on rollover or initialization)
    """

    _RE_RAIN = re.compile(r"^\w+/rain$")
    _RE_TOTALS = re.compile(r"^\w+/totals/rain$")
    _RE_SKIP = re.compile(r"rain/today|totals/rain|rain/event")

    def __init__(self, store):
        self.store = store
        state = store.get("accumulator")
        if state:
            self.baseline = state.get("baseline")
            self.last_rain = state.get("last_rain")
        else:
            self.baseline = None
            self.last_rain = None
        self.prev_rain = None

    def run(self, client, topic, payload):
        if self._RE_TOTALS.search(topic):
            self._on_totals(client, topic, payload)
        elif self._RE_RAIN.search(topic):
            self._on_rain(client, topic, payload)
        elif not self._RE_SKIP.search(topic):
            self._check_rollover(client, topic, payload)

    def _on_totals(self, client, topic, payload):
        self.baseline = payload
        self._persist()

    def _on_rain(self, client, topic, payload):
        self.prev_rain = self.last_rain or payload
        self.last_rain = payload

        if not self.baseline:
            client.send("totals/rain", payload, retain=True)

        if self.baseline:
            ts = payload.get("timestamp")
            if (
                ts
                and self.prev_rain
                and not self._is_same_day(ts, self.baseline["timestamp"])
            ):
                self._do_rollover(client, ts)

            delta = payload["total"] - self.baseline["total"]
            if delta < 0:
                delta = 0
            since_midnight = {
                "timestamp": payload["timestamp"],
                "since_midnight": round(delta, 3),
            }
            client.send("rain/today", since_midnight)

        self._persist()

    def _check_rollover(self, client, topic, payload):
        ts = payload.get("timestamp")
        if not ts or not self.baseline or not self.prev_rain:
            return

        if self._is_same_day(ts, self.baseline["timestamp"]):
            return

        self._do_rollover(client, ts)

    def _do_rollover(self, client, ts):
        logger.info("Rain day rollover detected")
        totals = self._yesterdays_totals()
        totals["timestamp"] = ts
        client.send("totals/rain", totals, retain=True)

    def _is_same_day(self, ts1, ts2):
        return datetime.date.fromtimestamp(ts1) == datetime.date.fromtimestamp(ts2)

    def _yesterdays_totals(self):
        if self._is_same_day(self.baseline["timestamp"], self.last_rain["timestamp"]):
            total = self.last_rain
        else:
            total = self.prev_rain
        return total.copy()

    def _persist(self):
        self.store.update(
            "accumulator",
            {"baseline": self.baseline, "last_rain": self.last_rain},
        )


class RainEventTracker:
    """Tracks rain events using lazy gap detection.

    A rain event starts when the gauge total increases.
    A rain event ends when 12 hours pass with no increase.
    Rain gauge packets arrive every 1-3 minutes even when idle.

    Watches: {root}/rain
    Publishes: rain/event with {timestamp, event_total, active}
    """

    GAP_SECONDS = 12 * 3600

    _RE_RAIN = re.compile(r"^\w+/rain$")

    def __init__(self, store):
        self.store = store
        state = store.get("event")
        if state:
            self.event_active = state.get("active", False)
            self.event_start_total = state.get("start_total")
            self.event_last_increment_ts = state.get("last_increment_ts")
            self.last_seen_total = state.get("last_seen_total")
        else:
            self.event_active = False
            self.event_start_total = None
            self.event_last_increment_ts = None
            self.last_seen_total = None

    def run(self, client, topic, payload):
        if not self._RE_RAIN.search(topic):
            return

        ts = payload.get("timestamp")
        total = payload.get("total")
        if ts is None or total is None:
            return

        if self.event_active and self.event_last_increment_ts:
            if ts - self.event_last_increment_ts >= self.GAP_SECONDS:
                self._end_event(client, ts)

        if self.last_seen_total is not None and total > self.last_seen_total:
            if not self.event_active:
                self.event_active = True
                self.event_start_total = self.last_seen_total
            self.event_last_increment_ts = ts
            self._publish_event(client, ts, total)

        self.last_seen_total = total
        self._persist()

    def _end_event(self, client, ts):
        self.event_active = False
        self._publish_event(client, ts, self.last_seen_total)

    def _publish_event(self, client, ts, current_total):
        if self.event_start_total is not None and current_total is not None:
            event_total = round(current_total - self.event_start_total, 3)
        else:
            event_total = 0.0
        client.send(
            "rain/event",
            {"timestamp": ts, "event_total": event_total, "active": self.event_active},
        )

    def _persist(self):
        self.store.update(
            "event",
            {
                "active": self.event_active,
                "start_total": self.event_start_total,
                "last_increment_ts": self.event_last_increment_ts,
                "last_seen_total": self.last_seen_total,
            },
        )
