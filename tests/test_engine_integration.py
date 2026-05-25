"""Integration tests: engine <-> SimpleMQTTBroker roundtrip."""

import json
import socket
import time

import paho.mqtt.client as paho

from arwn import engine, handlers
from arwn.config import Config
from tests.conftest import wait_for_message


def make_config(port, names=None):
    return Config.from_dict(
        {
            "mqtt": {"server": "localhost", "port": port},
            "names": names or {},
            "collector": {"type": "rfxcom", "device": "/dev/null"},
        }
    )


def test_status_alive_published_with_retain(sim_broker, sim_broker_clean):
    """engine.MQTT publishes arwn/status with retain=True on connect."""
    handlers.setup()
    mq = engine.MQTT(make_config(sim_broker.port), port=sim_broker.port)
    try:
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        assert "arwn/status" in sim_broker.broker.retained
        payload = json.loads(sim_broker.broker.retained["arwn/status"])
        assert payload["status"] == "alive"
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()


def test_will_published_on_unclean_disconnect(sim_broker, sim_broker_clean):
    """Will message arwn/status=dead is published when engine socket is force-closed."""
    handlers.setup()
    mq = engine.MQTT(make_config(sim_broker.port), port=sim_broker.port)
    try:
        # Wait for initial status=alive
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        sim_broker.broker.messages.clear()

        # Force-close the socket before stopping the loop — loop_stop() in paho 2.x
        # sends a clean DISCONNECT which clears the will on the broker side.
        try:
            mq.client._sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        mq.client.loop_stop()

        # Broker should detect EOF and fire the will
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        payload = json.loads(sim_broker.broker.retained["arwn/status"])
        assert payload["status"] == "dead"
    finally:
        try:
            mq.client.loop_stop()
        except Exception:
            pass
        try:
            mq.client.disconnect()
        except Exception:
            pass


def test_rain_sensor_publishes_to_rain_topic(sim_broker, sim_broker_clean):
    """engine.MQTT.send('rain', payload) publishes to arwn/rain."""
    handlers.setup()
    mq = engine.MQTT(make_config(sim_broker.port), port=sim_broker.port)
    try:
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        now = int(time.time())
        payload = {"total": 1.23, "units": "in", "timestamp": now}
        mq.send("rain", payload)
        msg = wait_for_message(sim_broker.broker, "arwn/rain", timeout=2.0)
        data = json.loads(msg.payload.decode("utf-8"))
        assert data["total"] == 1.23
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()


def test_rain_handler_computes_today_total(sim_broker, sim_broker_clean):
    """RainAccumulator emits arwn/rain/today when baseline is pre-seeded.

    The accumulator sets baseline when the engine receives a retained
    arwn/totals/rain replayed on subscribe. Pre-seed that retained message
    before the engine connects so the handler chain has the state it needs.
    """
    now = int(time.time())
    seed_payload = json.dumps({"total": 0.5, "units": "in", "timestamp": now})
    sim_broker.broker.retained["arwn/totals/rain"] = seed_payload.encode("utf-8")

    handlers.setup()
    mq = engine.MQTT(make_config(sim_broker.port), port=sim_broker.port)
    publisher = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION2)
    try:
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if handlers._rain_accumulator.baseline is not None:
                break
            time.sleep(0.05)
        assert handlers._rain_accumulator.baseline is not None, (
            "baseline not set after engine connected and received retained "
            "arwn/totals/rain"
        )

        publisher.connect("localhost", sim_broker.port)
        publisher.loop_start()
        try:
            sim_broker.broker.messages.clear()

            rain_payload = json.dumps(
                {"total": 0.7, "units": "in", "timestamp": now + 60}
            ).encode("utf-8")
            publisher.publish("arwn/rain", rain_payload)
            msg = wait_for_message(sim_broker.broker, "arwn/rain/today", timeout=2.0)
            data = json.loads(msg.payload.decode("utf-8"))
            assert "since_midnight" in data
        finally:
            publisher.loop_stop()
            publisher.disconnect()
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()


def test_retained_rain_total_replayed_on_reconnect(sim_broker, sim_broker_clean):
    """A retained arwn/totals/rain is replayed to a new subscriber on connect."""
    # Publish a retained message using a plain paho client
    publisher = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION2)
    publisher.connect("localhost", sim_broker.port)
    publisher.loop_start()
    payload = json.dumps({"total": 3.1, "units": "in", "timestamp": int(time.time())})
    publisher.publish("arwn/totals/rain", payload.encode("utf-8"), retain=True)
    # Wait for broker to record the retained message
    wait_for_message(sim_broker.broker, "arwn/totals/rain", timeout=2.0)
    publisher.loop_stop()
    publisher.disconnect()

    # A new subscriber should receive the retained message on connect
    received = []
    subscriber = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION2)

    def on_message(client, userdata, msg):
        received.append(msg)

    subscriber.on_message = on_message
    subscriber.connect("localhost", sim_broker.port)
    subscriber.loop_start()
    subscriber.subscribe("arwn/#")
    try:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if any(m.topic == "arwn/totals/rain" for m in received):
                break
            time.sleep(0.05)
        rain_msgs = [m for m in received if m.topic == "arwn/totals/rain"]
        assert rain_msgs, "No retained arwn/totals/rain received by new subscriber"
        data = json.loads(rain_msgs[0].payload.decode("utf-8"))
        assert data["total"] == 3.1
    finally:
        subscriber.loop_stop()
        subscriber.disconnect()


def test_temperature_sensor_routes_by_name(sim_broker, sim_broker_clean):
    """engine.MQTT.send routes temperature data to arwn/temperature/<name>."""
    handlers.setup()
    config = make_config(sim_broker.port, names={"aa:01": "outside"})
    mq = engine.MQTT(config, port=sim_broker.port)
    try:
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        now = int(time.time())
        payload = {
            "temp": 72.5,
            "humid": 55.0,
            "dewpoint": 54.2,
            "units": "F",
            "timestamp": now,
        }
        mq.send("temperature/outside", payload)
        msg = wait_for_message(
            sim_broker.broker, "arwn/temperature/outside", timeout=2.0
        )
        data = json.loads(msg.payload.decode("utf-8"))
        assert data["temp"] == 72.5
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()
