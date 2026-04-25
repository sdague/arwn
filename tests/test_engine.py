import os
import tempfile
import threading
import time
from unittest.mock import patch

import yaml

from arwn.engine import ConfigWatcher, Dispatcher


def make_config(names=None):
    return {
        "collector": {"type": "rfxcom", "device": "/dev/ttyUSB0"},
        "names": names or {"aa:01": "outdoor"},
        "mqtt": {"server": "localhost"},
    }


@patch("arwn.engine.MQTT")
@patch("arwn.engine.RFXCOMCollector")
def test_dispatcher_reload_updates_names(mock_collector, mock_mqtt):
    config = make_config({"aa:01": "outdoor"})
    d = Dispatcher(config)
    assert d.names == {"aa:01": "outdoor"}

    new_config = make_config({"aa:01": "garden", "bb:02": "porch"})
    d.reload(new_config)
    assert d.names == {"aa:01": "garden", "bb:02": "porch"}


@patch("arwn.engine.MQTT")
@patch("arwn.engine.RFXCOMCollector")
def test_dispatcher_reload_is_thread_safe(mock_collector, mock_mqtt):
    config = make_config({"aa:01": "outdoor"})
    d = Dispatcher(config)

    errors = []

    def do_reload():
        for _ in range(50):
            try:
                d.reload(make_config({"aa:01": "updated"}))
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=do_reload) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []


@patch("arwn.engine.MQTT")
@patch("arwn.engine.RFXCOMCollector")
def test_config_watcher_triggers_reload(mock_collector, mock_mqtt):
    initial = {
        "collector": {"type": "rfxcom", "device": "/dev/null"},
        "names": {"aa:01": "outdoor"},
        "mqtt": {"server": "localhost"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(initial, f)
        config_path = f.name

    try:
        dispatcher = Dispatcher(initial)
        watcher = ConfigWatcher(config_path, dispatcher)
        watcher.start()
        try:
            updated = dict(initial)
            updated["names"] = {"aa:01": "garden"}
            with open(config_path, "w") as f:
                yaml.dump(updated, f)

            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if dispatcher.names == {"aa:01": "garden"}:
                    break
                time.sleep(0.05)
        finally:
            watcher.stop()

        assert dispatcher.names == {"aa:01": "garden"}
    finally:
        os.unlink(config_path)
