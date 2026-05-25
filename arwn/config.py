from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    server: str
    root: str = "arwn"
    username: str | None = None
    password: str | None = None
    port: int = 1883


@dataclass
class CollectorConfig:
    type: str = "rtl433"
    device: str | None = None
    devices: list | None = None


@dataclass
class WundergroundConfig:
    username: str | None = None
    station: str | None = None
    password: str | None = None


@dataclass
class Config:
    mqtt: MQTTConfig
    names: dict[str, str]
    collector: CollectorConfig = field(default_factory=CollectorConfig)
    wunderground: WundergroundConfig | None = None
    logfile: str | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> Config:
        mqtt_raw = dict(raw.get("mqtt") or {})

        if "user" in mqtt_raw:
            if "username" not in mqtt_raw:
                logger.warning(
                    "Config key 'mqtt.user' is deprecated; use 'mqtt.username'"
                )
                mqtt_raw["username"] = mqtt_raw.pop("user")
            else:
                mqtt_raw.pop("user")

        if "passwd" in mqtt_raw:
            if "password" not in mqtt_raw:
                logger.warning(
                    "Config key 'mqtt.passwd' is deprecated; use 'mqtt.password'"
                )
                mqtt_raw["password"] = mqtt_raw.pop("passwd")
            else:
                mqtt_raw.pop("passwd")

        if "server" not in mqtt_raw:
            raise ValueError("Config requires 'mqtt.server'")

        mqtt_cfg = MQTTConfig(
            server=mqtt_raw["server"],
            root=mqtt_raw.get("root", "arwn"),
            username=mqtt_raw.get("username"),
            password=mqtt_raw.get("password"),
            port=mqtt_raw.get("port", 1883),
        )

        names = raw.get("names")
        if names is None:
            raise ValueError("Config requires 'names' section")

        col_raw = dict(raw.get("collector") or {})

        if "device" in raw and "device" not in col_raw:
            logger.warning("Top-level 'device' is deprecated; use 'collector.device'")
            col_raw.setdefault("type", "rfxcom")
            col_raw["device"] = raw["device"]

        collector_cfg = CollectorConfig(
            type=col_raw.get("type", "rtl433"),
            device=col_raw.get("device"),
            devices=col_raw.get("devices"),
        )

        wu_raw = raw.get("wunderground")
        wu_cfg = None
        if wu_raw:
            wu_raw = dict(wu_raw)

            if "user" in wu_raw:
                if "username" not in wu_raw:
                    logger.warning(
                        "Config key 'wunderground.user' is deprecated; "
                        "use 'wunderground.username'"
                    )
                    wu_raw["username"] = wu_raw.pop("user")
                else:
                    wu_raw.pop("user")

            if "passwd" in wu_raw:
                if "password" not in wu_raw:
                    logger.warning(
                        "Config key 'wunderground.passwd' is deprecated; "
                        "use 'wunderground.password'"
                    )
                    wu_raw["password"] = wu_raw.pop("passwd")
                else:
                    wu_raw.pop("passwd")

            wu_cfg = WundergroundConfig(
                username=wu_raw.get("username"),
                station=wu_raw.get("station"),
                password=wu_raw.get("password"),
            )

        return cls(
            mqtt=mqtt_cfg,
            names=names,
            collector=collector_cfg,
            wunderground=wu_cfg,
            logfile=raw.get("logfile"),
        )
