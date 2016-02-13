#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import sys

import mock
import testtools
import unittest

from arwn.cmd import collect

from . import arwn_fixtures


class TestArwnCollect(testtools.TestCase):

    @mock.patch('arwn.cmd.collect.event_loop')
    def test_start_in_forground(self, evloop):
        cfg = arwn_fixtures.SampleConfig()
        stdout = arwn_fixtures.CaptureStdout()
        self.useFixture(stdout)
        self.useFixture(cfg)

        testargs = ["collect", "-f", "-c", cfg.path]
        with mock.patch.object(sys, 'argv', testargs):
            collect.main()

        self.assertIn("[DEBUG] root: Starting arwn in foreground",
                      str(stdout))
        self.assertTrue(evloop.called, "Eventloop not called")


if __name__ == '__main__':
    sys.exit(unittest.main())
