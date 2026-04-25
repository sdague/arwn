# MQTT Simulation Broker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `SimpleMQTTBroker` with retained messages, will messages, QoS 1 PUBACK, and an inspection API, then add a `sim_broker` pytest fixture and six integration tests that exercise the full engine → broker → handler roundtrip without requiring an external mosquitto process.

**Architecture:** Three additive changes to `tests/mqtt_broker.py` (retained store, will handling, PUBACK), a `SimBrokerHandle` dataclass plus two fixtures and a `wait_for_message` helper in `tests/conftest.py`, and a new `tests/test_engine_integration.py` with six tests. No new files in the production `arwn/` package.

**Tech Stack:** Python 3.8+, paho-mqtt, pytest, threading (already used throughout)

---

## File Map

| File | Change |
|------|--------|
| `tests/mqtt_broker.py` | Add `ReceivedMessage` dataclass, `WillMessage` dataclass, retained store, will registration, QoS 1 PUBACK, inspection API (`self.messages`, `self.retained`, `self.wills`) |
| `tests/conftest.py` | Add `SimBrokerHandle` dataclass, `sim_broker` fixture (module-scoped), `sim_broker_clean` fixture (function-scoped), `wait_for_message` helper |
| `tests/test_engine_integration.py` | New — 6 integration tests |

---

### Task 1: Add `ReceivedMessage` and `WillMessage` dataclasses + inspection API skeleton

**Files:**
- Modify: `tests/mqtt_broker.py`

The broker currently has no `messages` list or `retained` dict. This task adds the data structures and wires `messages` recording into `_route_message`. No behaviour changes yet — just the skeleton needed by all later tasks.

- [ ] **Step 1: Add dataclasses and initialize inspection state in `__init__`**

At the top of `tests/mqtt_broker.py`, after the existing imports, add:

```python
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
```

After the `import` block and before the `SimpleMQTTBroker` class definition, add:

```python
@dataclass
class ReceivedMessage:
    topic: str
    payload: bytes
    retain: bool
    qos: int
    timestamp: float


@dataclass
class WillMessage:
    topic: str
    payload: bytes
    retain: bool
    qos: int
```

In `SimpleMQTTBroker.__init__`, after the existing `self.subscriptions = {}` line, add:

```python
self.messages: List[ReceivedMessage] = []
self.retained: Dict[str, bytes] = {}
self.wills: Dict[object, WillMessage] = {}
self._messages_lock = threading.Lock()
```

- [ ] **Step 2: Record every published message in `_route_message`**

At the top of `_route_message`, before the existing packet-building code, add:

```python
retain_flag = False  # will be set properly in Task 2; placeholder for now
qos_val = 0
with self._messages_lock:
    self.messages.append(
        ReceivedMessage(
            topic=topic,
            payload=payload,
            retain=retain_flag,
            qos=qos_val,
            timestamp=time.monotonic(),
        )
    )
```

- [ ] **Step 3: Run existing tests to confirm nothing broke**

```bash
pytest tests/test_mqtt.py -v
```

Expected: same results as before (currently 5 passing tests).

- [ ] **Step 4: Commit**

```bash
git add tests/mqtt_broker.py
git commit -m "feat: add ReceivedMessage/WillMessage dataclasses and inspection API skeleton"
```

---

### Task 2: Add retained message store

**Files:**
- Modify: `tests/mqtt_broker.py`

MQTT retained messages: when a PUBLISH arrives with the retain bit set (bit 0 of the first header byte), store the payload under that exact topic. On SUBSCRIBE, immediately replay any stored retained messages whose topics match the new subscription. An empty-payload retained publish clears the topic.

The current `_handle_connection` PUBLISH handler reads `data[0] >> 4` for packet type but discards the retain bit (`data[0] & 0x01`) and QoS bits. This task extracts those flags.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sim_broker.py` (unit tests for the broker itself):

```python
"""Unit tests for SimpleMQTTBroker enhancements."""
import json
import time

import paho.mqtt.client as mqtt
import pytest

from tests.mqtt_broker import SimpleMQTTBroker


@pytest.fixture
def broker():
    b = SimpleMQTTBroker()
    b.start()
    yield b
    b.stop()


def connect_client(port):
    """Return a connected, looping paho client."""
    c = mqtt.Client()
    c.connect("localhost", port)
    c.loop_start()
    time.sleep(0.15)
    return c


def test_retained_message_stored(broker):
    """Publishing with retain=True stores payload in broker.retained."""
    c = connect_client(broker.port)
    c.publish("arwn/status", json.dumps({"status": "alive"}), retain=True)
    time.sleep(0.2)
    c.loop_stop()
    c.disconnect()

    assert "arwn/status" in broker.retained
    payload = json.loads(broker.retained["arwn/status"])
    assert payload["status"] == "alive"


def test_retained_message_replayed_on_subscribe(broker):
    """A subscriber receives retained messages immediately on subscribe."""
    # Publish retained before subscriber connects
    pub = connect_client(broker.port)
    pub.publish("arwn/totals/rain", json.dumps({"total": 1.5}), retain=True)
    time.sleep(0.2)
    pub.loop_stop()
    pub.disconnect()

    received = []

    def on_message(client, userdata, msg):
        received.append((msg.topic, json.loads(msg.payload)))

    sub = mqtt.Client()
    sub.on_message = on_message
    sub.connect("localhost", broker.port)
    sub.subscribe("arwn/#")
    sub.loop_start()
    time.sleep(0.3)
    sub.loop_stop()
    sub.disconnect()

    assert any(t == "arwn/totals/rain" for t, _ in received), \
        f"Retained message not replayed. Received: {received}"


def test_empty_retained_clears_topic(broker):
    """Publishing empty payload with retain=True removes the stored message."""
    c = connect_client(broker.port)
    c.publish("arwn/status", json.dumps({"status": "alive"}), retain=True)
    time.sleep(0.15)
    c.publish("arwn/status", b"", retain=True)
    time.sleep(0.15)
    c.loop_stop()
    c.disconnect()

    assert "arwn/status" not in broker.retained
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_sim_broker.py -v
```

Expected: `FAILED` — retained messages not yet stored or replayed.

- [ ] **Step 3: Extract retain bit and QoS in `_handle_connection` PUBLISH block**

In `_handle_connection`, the PUBLISH block starts with `elif packet_type == 3:`. Replace it with:

```python
elif packet_type == 3:
    retain_flag = bool(data[0] & 0x01)
    qos_val = (data[0] >> 1) & 0x03
    remaining = self._read_remaining_length(conn)
    if remaining > 0:
        publish_data = conn.recv(remaining)
        if len(publish_data) >= 2:
            topic_len = struct.unpack("!H", publish_data[:2])[0]
            if len(publish_data) >= 2 + topic_len:
                topic = publish_data[2 : 2 + topic_len].decode("utf-8")
                offset = 2 + topic_len
                # Skip packet ID for QoS 1/2
                if qos_val > 0:
                    packet_id = struct.unpack("!H", publish_data[offset : offset + 2])[0]
                    offset += 2
                else:
                    packet_id = None
                payload = publish_data[offset:]
                self._route_message(topic, payload, conn, retain_flag, qos_val)
                # Send PUBACK for QoS 1 or 2
                if qos_val >= 1 and packet_id is not None:
                    puback = struct.pack("!BBH", 0x40, 0x02, packet_id)
                    try:
                        conn.send(puback)
                    except Exception:
                        pass
```

- [ ] **Step 4: Update `_route_message` signature and retained store**

Replace the existing `_route_message` definition with:

```python
def _route_message(self, topic, payload, sender_conn, retain=False, qos=0):
    """Route a published message to all matching subscribers."""
    # Update retained store
    if retain:
        if payload:
            self.retained[topic] = payload
        else:
            self.retained.pop(topic, None)

    # Record in inspection list
    with self._messages_lock:
        self.messages.append(
            ReceivedMessage(
                topic=topic,
                payload=payload,
                retain=retain,
                qos=qos,
                timestamp=time.monotonic(),
            )
        )

    # Build PUBLISH packet (QoS 0 delivery to subscribers)
    topic_bytes = topic.encode("utf-8")
    topic_len = struct.pack("!H", len(topic_bytes))
    remaining_length = 2 + len(topic_bytes) + len(payload)
    remaining_bytes = []
    while True:
        byte = remaining_length % 128
        remaining_length = remaining_length // 128
        if remaining_length > 0:
            byte |= 0x80
        remaining_bytes.append(byte)
        if remaining_length == 0:
            break
    publish_packet = (
        bytes([0x30]) + bytes(remaining_bytes) + topic_len + topic_bytes + payload
    )

    # Send to all matching subscribers (except sender)
    for conn, filters in list(self.subscriptions.items()):
        if conn == sender_conn:
            continue
        for topic_filter in filters:
            if self._topic_matches(topic_filter, topic):
                try:
                    conn.send(publish_packet)
                except Exception:
                    pass
                break
```

Also remove the placeholder recording added in Task 1 Step 2 (it's now handled in this updated `_route_message`).

- [ ] **Step 5: Add retained replay in SUBSCRIBE handler**

In `_handle_connection`, find the SUBSCRIBE block. After `conn.send(suback)`, add:

```python
# Replay matching retained messages
for ret_topic, ret_payload in list(self.retained.items()):
    if self._topic_matches(topic_filter, ret_topic):
        ret_topic_bytes = ret_topic.encode("utf-8")
        ret_topic_len_bytes = struct.pack("!H", len(ret_topic_bytes))
        # Set retain bit in fixed header: 0x31
        rem_len = 2 + len(ret_topic_bytes) + len(ret_payload)
        rem_bytes = []
        while True:
            byte = rem_len % 128
            rem_len = rem_len // 128
            if rem_len > 0:
                byte |= 0x80
            rem_bytes.append(byte)
            if rem_len == 0:
                break
        retained_packet = (
            bytes([0x31])
            + bytes(rem_bytes)
            + ret_topic_len_bytes
            + ret_topic_bytes
            + ret_payload
        )
        try:
            conn.send(retained_packet)
        except Exception:
            pass
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_sim_broker.py -v
```

Expected: all 3 new tests PASS.

- [ ] **Step 7: Run full suite**

```bash
pytest tests/test_mqtt.py tests/test_sim_broker.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add tests/mqtt_broker.py tests/test_sim_broker.py
git commit -m "feat: add retained message store and replay to SimpleMQTTBroker"
```

---

### Task 3: Add will message support

**Files:**
- Modify: `tests/mqtt_broker.py`

MQTT will messages: the CONNECT packet can carry a "will" — a topic/payload to publish if the client disconnects without sending DISCONNECT. The broker must parse the will from CONNECT, store it per connection, publish it on unclean socket close, and discard it on clean DISCONNECT.

The current CONNECT handler discards everything after the fixed header (`conn.recv(remaining)`). This task replaces that with real parsing.

CONNECT payload layout (MQTT 3.1.1):
- 2 bytes: protocol name length (always 4)
- 4 bytes: "MQTT"
- 1 byte: protocol level (4 = MQTT 3.1.1)
- 1 byte: connect flags
- 2 bytes: keep-alive
- Then variable header fields in order: client ID, [will topic, will payload if will flag set], [username if flag], [password if flag]

Connect flags byte:
- bit 2: will flag
- bit 3: will QoS low bit
- bit 4: will QoS high bit
- bit 5: will retain
- bit 6: password flag
- bit 7: username flag

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sim_broker.py`:

```python
def test_will_published_on_unclean_disconnect(broker):
    """Will message is published when client socket is force-closed."""
    import socket as _socket

    will_received = []

    # Observer subscribes to arwn/status before the will fires
    obs = mqtt.Client()
    obs.on_message = lambda c, u, m: will_received.append(
        (m.topic, json.loads(m.payload))
    )
    obs.connect("localhost", broker.port)
    obs.subscribe("arwn/#")
    obs.loop_start()
    time.sleep(0.15)

    # Connect a client with a will
    victim = mqtt.Client()
    victim.will_set("arwn/status", json.dumps({"status": "dead"}), retain=True)
    victim.connect("localhost", broker.port)
    victim.loop_start()
    time.sleep(0.15)

    # Force-close without DISCONNECT
    victim.loop_stop(force=True)
    victim._sock.close() if hasattr(victim, "_sock") else None
    # Access the underlying socket via paho internals
    try:
        victim._sock.shutdown(_socket.SHUT_RDWR)
    except Exception:
        pass

    time.sleep(0.5)

    obs.loop_stop()
    obs.disconnect()

    assert any(
        t == "arwn/status" and p.get("status") == "dead"
        for t, p in will_received
    ), f"Will not received. Got: {will_received}"
    # Also check retained store was updated
    assert "arwn/status" in broker.retained


def test_will_not_published_on_clean_disconnect(broker):
    """Will message is NOT published when client disconnects cleanly."""
    c = mqtt.Client()
    c.will_set("arwn/status", json.dumps({"status": "dead"}), retain=True)
    c.connect("localhost", broker.port)
    c.loop_start()
    time.sleep(0.15)
    c.disconnect()  # clean disconnect
    time.sleep(0.3)

    # Will should NOT be in retained
    assert "arwn/status" not in broker.retained
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_sim_broker.py::test_will_published_on_unclean_disconnect tests/test_sim_broker.py::test_will_not_published_on_clean_disconnect -v
```

Expected: both FAIL.

- [ ] **Step 3: Replace CONNECT handler with will-parsing version**

In `_handle_connection`, replace the entire `if packet_type == 1:` block with:

```python
if packet_type == 1:
    remaining = self._read_remaining_length(conn)
    connect_data = conn.recv(remaining) if remaining > 0 else b""
    will = self._parse_will(connect_data, conn)
    if will:
        self.wills[conn] = will
    connack = struct.pack("!BBBB", 0x20, 0x02, 0x00, 0x00)
    conn.send(connack)
```

- [ ] **Step 4: Add `_parse_will` method to `SimpleMQTTBroker`**

Add after `_read_remaining_length`:

```python
def _parse_will(self, connect_data, conn):
    """Parse will message from a CONNECT packet payload. Returns WillMessage or None."""
    try:
        # Skip protocol name (2-byte length + "MQTT")
        proto_len = struct.unpack("!H", connect_data[:2])[0]
        offset = 2 + proto_len  # skip "MQTT"
        # protocol level (1 byte) + connect flags (1 byte) + keep-alive (2 bytes)
        offset += 1  # protocol level
        connect_flags = connect_data[offset]
        offset += 1  # connect flags
        offset += 2  # keep-alive

        will_flag = bool(connect_flags & 0x04)
        will_qos = (connect_flags >> 3) & 0x03
        will_retain = bool(connect_flags & 0x20)

        # Skip client ID
        client_id_len = struct.unpack("!H", connect_data[offset : offset + 2])[0]
        offset += 2 + client_id_len

        if not will_flag:
            return None

        # Will topic
        will_topic_len = struct.unpack("!H", connect_data[offset : offset + 2])[0]
        offset += 2
        will_topic = connect_data[offset : offset + will_topic_len].decode("utf-8")
        offset += will_topic_len

        # Will payload
        will_payload_len = struct.unpack("!H", connect_data[offset : offset + 2])[0]
        offset += 2
        will_payload = connect_data[offset : offset + will_payload_len]

        return WillMessage(
            topic=will_topic,
            payload=will_payload,
            retain=will_retain,
            qos=will_qos,
        )
    except Exception:
        return None
```

- [ ] **Step 5: Fire will on unclean disconnect, clear on clean DISCONNECT**

In `_handle_connection`, the `finally` block currently just closes the socket. Replace the whole `finally` block:

```python
finally:
    # Determine if this was a clean disconnect
    # (clean = DISCONNECT packet was received, which sets a flag)
    # We use a local variable `clean_disconnect` set in the DISCONNECT handler
    if not clean_disconnect:
        will = self.wills.pop(conn, None)
        if will:
            self._route_message(
                will.topic, will.payload, conn,
                retain=will.retain, qos=will.qos
            )
    else:
        self.wills.pop(conn, None)
    try:
        conn.close()
    except Exception:
        pass
```

To make `clean_disconnect` work, add it as a local variable at the top of `_handle_connection`, just inside the `try:` block, before the `while self.running:` loop:

```python
clean_disconnect = False
```

And in the DISCONNECT handler (currently just `break`), set the flag first:

```python
elif packet_type == 14:
    clean_disconnect = True
    break
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_sim_broker.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 7: Run full suite**

```bash
pytest tests/test_mqtt.py tests/test_sim_broker.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add tests/mqtt_broker.py tests/test_sim_broker.py
git commit -m "feat: add will message support to SimpleMQTTBroker"
```

---

### Task 4: Add `sim_broker` fixtures and `wait_for_message` helper to `conftest.py`

**Files:**
- Modify: `tests/conftest.py`

This task adds the `SimBrokerHandle` dataclass, two fixtures, and the `wait_for_message` helper that integration tests will use for all synchronisation (no `time.sleep` in integration tests).

- [ ] **Step 1: Write the failing test**

Add a new file `tests/test_sim_broker_fixture.py` to test the fixtures themselves:

```python
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
    from tests.mqtt_broker import ReceivedMessage
    # sim_broker_clean should have cleared any prior messages
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
    import pytest

    with pytest.raises(TimeoutError, match="arwn/never"):
        wait_for_message(sim_broker.broker, "arwn/never", timeout=0.3)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_sim_broker_fixture.py -v
```

Expected: `FAILED` — `sim_broker` fixture not defined.

- [ ] **Step 3: Add `SimBrokerHandle`, fixtures, and `wait_for_message` to `conftest.py`**

Add these imports at the top of `tests/conftest.py`:

```python
import re
from dataclasses import dataclass
from typing import Optional, Union
```

Add `SimpleMQTTBroker` import:

```python
from tests.mqtt_broker import ReceivedMessage, SimpleMQTTBroker
```

Add after the existing imports:

```python
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
    yield


def wait_for_message(
    broker: SimpleMQTTBroker,
    pattern: Union[str, "re.Pattern"],
    timeout: float = 2.0,
) -> ReceivedMessage:
    """Poll broker.messages until a message matching pattern arrives.

    pattern: str  → exact topic prefix match (topic.startswith(pattern))
    pattern: re.Pattern → full regex match against topic

    Raises TimeoutError if no matching message arrives within timeout seconds.
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
    raise TimeoutError(
        f"No message matching {pattern!r} arrived within {timeout}s. "
        f"Topics seen: {[m.topic for m in broker.messages]}"
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_sim_broker_fixture.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest tests/test_mqtt.py tests/test_sim_broker.py tests/test_sim_broker_fixture.py -v
```

Expected: all pass.

- [ ] **Step 6: Run linting**

```bash
black --check tests/conftest.py tests/mqtt_broker.py
isort --check-only tests/conftest.py tests/mqtt_broker.py
```

Fix with `black tests/conftest.py tests/mqtt_broker.py && isort tests/conftest.py tests/mqtt_broker.py` if needed.

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py tests/test_sim_broker_fixture.py
git commit -m "feat: add sim_broker fixture and wait_for_message helper to conftest"
```

---

### Task 5: Integration tests — engine connect and status lifecycle

**Files:**
- Create: `tests/test_engine_integration.py`

This task adds the first two integration tests: status-alive-with-retain on connect, and will-published-on-unclean-disconnect. Both test behaviors that the current mock-based tests cannot reach.

Key context:
- `engine.MQTT.__init__` calls `handlers.setup()` which resets global handler state — call it before creating `engine.MQTT` in tests
- `engine.MQTT` calls `client.loop_start()` internally — do not call it again
- To force-close paho's socket without a clean DISCONNECT, access `mq.client._sock` (paho internals)
- After force-close, the broker detects the socket EOF and fires the will

- [ ] **Step 1: Create `tests/test_engine_integration.py` with the first two tests**

```python
"""Integration tests: engine <-> SimpleMQTTBroker roundtrip."""
import json
import socket
import time

import pytest

from arwn import engine, handlers
from tests.conftest import wait_for_message


def make_config(port):
    return {
        "mqtt": {"server": "localhost", "port": port},
        "names": {},
        "collector": {"type": "rfxcom", "device": "/dev/null"},
    }


def test_status_alive_published_with_retain(sim_broker, sim_broker_clean):
    """engine.MQTT publishes arwn/status with retain=True on connect."""
    handlers.setup()
    mq = engine.MQTT("localhost", make_config(sim_broker.port), port=sim_broker.port)
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
    mq = engine.MQTT("localhost", make_config(sim_broker.port), port=sim_broker.port)

    # Wait for initial connect and status=alive
    wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
    sim_broker.broker.messages.clear()

    # Force-close the paho socket without sending DISCONNECT
    mq.client.loop_stop(force=True)
    try:
        mq.client._sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    try:
        mq.client._sock.close()
    except Exception:
        pass

    # Broker should detect EOF and fire the will
    wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
    payload = json.loads(sim_broker.broker.retained["arwn/status"])
    assert payload["status"] == "dead"
```

- [ ] **Step 2: Run the two new tests**

```bash
pytest tests/test_engine_integration.py -v
```

Expected: both PASS.

- [ ] **Step 3: Run full suite**

```bash
pytest -v --ignore=tests/test_mqtt_real.py
```

Expected: all pass (real mosquitto tests are excluded).

- [ ] **Step 4: Commit**

```bash
git add tests/test_engine_integration.py
git commit -m "test: add engine connect and will integration tests"
```

---

### Task 6: Integration tests — rain sensor and handler roundtrip

**Files:**
- Modify: `tests/test_engine_integration.py`

This task adds four more integration tests covering the rain and temperature sensor flows. The rain handler chain relies on global state (`LAST_RAIN_TOTAL`, `LAST_RAIN`, `PREV_RAIN`) that is reset by `handlers.setup()` — each test calls that.

For Test 4 (`test_rain_handler_computes_today_total`), the `TodaysRain` handler only fires if `LAST_RAIN_TOTAL` is already set (from a prior `arwn/totals/rain` message). The setup is: first publish a rain total to seed `LAST_RAIN_TOTAL` (via `InitializeLastRainIfNotThere`), then publish a rain reading and wait for `arwn/rain/today`.

For Test 6 (`test_temperature_sensor_routes_by_name`), `engine.Dispatcher` is used directly. `Dispatcher.__init__` calls `_get_collector` which tries to open a real device — patch `RFXCOMCollector` to avoid that.

- [ ] **Step 1: Add four more tests to `tests/test_engine_integration.py`**

Add these imports at the top of the existing file:

```python
from unittest.mock import patch

from arwn.engine import IS_RAIN, IS_TEMP, IS_HUMID, SensorPacket
```

Then append the four tests:

```python
def test_rain_sensor_publishes_to_rain_topic(sim_broker, sim_broker_clean):
    """Dispatcher.mqtt.send('rain', ...) results in a message on arwn/rain."""
    handlers.setup()
    mq = engine.MQTT("localhost", make_config(sim_broker.port), port=sim_broker.port)
    wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)

    try:
        payload = {"total": 2.45, "units": "in", "timestamp": 1700000000}
        mq.send("rain", payload)
        msg = wait_for_message(sim_broker.broker, "arwn/rain", timeout=2.0)
        data = json.loads(msg.payload)
        assert data["total"] == 2.45
        assert data["units"] == "in"
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()


def test_rain_handler_computes_today_total(sim_broker, sim_broker_clean):
    """Publishing arwn/rain triggers TodaysRain handler → arwn/rain/today."""
    handlers.setup()
    mq = engine.MQTT("localhost", make_config(sim_broker.port), port=sim_broker.port)
    wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)

    try:
        # Seed LAST_RAIN_TOTAL by publishing a retained totals message
        # InitializeLastRainIfNotThere fires when arwn/rain arrives and
        # LAST_RAIN_TOTAL is None — it publishes arwn/totals/rain (retained).
        # Then TodaysRain fires on the next arwn/rain message.
        ts = 1700000000
        rain_payload = json.dumps({"total": 1.0, "units": "in", "timestamp": ts})
        # First rain message seeds LAST_RAIN_TOTAL
        mq.client.publish("arwn/rain", rain_payload)
        wait_for_message(sim_broker.broker, "arwn/totals/rain", timeout=2.0)
        sim_broker.broker.messages.clear()

        # Second rain message triggers TodaysRain
        rain_payload2 = json.dumps({"total": 1.2, "units": "in", "timestamp": ts + 10})
        mq.client.publish("arwn/rain", rain_payload2)
        msg = wait_for_message(sim_broker.broker, "arwn/rain/today", timeout=2.0)
        data = json.loads(msg.payload)
        assert "since_midnight" in data
    finally:
        mq.client.loop_stop()
        mq.client.disconnect()


def test_retained_rain_total_replayed_on_reconnect(sim_broker, sim_broker_clean):
    """A retained arwn/totals/rain message is replayed to a new subscriber."""
    # Publish a retained total directly via a plain paho client
    import paho.mqtt.client as mqtt_client

    pub = mqtt_client.Client()
    pub.connect(sim_broker.host, sim_broker.port)
    pub.loop_start()
    time.sleep(0.15)
    pub.publish(
        "arwn/totals/rain",
        json.dumps({"total": 3.1, "units": "in", "timestamp": 1700000000}),
        retain=True,
    )
    time.sleep(0.2)
    pub.loop_stop()
    pub.disconnect()

    # New subscriber should receive the retained message immediately
    received = []

    def on_msg(c, u, m):
        received.append((m.topic, json.loads(m.payload)))

    sub = mqtt_client.Client()
    sub.on_message = on_msg
    sub.connect(sim_broker.host, sim_broker.port)
    sub.subscribe("arwn/#")
    sub.loop_start()
    time.sleep(0.4)
    sub.loop_stop()
    sub.disconnect()

    assert any(
        t == "arwn/totals/rain" and p.get("total") == 3.1
        for t, p in received
    ), f"Retained total not replayed. Received: {received}"


def test_temperature_sensor_routes_by_name(sim_broker, sim_broker_clean):
    """A temp packet with a known sensor_id appears on arwn/temperature/<name>."""
    config = make_config(sim_broker.port)
    config["names"] = {"aa:01": "outside"}
    handlers.setup()

    with patch("arwn.engine.RFXCOMCollector"):
        dispatcher = engine.Dispatcher(config)

    try:
        wait_for_message(sim_broker.broker, "arwn/status", timeout=2.0)
        sim_broker.broker.messages.clear()

        now = int(time.time())
        packet = SensorPacket(stype=IS_TEMP | IS_HUMID, sensor_id="aa:01")
        packet.data = {"temp": 72.5, "humid": 55.0, "dewpoint": 54.2, "units": "F"}
        dispatcher.mqtt.send(
            "temperature/outside", packet.as_json(timestamp=now)
        )

        msg = wait_for_message(
            sim_broker.broker, "arwn/temperature/outside", timeout=2.0
        )
        data = json.loads(msg.payload)
        assert data["temp"] == 72.5
        assert data["humid"] == 55.0
    finally:
        dispatcher.mqtt.client.loop_stop()
        dispatcher.mqtt.client.disconnect()
```

- [ ] **Step 2: Run all integration tests**

```bash
pytest tests/test_engine_integration.py -v
```

Expected: all 6 PASS.

- [ ] **Step 3: Run full suite excluding real mosquitto tests**

```bash
pytest --ignore=tests/test_mqtt_real.py -v
```

Expected: all pass.

- [ ] **Step 4: Run linting**

```bash
black --check tests/
isort --check-only tests/
```

Fix with `black tests/ && isort tests/` if needed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_engine_integration.py
git commit -m "test: add rain handler and temperature routing integration tests"
```

---

### Task 7: Final verification and lint

- [ ] **Step 1: Verify full test suite excluding real mosquitto (optional)**

```bash
pytest --ignore=tests/test_mqtt_real.py
```

Expected: all pass. Real mosquitto tests (`test_mqtt_real.py`) can be run separately with `pytest tests/test_mqtt_real.py` when mosquitto is installed.

- [ ] **Step 3: Final lint check**

```bash
black --check arwn tests
isort --check-only arwn tests
```

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: final lint cleanup for MQTT sim broker feature"
```
