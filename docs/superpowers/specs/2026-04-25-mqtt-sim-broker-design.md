# MQTT Simulation Broker Design

**Date:** 2026-04-25
**Status:** Approved

## Goal

Replace mock-level handler tests with full integration tests that exercise the
engine → sim broker → handler roundtrip. The sim broker runs in-process with no
external dependencies so CI does not require mosquitto installed. Real mosquitto
tests (`test_mqtt_real.py`) are kept as an optional layer.

---

## Architecture

Extend `tests/mqtt_broker.py` (`SimpleMQTTBroker`) with three protocol
capabilities and an inspection API. Add a `sim_broker` pytest fixture to
`conftest.py`. Write integration tests in a new `tests/test_engine_integration.py`.

```
┌─────────────────────────────────────────────────────┐
│  test_engine_integration.py                         │
│                                                     │
│  engine.MQTT (paho client)  ──publish/subscribe──►  │
│                                  SimpleMQTTBroker   │
│  engine.Dispatcher          ◄──on_message───────    │
│       │                         (in-process,        │
│       ▼                          no subprocess)     │
│  handlers.py                                        │
└─────────────────────────────────────────────────────┘
```

---

## Component 1: `SimpleMQTTBroker` enhancements (`tests/mqtt_broker.py`)

### 1a. Retained message store

`self.retained: dict[str, bytes]` — stores the last retained publish per exact
topic. Updated on every PUBLISH with retain=1; cleared for a topic when a
retained publish arrives with empty payload.

On SUBSCRIBE, immediately replay matching retained messages to the subscribing
connection. Matching uses the existing wildcard logic already in the broker.

### 1b. Will message registration

On CONNECT, parse the will flag, will QoS, will retain, will topic, and will
payload from the connect packet. Store per connection as
`self.wills: dict[conn, WillMessage]`.

On **unclean disconnect** (socket error / EOF without a prior DISCONNECT
packet): publish the will (respecting its retain flag) and remove it.

On **clean DISCONNECT packet**: clear the will without publishing it.

`WillMessage` is a small dataclass: `topic: str`, `payload: bytes`,
`retain: bool`, `qos: int`.

### 1c. QoS 1 PUBACK

When a PUBLISH arrives with QoS 1 (header bits `0x32`), send PUBACK
(fixed header `0x40`, remaining length `0x02`, packet ID echoed back).
QoS 2 is acknowledged as QoS 1 (PUBACK only) — sufficient for paho to not
stall; full QoS 2 flow is out of scope.

### 1d. Inspection API

`self.messages: list[ReceivedMessage]` — every PUBLISH the broker processes is
appended here (regardless of retain flag or QoS). Never cleared automatically;
tests reset it via `broker.messages.clear()` in fixtures.

`ReceivedMessage` dataclass: `topic: str`, `payload: bytes`, `retain: bool`,
`qos: int`, `timestamp: float` (from `time.monotonic()`).

`self.retained: dict[str, bytes]` — already described above; exposed directly
for test assertions.

---

## Component 2: pytest fixtures (`tests/conftest.py`)

### `sim_broker` fixture (module-scoped)

Starts one `SimpleMQTTBroker` instance per test module on a random free port.
Yields `SimBrokerHandle(host="localhost", port=<n>, broker=<instance>)`.
Stops and joins the broker thread on teardown.

Module scope (rather than session) keeps inter-test state leakage bounded —
each test module gets a fresh broker.

### `sim_broker_clean` fixture (function-scoped, uses `sim_broker`)

Calls `sim_broker.broker.messages.clear()` and
`sim_broker.broker.retained.clear()` before each test, so tests in the same
module start with a clean slate without paying broker startup cost.

### `wait_for_message(broker, pattern, timeout=2.0)` helper

Not a fixture — a plain function in `conftest.py`. Polls `broker.messages`
every 50 ms until a message whose topic matches `pattern` (string prefix or
compiled regex) appears, or `timeout` seconds elapse. Returns the matching
`ReceivedMessage`. Raises `TimeoutError` with a descriptive message if it
times out. Replaces all `time.sleep()` calls in integration tests.

---

## Component 3: Integration tests (`tests/test_engine_integration.py`)

Six tests, all using `sim_broker_clean` (function-scoped reset) and the
`sim_broker` (module-scoped broker instance).

Each test constructs a minimal config dict pointing at `sim_broker.port`,
creates an `engine.Dispatcher` or `engine.MQTT` instance, and uses
`wait_for_message` for synchronisation.

### Test 1 — `test_status_alive_published_with_retain`

Engine connects. Assert `arwn/status` appears in `broker.retained` with
`payload["status"] == "alive"`.

### Test 2 — `test_will_published_on_unclean_disconnect`

Engine connects. Force-close the underlying paho socket (simulating network
drop). `wait_for_message(broker, "arwn/status")` after the close. Assert
`broker.retained["arwn/status"]` decodes to `{"status": "dead"}`.

### Test 3 — `test_rain_sensor_publishes_to_rain_topic`

Construct a `SensorPacket` with `IS_RAIN` type and known rain total. Call
`dispatcher.mqtt.send("rain", packet.as_json(...))` directly. Assert a message
on `arwn/rain` appears with `total` field matching the packet value.

### Test 4 — `test_rain_handler_computes_today_total`

Publish a `arwn/rain` message via the broker (simulating an incoming sensor
reading). `wait_for_message(broker, "arwn/totals/rain")`. Assert the message
payload contains a `since_midnight` field.

### Test 5 — `test_retained_rain_total_replayed_on_reconnect`

Publish a retained `arwn/totals/rain` message. Disconnect and reconnect a
second paho client subscribing to `arwn/#`. Assert the first message it
receives is the retained total (via `wait_for_message`).

### Test 6 — `test_temperature_sensor_routes_by_name`

Configure dispatcher `names` with `{"aa:01": "outside"}`. Dispatch a temp
packet with `sensor_id = "aa:01"`. `wait_for_message(broker, "arwn/temperature/outside")`.
Assert `temp` and `humid` fields in payload.

---

## What is explicitly out of scope

- Full QoS 2 four-way handshake (PUBREC/PUBREL/PUBCOMP)
- MQTT 5 properties
- Authentication enforcement
- Keep-alive timeout enforcement
- Persistent sessions across broker restarts
- Replacing `test_mqtt_real.py` (real mosquitto tests are kept as optional)

---

## File changes summary

| File | Change |
|------|--------|
| `tests/mqtt_broker.py` | Add retained store, will handling, QoS 1 PUBACK, inspection API |
| `tests/conftest.py` | Add `sim_broker`, `sim_broker_clean` fixtures; `wait_for_message` helper |
| `tests/test_engine_integration.py` | New file — 6 integration tests |
