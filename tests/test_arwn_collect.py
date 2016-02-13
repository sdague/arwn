#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_arwn
----------------------------------

Tests for `arwn` module.
"""

import os.path
import sys

import fixtures
import mock
import testtools
import unittest

from arwn.cmd import collect


class TestArwnCollect(testtools.TestCase):

    def setUp(self):
        super(TestArwnCollect, self).setUp()
        self.tmpdir = self.useFixture(fixtures.TempDir()).path
        self.cfgfile = os.path.join(self.tmpdir, "config.yml")
        with open(self.cfgfile, 'w') as f:
            f.write("""device: /dev/ttyUSB0
logfile: test.log
mqtt:
  server: 10.42.0.3
names:
  "ec:01": "Outside"
  "65:00": "Rain"
  "33:00": "Wind"
  "a9:04": "Freezer"
  "8c:00": "Refrigerator"
  "ce:08": "Arwen Room"
  "07:05": "Office"
  "e3:02": "Bomb Shelter"
  "de:01": "Subaru"
  "8e:01": "Cold Frame"
  "55:09": "Bed Room"
  "e9:04": "Garage"
""")

    @mock.patch('arwn.cmd.collect.event_loop')
    def test_start_in_forground(self, evloop):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout.stream))

        testargs = ["collect", "-f", "-c", self.cfgfile]
        with mock.patch.object(sys, 'argv', testargs):
            collect.main()

        self.assertIn("[DEBUG] root: Starting arwn in foreground",
                      stdout._details["stdout"].as_text())
        self.assertTrue(evloop.called, "Eventloop not called")


if __name__ == '__main__':
    sys.exit(unittest.main())
