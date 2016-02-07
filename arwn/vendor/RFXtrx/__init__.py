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
This module provides the base implementation for pyRFXtrx
"""
# pylint: disable=R0903

from arwn.vendor.RFXtrx import lowlevel


###############################################################################
# RFXtrxTransport class
###############################################################################

class RFXtrxTransport(object):
    """ Abstract superclass for all transport mechanisms """

    @staticmethod
    def parse(data):
        """ Parse the given data and return an RFXtrxEvent """
        pkt = lowlevel.parse(data)
        if pkt is not None:
            if isinstance(pkt, lowlevel.SensorPacket):
                return SensorEvent(pkt)
            else:
                return ControlEvent(pkt)


###############################################################################
# RFXtrxDevice class
###############################################################################

class RFXtrxDevice(object):
    """ Superclass for all devices """

    def __init__(self, pkt):
        self.packettype = pkt.packettype
        self.subtype = pkt.subtype
        self.type_string = pkt.type_string
        self.id_string = pkt.id_string
        self.pkt = pkt

    def __eq__(self, other):
        if self.packettype != other.packettype:
            return False
        if self.subtype != other.subtype:
            return False
        return self.id_string == other.id_string

    def __str__(self):
        return "{0} type='{1}' id='{2}'".format(
            type(self), self.type_string, self.id_string)


###############################################################################
# LightingDevice class
###############################################################################

class LightingDevice(RFXtrxDevice):
    """ Concrete class for a lighting device """

    def __init__(self, pkt):
        super(LightingDevice, self).__init__(pkt)
        if isinstance(pkt, lowlevel.Lighting1):
            self.housecode = pkt.housecode
            self.unitcode = pkt.unitcode
        if isinstance(pkt, lowlevel.Lighting2):
            self.id_combined = pkt.id_combined
            self.unitcode = pkt.unitcode
        if isinstance(pkt, lowlevel.Lighting3):
            self.system = pkt.system
            self.channel = pkt.channel
        if isinstance(pkt, lowlevel.Lighting5):
            self.id_combined = pkt.id_combined
            self.unitcode = pkt.unitcode
        if isinstance(pkt, lowlevel.Lighting6):
            self.id_combined = pkt.id_combined
            self.groupcode = pkt.groupcode
            self.unitcode = pkt.unitcode
            self.cmndseqnbr = 0

    def send_on(self, transport):
        """ Send an 'On' command using the given transport """
        if self.packettype == 0x10:  # Lighting1
            pkt = lowlevel.Lighting1()
            pkt.set_transmit(self.subtype, 0, self.housecode, self.unitcode,
                             0x01)
            transport.send(pkt.data)
        elif self.packettype == 0x11:  # Lighting2
            pkt = lowlevel.Lighting2()
            pkt.set_transmit(self.subtype, 0, self.id_combined, self.unitcode,
                             0x01, 0x00)
            transport.send(pkt.data)
        elif self.packettype == 0x12:  # Lighting3
            pkt = lowlevel.Lighting3()
            pkt.set_transmit(self.subtype, 0, self.system, self.channel,
                             0x10)
            transport.send(pkt.data)
        elif self.packettype == 0x14:  # Lighting5
            pkt = lowlevel.Lighting5()
            pkt.set_transmit(self.subtype, 0, self.id_combined, self.unitcode,
                             0x01, 0x00)
            transport.send(pkt.data)
        elif self.packettype == 0x15:  # Lighting6
            pkt = lowlevel.Lighting6()
            pkt.set_transmit(self.subtype, 0, self.id_combined, self.groupcode,
                             self.unitcode, 0x00, self.cmndseqnbr)
            self.cmndseqnbr = (self.cmndseqnbr + 1) % 5
            transport.send(pkt.data)
        else:
            raise ValueError("Unsupported packettype")

    def send_off(self, transport):
        """ Send an 'Off' command using the given transport """
        if self.packettype == 0x10:  # Lighting1
            pkt = lowlevel.Lighting1()
            pkt.set_transmit(self.subtype, 0, self.housecode, self.unitcode,
                             0x00)
            transport.send(pkt.data)
        elif self.packettype == 0x11:  # Lighting2
            pkt = lowlevel.Lighting2()
            pkt.set_transmit(self.subtype, 0, self.id_combined, self.unitcode,
                             0x00, 0x00)
            transport.send(pkt.data)
        elif self.packettype == 0x12:  # Lighting3
            pkt = lowlevel.Lighting3()
            pkt.set_transmit(self.subtype, 0, self.system, self.channel,
                             0x1a)
            transport.send(pkt.data)
        elif self.packettype == 0x14:  # Lighting5
            pkt = lowlevel.Lighting5()
            pkt.set_transmit(self.subtype, 0, self.id_combined, self.unitcode,
                             0x00, 0x00)
            transport.send(pkt.data)
        elif self.packettype == 0x15:  # Lighting6
            pkt = lowlevel.Lighting6()
            pkt.set_transmit(self.subtype, 0, self.id_combined, self.groupcode,
                             self.unitcode, 0x01, self.cmndseqnbr)
            self.cmndseqnbr = (self.cmndseqnbr + 1) % 5
            transport.send(pkt.data)
        else:
            raise ValueError("Unsupported packettype")

    def send_dim(self, transport, level):
        """ Send a 'Dim' command with the given level using the given
            transport
        """
        if self.packettype == 0x10:  # Lighting1
            raise ValueError("Dim level unsupported for Lighting1")
            # Supporting a dim level for X10 directly is not possible because
            # RFXtrx does not support sending extended commands
        elif self.packettype == 0x11:  # Lighting2
            if level == 0:
                self.send_off(transport)
            else:
                pkt = lowlevel.Lighting2()
                pkt.set_transmit(self.subtype, 0, self.id_combined,
                                 self.unitcode, 0x02,
                                 ((level + 6) * 16 // 100) - 1)
                transport.send(pkt.data)
        elif self.packettype == 0x12:  # Lighting3
            raise ValueError("Dim level unsupported for Lighting3")
            # Should not be too hard to add dim level support for Lighting3
            # (Ikea Koppla) due to the availability of the level 1 .. level 9
            # commands. I just need someone to help me with defining a mapping
            # between a percentage and a level
        elif self.packettype == 0x14:  # Lighting5
            if level == 0:
                self.send_off(transport)
            else:
                pkt = lowlevel.Lighting5()
                pkt.set_transmit(self.subtype, 0, self.id_combined,
                                 self.unitcode, 0x10,
                                 ((level + 3) * 32 // 100) - 1)
                transport.send(pkt.data)
        elif self.packettype == 0x15:  # Lighting6
            raise ValueError("Dim level unsupported for Lighting6")
        else:
            raise ValueError("Unsupported packettype")


###############################################################################
# get_devide method
###############################################################################

def get_device(packettype, subtype, id_string):
    """ Return a device base on its identifying values """
    if packettype == 0x10:  # Lighting1
        pkt = lowlevel.Lighting1()
        pkt.parse_id(subtype, id_string)
        return LightingDevice(pkt)
    elif packettype == 0x11:  # Lighting2
        pkt = lowlevel.Lighting2()
        pkt.parse_id(subtype, id_string)
        return LightingDevice(pkt)
    elif packettype == 0x12:  # Lighting3
        pkt = lowlevel.Lighting3()
        pkt.parse_id(subtype, id_string)
        return LightingDevice(pkt)
    elif packettype == 0x14:  # Lighting5
        pkt = lowlevel.Lighting5()
        pkt.parse_id(subtype, id_string)
        return LightingDevice(pkt)
    elif packettype == 0x15:  # Lighting6
        pkt = lowlevel.Lighting6()
        pkt.parse_id(subtype, id_string)
        return LightingDevice(pkt)
    else:
        raise ValueError("Unsupported packettype")


###############################################################################
# RFXtrxEvent class
###############################################################################

class RFXtrxEvent(object):
    """ Abstract superclass for all events """

    def __init__(self, device):
        self.device = device


###############################################################################
# SensorEvent class
###############################################################################

class SensorEvent(RFXtrxEvent):
    """ Concrete class for sensor events """

    def __init__(self, pkt):
        device = RFXtrxDevice(pkt)
        super(SensorEvent, self).__init__(device)

        self.values = {}
        if isinstance(pkt, lowlevel.Temp) \
                or isinstance(pkt, lowlevel.TempHumid) \
                or isinstance(pkt, lowlevel.TempHumidBaro):
            self.values['Temperature (C)'] = pkt.temp
        if isinstance(pkt, lowlevel.Humid) \
                or isinstance(pkt, lowlevel.TempHumid) \
                or isinstance(pkt, lowlevel.TempHumidBaro):
            self.values['Humidity'] = pkt.humidity
            self.values['Humidity status'] = pkt.humidity_status_string
            self.values['Humidity status numeric'] = pkt.humidity_status
        if isinstance(pkt, lowlevel.Baro) \
                or isinstance(pkt, lowlevel.TempHumidBaro):
            self.values['Barometer (hPa)'] = pkt.baro
            self.values['Forecast'] = pkt.forecast_string
            self.values['Forecast numeric'] = pkt.forecast
        if isinstance(pkt, lowlevel.RainGauge):
            self.values['Rain Rate (mm/hr)'] = pkt.rainrate
            self.values['Rain Total (mm)'] = pkt.raintotal
        if isinstance(pkt, lowlevel.Wind):
            self.values['Direction'] = pkt.direction
            self.values['Average speed'] = pkt.average_speed
            self.values['Gust'] = pkt.gust
        self.values['Battery numeric'] = pkt.battery
        self.values['Rssi numeric'] = pkt.rssi

    def __str__(self):
        return "{0} device=[{1}] values={2}".format(
            type(self), self.device, sorted(self.values.items()))


###############################################################################
# ControlEvent class
###############################################################################

class ControlEvent(RFXtrxEvent):
    """ Concrete class for control events """

    def __init__(self, pkt):
        if isinstance(pkt, lowlevel.Lighting1) \
                or isinstance(pkt, lowlevel.Lighting2) \
                or isinstance(pkt, lowlevel.Lighting3) \
                or isinstance(pkt, lowlevel.Lighting5) \
                or isinstance(pkt, lowlevel.Lighting6):
            device = LightingDevice(pkt)
        else:
            device = RFXtrxDevice(pkt)
        super(ControlEvent, self).__init__(device)

        self.values = {}
        if isinstance(pkt, lowlevel.Lighting1) \
                or isinstance(pkt, lowlevel.Lighting2) \
                or isinstance(pkt, lowlevel.Lighting3):
            self.values['Command'] = pkt.cmnd_string
        if isinstance(pkt, lowlevel.Lighting2) and pkt.cmnd in [2, 5]:
            self.values['Dim level'] = (pkt.level + 1) * 100 // 16
        if isinstance(pkt, lowlevel.Lighting5) and pkt.cmnd in [0x10]:
            self.values['Dim level'] = (pkt.level + 1) * 100 // 32
        self.values['Rssi numeric'] = pkt.rssi

    def __str__(self):
        return "{0} device=[{1}] values={2}".format(
            type(self), self.device, sorted(self.values.items()))
