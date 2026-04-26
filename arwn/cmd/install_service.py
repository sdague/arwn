import argparse
import getpass
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Install arwn as a systemd user service"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="path to arwn config file (default: ~/.config/arwn/config.yml)",
    )
    opts = parser.parse_args(args)

    arwn_collect = shutil.which("arwn-collect")
    if arwn_collect is None:
        print(
            "Error: arwn-collect not found in PATH. Is arwn installed?",
            file=sys.stderr,
        )
        sys.exit(1)

    config_raw = opts.config or str(Path.home() / ".config" / "arwn" / "config.yml")
    config = str(Path(config_raw).expanduser().resolve())

    template = (
        files("arwn.data").joinpath("arwn.service.template").read_text(encoding="utf-8")
    )
    unit_content = template.format(arwn_collect=arwn_collect, config=config)

    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    unit_file = unit_dir / "arwn.service"
    unit_file.write_text(unit_content, encoding="utf-8")
    print(f"Written: {unit_file}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "arwn"], check=True)
    subprocess.run(["loginctl", "enable-linger", getpass.getuser()], check=True)

    print("arwn service installed and started.")
    print("It will start automatically at boot and after logout.")
