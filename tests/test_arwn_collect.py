#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import os
import sys
import tempfile
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
import yaml

from arwn.cmd import collect


@mock.patch("arwn.cmd.collect.event_loop")
def test_start_in_forground(evloop, sample_config, capsys):
    """Test starting arwn in foreground mode."""
    testargs = ["collect", "-f", "-c", sample_config]
    with mock.patch.object(sys, "argv", testargs):
        collect.main()

    captured = capsys.readouterr()
    assert "[DEBUG] root: Starting arwn in foreground" in captured.out
    assert evloop.called, "Eventloop not called"


def make_minimal_config():
    return {
        "collector": {"type": "rfxcom", "device": "/dev/null"},
        "names": {},
        "mqtt": {"server": "localhost"},
    }


@patch("arwn.cmd.collect.engine.ConfigWatcher")
@patch("arwn.cmd.collect.engine.Dispatcher")
def test_event_loop_starts_config_watcher(mock_dispatcher_cls, mock_watcher_cls):
    from arwn.cmd.collect import event_loop

    mock_dispatcher = MagicMock()
    mock_dispatcher_cls.return_value = mock_dispatcher
    mock_watcher = MagicMock()
    mock_watcher_cls.return_value = mock_watcher

    # Make loopforever return immediately
    mock_dispatcher.loopforever.side_effect = StopIteration

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(make_minimal_config(), f)
        config_path = f.name

    try:
        try:
            event_loop(make_minimal_config(), config_path)
        except StopIteration:
            pass

        mock_watcher_cls.assert_called_once_with(config_path, mock_dispatcher)
        mock_watcher.start.assert_called_once()
    finally:
        os.unlink(config_path)
