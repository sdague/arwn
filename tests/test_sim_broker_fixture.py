"""Test that the sim_broker fixture and wait_for_message work correctly."""

import json
import time

import paho.mqtt.client as mqtt
import pytest


def test_sim_broker_fixture_provides_handle(sim_broker):
    assert sim_broker.host == "localhost"
    assert sim_broker.port > 0
    assert sim_broker.broker is not None


def test_sim_broker_clean_resets_messages(sim_broker, sim_broker_clean):
    assert sim_broker.broker.messages == []
    assert sim_broker.broker.retained == {}


def test_wait_for_message_returns_on_match(sim_broker, sim_broker_clean):
    from tests.conftest import wait_for_message

    c = mqtt.Client()
    c.connect(sim_broker.host, sim_broker.port)
    c.loop_start()
    time.sleep(0.1)
    c.publish("arwn/test", json.dumps({"x": 1}))
    time.sleep(0.05)

    msg = wait_for_message(sim_broker.broker, "arwn/test")
    assert msg.topic == "arwn/test"
    assert json.loads(msg.payload)["x"] == 1

    c.loop_stop()
    c.disconnect()


def test_wait_for_message_times_out(sim_broker, sim_broker_clean):
    from tests.conftest import wait_for_message

    with pytest.raises(TimeoutError, match="arwn/never"):
        wait_for_message(sim_broker.broker, "arwn/never", timeout=0.3)
