"""Tests for the Config dataclass and from_dict factory."""

import logging

import pytest

from arwn.config import Config


def minimal_raw():
    return {
        "mqtt": {"server": "localhost"},
        "names": {"aa:01": "Outside"},
        "collector": {"type": "rtl433"},
    }


class TestConfigConstruction:
    def test_minimal_valid(self):
        cfg = Config.from_dict(minimal_raw())
        assert cfg.mqtt.server == "localhost"
        assert cfg.mqtt.root == "arwn"
        assert cfg.mqtt.port == 1883
        assert cfg.mqtt.username is None
        assert cfg.mqtt.password is None
        assert cfg.names == {"aa:01": "Outside"}
        assert cfg.collector.type == "rtl433"
        assert cfg.wunderground is None
        assert cfg.logfile is None

    def test_full_config(self):
        raw = {
            "mqtt": {
                "server": "10.0.0.1",
                "root": "weather",
                "username": "admin",
                "password": "secret",
                "port": 8883,
            },
            "names": {"bb:02": "Garden"},
            "collector": {"type": "rfxcom", "device": "/dev/ttyUSB0"},
            "wunderground": {
                "username": "me@example.com",
                "station": "KTEST1",
                "password": "wupass",
            },
            "logfile": "/var/log/arwn.log",
        }
        cfg = Config.from_dict(raw)
        assert cfg.mqtt.server == "10.0.0.1"
        assert cfg.mqtt.root == "weather"
        assert cfg.mqtt.username == "admin"
        assert cfg.mqtt.password == "secret"
        assert cfg.mqtt.port == 8883
        assert cfg.collector.type == "rfxcom"
        assert cfg.collector.device == "/dev/ttyUSB0"
        assert cfg.wunderground.username == "me@example.com"
        assert cfg.wunderground.station == "KTEST1"
        assert cfg.wunderground.password == "wupass"
        assert cfg.logfile == "/var/log/arwn.log"

    def test_empty_names_allowed(self):
        raw = {"mqtt": {"server": "localhost"}, "names": {}}
        cfg = Config.from_dict(raw)
        assert cfg.names == {}

    def test_collector_defaults_to_rtl433(self):
        raw = {"mqtt": {"server": "localhost"}, "names": {}}
        cfg = Config.from_dict(raw)
        assert cfg.collector.type == "rtl433"
        assert cfg.collector.device is None


class TestLegacyKeys:
    def test_mqtt_user_warns(self, caplog):
        raw = {
            "mqtt": {"server": "localhost", "user": "olduser", "passwd": "oldpass"},
            "names": {},
        }
        with caplog.at_level(logging.WARNING):
            cfg = Config.from_dict(raw)
        assert cfg.mqtt.username == "olduser"
        assert cfg.mqtt.password == "oldpass"
        assert "mqtt.user" in caplog.text
        assert "mqtt.passwd" in caplog.text

    def test_canonical_takes_precedence_over_legacy(self, caplog):
        raw = {
            "mqtt": {
                "server": "localhost",
                "user": "old",
                "username": "new",
                "passwd": "oldpw",
                "password": "newpw",
            },
            "names": {},
        }
        with caplog.at_level(logging.WARNING):
            cfg = Config.from_dict(raw)
        assert cfg.mqtt.username == "new"
        assert cfg.mqtt.password == "newpw"
        assert "deprecated" not in caplog.text

    def test_top_level_device_warns(self, caplog):
        raw = {
            "mqtt": {"server": "localhost"},
            "names": {},
            "device": "/dev/ttyUSB0",
        }
        with caplog.at_level(logging.WARNING):
            cfg = Config.from_dict(raw)
        assert cfg.collector.device == "/dev/ttyUSB0"
        assert cfg.collector.type == "rfxcom"
        assert "Top-level 'device'" in caplog.text

    def test_wunderground_legacy_keys_warn(self, caplog):
        raw = {
            "mqtt": {"server": "localhost"},
            "names": {},
            "wunderground": {
                "user": "me@test.com",
                "station": "KTEST",
                "passwd": "secret",
            },
        }
        with caplog.at_level(logging.WARNING):
            cfg = Config.from_dict(raw)
        assert cfg.wunderground.username == "me@test.com"
        assert cfg.wunderground.password == "secret"
        assert "wunderground.user" in caplog.text
        assert "wunderground.passwd" in caplog.text


class TestValidation:
    def test_missing_mqtt_server_raises(self):
        raw = {"mqtt": {}, "names": {}}
        with pytest.raises(ValueError, match="mqtt.server"):
            Config.from_dict(raw)

    def test_missing_mqtt_section_raises(self):
        raw = {"names": {}}
        with pytest.raises(ValueError, match="mqtt.server"):
            Config.from_dict(raw)

    def test_missing_names_raises(self):
        raw = {"mqtt": {"server": "localhost"}}
        with pytest.raises(ValueError, match="names"):
            Config.from_dict(raw)
