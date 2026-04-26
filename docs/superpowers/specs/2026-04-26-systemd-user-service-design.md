# systemd User Service Installation Design

## Goal

Replace `install.sh` with a pip-native `arwn-install-service` CLI command that installs arwn as a user-level systemd service that starts at boot and survives logout, without requiring `sudo`.

## Architecture

A unit file template ships as package data in `arwn/data/arwn.service.template`. A new CLI entry point `arwn-install-service` (`arwn/cmd/install_service.py`) reads the template via `importlib.resources`, resolves the `arwn-collect` binary with `shutil.which`, renders the template, writes the unit file to `~/.config/systemd/user/arwn.service`, then enables and starts the service via `systemctl --user`. `loginctl enable-linger` is run unconditionally so the service starts at boot and survives logout.

## Components

### `arwn/data/arwn.service.template`

```ini
[Unit]
Description=ARWN Collector

[Service]
ExecStart={arwn_collect} -f -c {config}
Type=simple
Restart=always

[Install]
WantedBy=default.target
```

Two substitution variables:
- `{arwn_collect}` — absolute path to the `arwn-collect` binary, resolved at install time via `shutil.which`
- `{config}` — absolute path to config file, defaults to `~/.config/arwn/config.yml`, overridable via `--config`

`WantedBy=default.target` is the correct target for user-level services. `-f` runs arwn in foreground mode (no double-daemonize under systemd).

### `arwn/cmd/install_service.py`

CLI entry point registered as `arwn-install-service` in `pyproject.toml`. Steps:

1. Resolve `arwn-collect` absolute path via `shutil.which` — print a clear error and exit non-zero if not found
2. Accept `--config` argument (default `~/.config/arwn/config.yml`) and expand to absolute path
3. Create `~/.config/systemd/user/` if it does not exist
4. Read template via `importlib.resources.files("arwn.data").joinpath("arwn.service.template").read_text()`
5. Render template with `str.format(arwn_collect=..., config=...)`
6. Write rendered unit to `~/.config/systemd/user/arwn.service`
7. Run `systemctl --user daemon-reload`
8. Run `systemctl --user enable --now arwn`
9. Run `loginctl enable-linger <current user>` (via `getpass.getuser()`)
10. Print success summary

### `arwn/data/__init__.py`

Empty file to make `arwn.data` a package, required for `importlib.resources` traversal.

### `pyproject.toml` changes

- Add `arwn-install-service = "arwn.cmd.install_service:main"` to `[project.scripts]`
- Add `arwn/data/*.template` to package data includes

### `tests/test_install_service.py`

Two test cases, both using `unittest.mock.patch`:

**Happy path:** mock `shutil.which` returning `/usr/bin/arwn-collect`, mock `subprocess.run` returning success, mock filesystem writes. Assert unit file content matches expected rendered output, assert all three subprocess calls were made with correct arguments.

**Binary not found:** mock `shutil.which` returning `None`. Assert exit code is non-zero, assert no files were written, assert no subprocess calls were made.

## Installation Instructions (to add to README.md)

```bash
# Add yourself to the dialout group (required for RFXCOM USB, one-time)
sudo usermod -aG dialout $USER
# Log out and back in for group change to take effect

# Install arwn
pip install arwn

# Install and start the systemd user service
arwn-install-service --config ~/.config/arwn/config.yml
```

The service will start at boot and restart automatically on failure.

## Files Changed

| Action | File |
|--------|------|
| Create | `arwn/data/__init__.py` |
| Create | `arwn/data/arwn.service.template` |
| Create | `arwn/cmd/install_service.py` |
| Create | `tests/test_install_service.py` |
| Modify | `pyproject.toml` — add entry point + package data |
| Modify | `README.md` — update installation instructions |
| Delete | `install.sh` |
