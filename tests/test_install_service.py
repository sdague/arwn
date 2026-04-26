import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from arwn.cmd.install_service import main


def test_install_service_happy_path(tmp_path):
    config_path = str(tmp_path / ".config" / "arwn" / "config.yml")

    with (
        patch(
            "arwn.cmd.install_service.shutil.which",
            return_value="/usr/bin/arwn-collect",
        ),
        patch("arwn.cmd.install_service.Path.home", return_value=tmp_path),
        patch("arwn.cmd.install_service.getpass.getuser", return_value="testuser"),
        patch("arwn.cmd.install_service.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        main(["--config", config_path])

    unit_file = tmp_path / ".config" / "systemd" / "user" / "arwn.service"
    assert unit_file.exists()
    content = unit_file.read_text()
    assert "ExecStart=/usr/bin/arwn-collect -f -c " + config_path in content
    assert "WantedBy=default.target" in content

    assert mock_run.call_args_list == [
        call(["systemctl", "--user", "daemon-reload"], check=True),
        call(["systemctl", "--user", "enable", "--now", "arwn"], check=True),
        call(["loginctl", "enable-linger", "testuser"], check=True),
    ]


def test_install_service_binary_not_found(tmp_path, capsys):
    with (
        patch("arwn.cmd.install_service.shutil.which", return_value=None),
        patch("arwn.cmd.install_service.Path.home", return_value=tmp_path),
        patch("arwn.cmd.install_service.subprocess.run") as mock_run,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main([])

    assert exc_info.value.code != 0
    captured = capsys.readouterr()
    assert "arwn-collect" in captured.err
    mock_run.assert_not_called()
    unit_file = tmp_path / ".config" / "systemd" / "user" / "arwn.service"
    assert not unit_file.exists()
