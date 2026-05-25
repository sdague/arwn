"""Pytest configuration and fixtures."""

import re
import time
from dataclasses import dataclass
from typing import Union

import pytest

from tests.mqtt_broker import ReceivedMessage, SimpleMQTTBroker


@dataclass
class SimBrokerHandle:
    host: str
    port: int
    broker: SimpleMQTTBroker


@pytest.fixture(scope="module")
def sim_broker():
    """Start a SimpleMQTTBroker for the test module. One broker per module."""
    broker = SimpleMQTTBroker()
    broker.start()
    yield SimBrokerHandle(host="localhost", port=broker.port, broker=broker)
    broker.stop()


@pytest.fixture(autouse=False)
def sim_broker_clean(sim_broker):
    """Reset broker message and retained state before each test."""
    sim_broker.broker.messages.clear()
    sim_broker.broker.retained.clear()
    sim_broker.broker.wills.clear()
    yield


def wait_for_message(
    broker: SimpleMQTTBroker,
    pattern: Union[str, "re.Pattern"],
    timeout: float = 2.0,
) -> ReceivedMessage:
    """Poll broker.messages until a message matching pattern arrives.

    pattern: str      → topic prefix match (topic.startswith(pattern))
    pattern: re.Pattern → regex match against topic

    Raises TimeoutError if no match within timeout seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with broker._messages_lock:
            for msg in broker.messages:
                if isinstance(pattern, str):
                    if msg.topic.startswith(pattern):
                        return msg
                else:
                    if pattern.search(msg.topic):
                        return msg
        time.sleep(0.05)
    with broker._messages_lock:
        topics = [m.topic for m in broker.messages]
    raise TimeoutError(
        f"No message matching {pattern!r} arrived within {timeout}s. "
        f"Topics seen: {topics}"
    )


@pytest.fixture
def sample_config(tmp_path):
    """Create a sample configuration file for testing."""
    config_path = tmp_path / "config.yml"
    config_path.write_text("""device: /dev/ttyUSB0
logfile: test.log
mqtt:
  server: 10.42.0.3
names:
  "ec:01": "Outside"
  "65:00": "Rain"
  "33:00": "Wind"
  "a9:04": "Freezer"
  "8c:00": "Refrigerator"
  "ce:08": "Arwen Room"
  "07:05": "Office"
  "e3:02": "Bomb Shelter"
  "de:01": "Subaru"
  "8e:01": "Cold Frame"
  "55:09": "Bed Room"
  "e9:04": "Garage"
""")
    return str(config_path)
