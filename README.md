# Ambient Radio Weather Network (arwn)

[![PyPI version](https://img.shields.io/pypi/v/arwn.svg)](https://pypi.python.org/pypi/arwn)
[![CI](https://github.com/sdague/arwn/actions/workflows/ci.yml/badge.svg)](https://github.com/sdague/arwn/actions/workflows/ci.yml)

Collect 433 MHz weather sensor data and publish to MQTT.

Designed to work with an [RFXCOM](http://www.rfxcom.com/) USB receiver or an
[RTL-SDR](https://www.rtl-sdr.com/) dongle, publishing sensor readings over
MQTT so they can be consumed by other software such as
[Home Assistant](https://www.home-assistant.io/).

## Hardware Requirements

You will need a Linux system (a Raspberry Pi 3 or later is sufficient) and a
433 MHz receiver:

* **RTL-SDR dongle** (~$25 on Amazon) — recommended default. Requires
  [rtl_433](https://github.com/merbanan/rtl_433) installed separately.
* **RFXCOM receiver** — more expensive, narrower sensor support, better
  hardware error correction. All supporting software is bundled.

## Installation

### Install rtl_433 (RTL-SDR users only)

Follow the [rtl_433 installation instructions](https://github.com/merbanan/rtl_433#installation).
On Debian/Ubuntu a package is available:

```bash
sudo apt-get install rtl-433
```

### Install arwn

```bash
pip install arwn
```

## Configuration

Copy `config.yml.sample` to `config.yml` and edit:

```yaml
collector:
  type: rtl433        # or rfxcom
  # device: /dev/ttyUSB0   # rfxcom only

mqtt:
  server: 192.168.1.x
  # username: user
  # password: pass

# Optional: Weather Underground reporting
wunderground:
  user: your@email.com
  station: KXXYYY123
  passwd: yourpassword

# Map hardware sensor IDs to friendly names.
# IDs survive battery changes when named here.
# An "Outside" sensor is required for Weather Underground.
names:
  "ae:01": Outside
  "e9:00": Living Room
```

## Running as a systemd service (recommended)

Install and enable the systemd user service:

```bash
arwn-install-service --config ~/.config/arwn/config.yml
```

The service will start immediately, start at boot, and restart automatically on
failure. No `sudo` required.

To check status:

```bash
systemctl --user status arwn
journalctl --user -u arwn -f
```

### RFXCOM USB access

If using an RFXCOM receiver, add yourself to the `dialout` group (one-time):

```bash
sudo usermod -aG dialout $USER
```

Log out and back in for the change to take effect, then re-run
`arwn-install-service`.

## Running manually

```bash
arwn-collect -f --config config.yml
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Credits

Sean Dague
