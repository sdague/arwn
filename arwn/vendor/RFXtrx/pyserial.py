# This file is part of pyRFXtrx, a Python library to communicate with
# the RFXtrx family of devices from http://www.rfxcom.com/
# See https://github.com/woudt/pyRFXtrx for the latest version.
#
# Copyright (C) 2012  Edwin Woudt <edwin@woudt.nl>
#
# pyRFXtrx is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyRFXtrx is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pyRFXtrx.  See the file COPYING.txt in the distribution.
# If not, see <http://www.gnu.org/licenses/>.
"""
This module provides a transport for PySerial
"""

import logging

from serial import Serial
from time import sleep
from . import RFXtrxTransport

logger = logging.getLogger(__name__)


class PySerialTransport(RFXtrxTransport):
    """ Implementation of a transport using PySerial """

    def __init__(self, port, debug=False):
        self.serial = Serial(port, 38400, timeout=0.1)
        self.debug = debug

    def receive_blocking(self):
        """ Wait until a packet is received and return with an RFXtrxEvent """
        while True:
            data = self.serial.read()
            if (len(data) > 0):
                pkt = bytearray(data)
                data = self.serial.read(pkt[0])
                pkt.extend(bytearray(data))
                if self.debug:
                    logger.debug(
                        "Recv: " + " ".join("0x{0:02x}".format(x)
                                            for x in pkt))
                return self.parse(pkt)

    def send(self, data):
        """ Send the given packet """
        if isinstance(data, bytearray):
            pkt = data
        elif isinstance(data, str) or isinstance(data, bytes):
            pkt = bytearray(data)
        else:
            raise ValueError("Invalid type")
        if self.debug:
            logger.debug(
                "Send: " + " ".join("0x{0:02x}".format(x) for x in pkt))
        self.serial.write(pkt)

    def reset(self):
        """ Reset the RFXtrx """
        self.send('\x0D\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        sleep(0.3)  # Should work with 0.05, but not for me
        self.serial.flushInput()
        self.send('\x0D\x00\x00\x01\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        # self.send('\x0D\x00\x00\x03\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        return self.receive_blocking()
