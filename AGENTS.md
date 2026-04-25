# ARWN Agent Guide

ARWN (Ambient Radio Weather Network) collects 433MHz wireless weather sensor
data via RFXCOM USB receivers or RTL-SDR dongles, then publishes it over MQTT.

## Setup

```bash
pip install -e ".[dev]"
```

## Testing

Run the full test suite before committing:

```bash
tox -e py314
```

Run a single test file or individual test:

```bash
tox -e py314 -- tests/test_handlers.py
tox -e py314 -- tests/test_handlers.py::TestClass::test_method
```

With coverage:

```bash
tox -e coverage
```

## Linting

Run both checks before committing:

```bash
tox -e lint
```

To auto-fix:

```bash
black arwn tests
isort arwn tests
```

## Project Structure

```
arwn/
  engine.py       - Core: SensorPacket, MQTT client, RFXCOMCollector, RTL433Collector, Dispatcher
  handlers.py     - MQTT event handlers: rain tracking, Weather Underground reporting
  temperature.py  - Temperature unit conversions (F/C/K) and dewpoint calculation
  cmd/collect.py  - CLI entry point (arwn-collect command)
  vendor/RFXtrx/  - Vendored RFXtrx protocol library for RFXCOM USB devices
tests/
  conftest.py           - Shared pytest fixtures
  test_arwn_collect.py  - CLI tests
  test_handlers.py      - Rain calculation handler tests (boundary cases: midnight, new year)
  test_mqtt.py          - MQTT integration tests
```

## Key Architecture

- **Collectors** (`RFXCOMCollector`, `RTL433Collector`) implement `__iter__`/`__next__`
  to yield raw sensor packets from hardware or subprocess.
- **SensorPacket** normalizes packets from either collector into a unified JSON
  structure with unit conversions.
- **Dispatcher** connects a collector to MQTT, publishing each packet and routing
  incoming MQTT messages to registered handlers.
- **Handlers** (`MQTTAction` subclasses) maintain stateful rain totals with
  rollover logic for midnight and new-year boundaries.
- Sensor capabilities are identified via bitflags (`IS_TEMP`, `IS_HUMIDITY`, etc.).

## Config Hot-Reload

The daemon watches `config.yml` for changes via `watchdog` (inotify on Linux).
When the file is modified — including atomic-rename saves used by most editors —
`ConfigWatcher` re-reads it and calls `Dispatcher.reload()`, which updates
`self.names` under a lock.

Only `names` (sensor name mappings) is reloaded at runtime. Changes to
`collector` or `mqtt` require a full restart.

## Configuration

Copy `config.yml.sample` to `config.yml`. Key fields:

- `collector`: `rtl433` or `rfxcom`
- `mqtt`: broker host/port
- `sensors`: friendly name mappings
- `wunderground`: optional Weather Underground credentials

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs lint, pytest on Python 3.10–3.14,
and build verification on every push. PyPI publish triggers on tags via OIDC.
