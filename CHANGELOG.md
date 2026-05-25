# Changelog

## [Unreleased]

### Breaking

* Remove daemon mode — `arwn-collect` now runs in the foreground only.
  The `-f`, `-l`, and `-p` flags are removed. Use systemd for service management
  (install via `arwn-install-service`).
* Remove `python-daemon` and `pid` dependencies.
* Remove legacy SysV init script (`etc/arwn-daemon`).

### Added

* Automatic collector restart with exponential backoff when rtl_433 exits.
* SensorPacket test coverage (18 tests covering all sensor types).

## [3.0.0] - 2026-05-25

* Add `Config` dataclass with typed attribute access and `from_dict()` factory
* Normalize legacy config keys (`mqtt.user`→`username`, `mqtt.passwd`→`password`) with deprecation warnings
* Validate required config fields (`mqtt.server`, `names`) at startup
* Remove duplicate MQTT credential paths in `engine.py`
* Remove redundant `will_set` inside `on_connect` (paho anti-pattern)
* Remove Python 2 `(object)` boilerplate from all class definitions
* Add `SyslogIdentifier=arwn` to systemd service template
* Move Weather Underground uploads to background thread (no longer blocks MQTT message processing)
* Add timeout (10s) to Weather Underground HTTP requests
* Use `importlib.metadata.version()` instead of stale `__version__` string
* Extract `MPS2MPH` module-level constant (was duplicated inline)
* Extract `_ConfigFileHandler._reload()` to deduplicate on_modified/on_moved
* Fix unclosed file handle in `collect.py` config loading
* Fix `--piddir` help text (was incorrectly labeled "pid file name")
* Remove dead test files (`test_arwn.py`, `broker.py`, `paho_test.py`)
* Fix inverted Kelvin↔Celsius temperature conversion formula
* Fix `RTL433Collector` crash on malformed JSON and CPU spin on subprocess death
* Fix `SensorPacket.bat` stored as tuple instead of scalar
* Remove debug `logger.error()` calls from `RTL433Collector.__init__`
* Clean up noisy debug logging; promote MQTT send to INFO
* Refactor rain handlers into `RainAccumulator` class with disk-persisted state
* Add `RainEventTracker` for tracking rain events (start/end after 12h gap)
* Add `RainStateStore` for atomic JSON state persistence (~/.local/share/arwn/)
* Fix year-boundary bug in rain midnight rollover detection (`%j` → `datetime.date`)
* Fix potential crash when rain baseline is None on first packet
* Migrate paho-mqtt client API to v2 to eliminate deprecation warnings
* Migrate test_mqtt_real.py to use SimpleMQTTBroker so tests run without external mosquitto
* Fix test_mqtt_disconnect race: wait for subscriber to receive alive before forcing disconnect
* Update Python version classifiers to reflect supported range (3.10–3.14)
* Migrate build backend from setuptools to hatchling
* Replace tox with uv for local development and CI
* Add uv.lock lockfile for reproducible installs
* Fix test suite blocked by stray pytest-homeassistant-custom-component global plugin
* Add Dependabot config for weekly pip and GitHub Actions updates
* Replace black and isort with ruff for formatting and import sorting
* Enable ruff E/W/F lint rules and fix all violations (unused imports, line length)
* Remove dead `tests/arwn_fixtures.py` fixture file

## [2.1.0] - 2026-04-26

* Fix `arwn-install-service` to use lazy default for `--config` argument
* Fix `test_install_service_binary_not_found` to assert no unit file is written
* Add `arwn-install-service` CLI command to install arwn as a systemd user service
* Add `SimpleMQTTBroker` in-process MQTT broker for tests — no external mosquitto required
* Add retained message store and replay support in `SimpleMQTTBroker`
* Add will message support in `SimpleMQTTBroker`
* Add `ReceivedMessage` / `WillMessage` dataclasses and broker inspection API
* Add `sim_broker` pytest fixture and `wait_for_message` helper in `conftest.py`
* Add integration tests for engine connect/will, rain handler, and temperature routing
* Add `ConfigWatcher` for hot-reloading config via watchdog/inotify without restart
* Add thread-safe `Dispatcher.reload()` for config hot-reload
* Add watchdog runtime dependency for config file watching
* Fix config path resolved before daemon `chdir` so relative paths work correctly
* Fix atomic-rename saves (e.g. from editors like vim) now detected correctly
* Fix retained-replay scope and QoS 2 PUBREC response in `SimpleMQTTBroker`
* Fix `test_mqtt_real.py` and `mosquitto_real` fixture updated for paho 2.x / mosquitto 2.x

## [2.0.0] - 2026-03-08

* Modernize packaging to PEP 517/518/621 (`pyproject.toml`)
* Replace flake8 with black for formatting; add isort
* Convert test suite from unittest/testtools to pytest
* Add GitHub Actions CI workflow
* Update `.gitignore` for modern Python development

## [1.1.0] - 2025-01-03

* Add MQTT username/password support

## [1.0.0] - 2024-03-09

* Add Acurite rain sensor support
* Initial 433 MHz weather sensor collection and MQTT publish
