#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import sys
from unittest import mock

import pytest

from arwn.cmd import collect

from . import arwn_fixtures


@mock.patch("arwn.cmd.collect.event_loop")
def test_start_in_forground(evloop, sample_config, capsys):
    """Test starting arwn in foreground mode."""
    testargs = ["collect", "-f", "-c", sample_config]
    with mock.patch.object(sys, "argv", testargs):
        collect.main()

    captured = capsys.readouterr()
    assert "[DEBUG] root: Starting arwn in foreground" in captured.out
    assert evloop.called, "Eventloop not called"
