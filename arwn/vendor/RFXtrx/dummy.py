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
This module provides a dummy transport for testing purposes
"""

from RFXtrx import RFXtrxTransport


class DummyTransport(RFXtrxTransport):
    """ Dummy transport for testing purposes """

    def __init__(self, debug=True):
        self.debug = debug

    def receive(self, data):
        """ Emulate a receive by parsing the given data """
        pkt = bytearray(data)
        if self.debug:
            print ("Recv: " + " ".join("0x{0:02x}".format(x) for x in pkt))
        return self.parse(pkt)

    def send(self, data):
        """ Emulate a send by doing nothing (except printing debug info if
            requested) """
        pkt = bytearray(data)
        if self.debug:
            print ("Send: " + " ".join("0x{0:02x}".format(x) for x in pkt))
