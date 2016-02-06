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
This module provides a transport and protocol implementation for using pyRFXtrx
with the Twisted framework
"""
# pylint: disable=C0103,E0611,E1101,F0401

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import SerialPort

from . import RFXtrxTransport


class _TwistedSerialProtocol(Protocol):
    """ Twisted Protocol implementation, used internally by
        TwistedSerialTransport
    """

    def __init__(self, receive_callback, reset_callback):
        self.receive_callback = receive_callback
        self.reset_callback = reset_callback
        self.buffer = bytearray([])

    def dataReceived(self, data):
        """ Called by Twisted when data is received """
        bdata = bytearray(data)
        self.buffer.extend(bdata)
        if len(self.buffer) == self.buffer[0] + 1:
            self.receive_callback(self.buffer)
            self.buffer = bytearray([])

    def connectionMade(self):
        """ Called by Twisted when the connection is made """
        self.reset_callback()


class TwistedSerialTransport(RFXtrxTransport):
    """ Transport implementation for the Twisted framework """

    def __init__(self, port, receive_callback, debug=False):
        self.debug = debug
        self.receive_callback = receive_callback
        self.protocol = _TwistedSerialProtocol(self._receive, self._reset)
        self.serial = SerialPort(self.protocol, port, reactor)
        self.serial.setBaudRate(38400)

    def _receive(self, data):
        """ Handle a received packet """
        if self.debug:
            print("Recv: " + " ".join("0x{0:02x}".format(x) for x in data))
        pkt = self.parse(data)
        self.receive_callback(pkt)

    def send(self, data):
        """ Send the given packet """
        if self.debug:
            bdata = bytearray(data)
            print ("Send: " + " ".join("0x{0:02x}".format(x) for x in bdata))
        self.protocol.transport.write(str(data))

    def _reset(self):
        """ Reset the RFXtrx """
        self.send('\x0D\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        reactor.callLater(0.3, self._get_status)

    def _get_status(self):
        """ Get the status of the RFXtrx after a reset """
        self.send('\x0D\x00\x00\x01\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00')
