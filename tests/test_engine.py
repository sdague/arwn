import threading
from unittest.mock import patch

from arwn.engine import Dispatcher


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
