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
This module provides low level packet parsing and generation code for the
RFXtrx.
"""
# pylint: disable=C0302,R0902,R0903,R0911,R0913

import logging

logger = logging.getLogger(__name__)


def parse(data):
    """ Parse a packet from a bytearray """
    if data[1] == 0x10:
        pkt = Lighting1()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x11:
        pkt = Lighting2()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x12:
        pkt = Lighting3()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x13:
        pkt = Lighting4()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x14:
        pkt = Lighting5()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x15:
        pkt = Lighting6()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x50:
        pkt = Temp()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x52:
        pkt = TempHumid()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x54:
        pkt = TempHumidBaro()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x55:
        pkt = RainGauge()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x56:
        pkt = Wind()
        pkt.load_receive(data)
        return pkt
    elif data[1] == 0x57:
        pkt = UV()
        pkt.load_receive(data)
        return pkt
    else:
        logger.debug("Unknown sensor type %s" % ("{0:02x}".format(data[1])))


###############################################################################
# Packet class
###############################################################################

class Packet(object):
    """ Abstract superclass for all low level packets """

    _UNKNOWN_TYPE = "Unknown type ({0:#04x}/{1:#04x})"
    _UNKNOWN_CMND = "Unknown command ({0:#04x})"

    def __init__(self):
        """Constructor"""
        self.data = None
        self.packetlength = None
        self.packettype = None
        self.subtype = None
        self.seqnbr = None
        self.rssi = None
        self.rssi_byte = None
        self.type_string = None
        self.id_string = None


###############################################################################
# Lighting1 class
###############################################################################

class Lighting1(Packet):
    """
    Data class for the Lighting1 packet type
    """

    TYPES = {0x00: 'X10 lighting',
             0x01: 'ARC',
             0x02: 'ELRO AB400D',
             0x03: 'Waveman',
             0x04: 'Chacon EMW200',
             0x05: 'IMPULS',
             0x06: 'RisingSun',
             0x07: 'Philips SBC',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    ALIAS_TYPES = {'KlikAanKlikUit code wheel': 0x01,
                   'NEXA code wheel': 0x01,
                   'CHACON code wheel': 0x01,
                   'HomeEasy code wheel': 0x01,
                   'Proove': 0x01,
                   'DomiaLite': 0x01,
                   'InterTechno': 0x01,
                   'AB600': 0x01,
                   }
    """
    Mapping of subtype aliases to the corresponding subtype value
    """

    HOUSECODES = {0x41: 'A', 0x42: 'B', 0x43: 'C', 0x44: 'D',
                  0x45: 'E', 0x46: 'F', 0x47: 'G', 0x48: 'H',
                  0x49: 'I', 0x4A: 'J', 0x4B: 'K', 0x4C: 'L',
                  0x4D: 'M', 0x4E: 'N', 0x4F: 'O', 0x50: 'P'}
    """
    Mapping of housecode numeric values to strings, used in id_string
    """

    COMMANDS = {0x00: 'Off',
                0x01: 'On',
                0x02: 'Dim',
                0x03: 'Bright',
                0x05: 'All/group Off',
                0x06: 'All/group On',
                0x07: 'Chime',
                0xFF: 'Illegal command'}
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    def __str__(self):
        return ("Lighting1 [subtype={0}, seqnbr={1}, id={2}, cmnd={3}, " +
                "rssi={4}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.cmnd_string, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Lighting1, self).__init__()
        self.housecode = None
        self.unitcode = None
        self.cmnd = None
        self.cmnd_string = None

    def parse_id(self, subtype, id_string):
        """Parse a string id into individual components"""
        try:
            self.packettype = 0x10
            self.subtype = subtype
            hcode = id_string[0:1]
            for hcode_num in self.HOUSECODES:
                if self.HOUSECODES[hcode_num] == hcode:
                    self.housecode = hcode_num
            self.unitcode = int(id_string[1:])
            self._set_strings()
        except:
            raise ValueError("Invalid id_string")
        if self.id_string != id_string:
            raise ValueError("Invalid id_string")

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.housecode = data[4]
        self.unitcode = data[5]
        self.cmnd = data[6]
        self.rssi_byte = data[7]
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def set_transmit(self, subtype, seqnbr, housecode, unitcode, cmnd):
        """Load data from individual data fields"""
        self.packetlength = 7
        self.packettype = 0x10
        self.subtype = subtype
        self.seqnbr = seqnbr
        self.housecode = housecode
        self.unitcode = unitcode
        self.cmnd = cmnd
        self.rssi_byte = 0
        self.rssi = 0
        self.data = bytearray([self.packetlength, self.packettype,
                               self.subtype, self.seqnbr, self.housecode,
                               self.unitcode, self.cmnd, self.rssi_byte])
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = self.HOUSECODES[self.housecode] + str(self.unitcode)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.cmnd is not None:
            if self.cmnd in self.COMMANDS:
                self.cmnd_string = self.COMMANDS[self.cmnd]
            else:
                self.cmnd_string = self._UNKNOWN_CMND.format(self.cmnd)


###############################################################################
# Lighting2 class
###############################################################################

class Lighting2(Packet):
    """
    Data class for the Lighting2 packet type
    """

    TYPES = {0x00: 'AC',
             0x01: 'HomeEasy EU',
             0x02: 'ANSLUT',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    ALIAS_TYPES = {'KlikAanKlikUit automatic': 0x00,
                   'NEXA automatic': 0x00,
                   'CHACON autometic': 0x00,
                   'HomeEasy UK': 0x00,
                   }
    """
    Mapping of subtype aliases to the corresponding subtype value
    """

    COMMANDS = {0x00: 'Off',
                0x01: 'On',
                0x02: 'Set level',
                0x03: 'Group off',
                0x04: 'Group on',
                0x05: 'Set group level',
                }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    def __str__(self):
        return ("Lighting2 [subtype={0}, seqnbr={1}, id={2}, cmnd={3}, " +
                "level={4}, rssi={5}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.cmnd_string, self.level, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Lighting2, self).__init__()
        self.id1 = None
        self.id2 = None
        self.id3 = None
        self.id4 = None
        self.id_combined = None
        self.unitcode = None
        self.cmnd = None
        self.level = None
        self.cmnd_string = None

    def parse_id(self, subtype, id_string):
        """Parse a string id into individual components"""
        try:
            self.packettype = 0x11
            self.subtype = subtype
            self.id_combined = int(id_string[:7], 16)
            self.id1 = self.id_combined >> 24
            self.id2 = self.id_combined >> 16 & 0xff
            self.id3 = self.id_combined >> 8 & 0xff
            self.id4 = self.id_combined & 0xff
            self.unitcode = int(id_string[8:])
            self._set_strings()
        except:
            raise ValueError("Invalid id_string")
        if self.id_string != id_string:
            raise ValueError("Invalid id_string")

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.id3 = data[6]
        self.id4 = data[7]
        self.id_combined = (self.id1 << 24) + (self.id2 << 16) \
            + (self.id3 << 8) + self.id4
        self.unitcode = data[8]
        self.cmnd = data[9]
        self.level = data[10]
        self.rssi_byte = data[11]
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def set_transmit(self, subtype, seqnbr, id_combined, unitcode, cmnd,
                     level):
        """Load data from individual data fields"""
        self.packetlength = 0x0b
        self.packettype = 0x11
        self.subtype = subtype
        self.seqnbr = seqnbr
        self.id_combined = id_combined
        self.id1 = id_combined >> 24
        self.id2 = id_combined >> 16 & 0xff
        self.id3 = id_combined >> 8 & 0xff
        self.id4 = id_combined & 0xff
        self.unitcode = unitcode
        self.cmnd = cmnd
        self.level = level
        self.rssi_byte = 0
        self.rssi = 0
        self.data = bytearray([self.packetlength, self.packettype,
                               self.subtype, self.seqnbr, self.id1, self.id2,
                               self.id3, self.id4, self.unitcode, self.cmnd,
                               self.level, self.rssi_byte])
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:07x}:{1}".format(self.id_combined, self.unitcode)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.cmnd is not None:
            if self.cmnd in self.COMMANDS:
                self.cmnd_string = self.COMMANDS[self.cmnd]
            else:
                self.cmnd_string = self._UNKNOWN_CMND.format(self.cmnd)


###############################################################################
# Lighting3 class
###############################################################################

class Lighting3(Packet):
    """
    Data class for the Lighting3 packet type
    """

    TYPES = {0x00: 'Ikea Koppla',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    COMMANDS = {0x00: 'Bright',
                0x08: 'Dim',
                0x10: 'On',
                0x11: 'Level 1',
                0x12: 'Level 2',
                0x13: 'Level 3',
                0x14: 'Level 4',
                0x15: 'Level 5',
                0x16: 'Level 6',
                0x17: 'Level 7',
                0x18: 'Level 8',
                0x19: 'Level 9',
                0x1a: 'Off',
                0x1c: 'Program',
                }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    def __str__(self):
        return ("Lighting3 [subtype={0}, seqnbr={1}, id={2}, cmnd={3}, " +
                "battery={4}, rssi={5}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.cmnd_string, self.battery, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Lighting3, self).__init__()
        self.system = None
        self.channel1 = None
        self.channel2 = None
        self.channel = None
        self.cmnd = None
        self.battery = None
        self.cmnd_string = None

    def parse_id(self, subtype, id_string):
        """Parse a string id into individual components"""
        try:
            self.packettype = 0x12
            self.subtype = subtype
            self.system = int(id_string[:1], 16)
            self.channel = int(id_string[2:], 16)
            self.channel1 = self.channel & 0xff
            self.channel2 = self.channel >> 8
            self._set_strings()
        except:
            raise ValueError("Invalid id_string")
        if self.id_string != id_string:
            raise ValueError("Invalid id_string")

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.system = data[4]
        self.channel1 = data[5]
        self.channel2 = data[6]
        self.channel = (self.channel2 << 8) + self.channel1
        self.cmnd = data[7]
        self.rssi_byte = data[8]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def set_transmit(self, subtype, seqnbr, system, channel, cmnd):
        """Load data from individual data fields"""
        self.packetlength = 0x08
        self.packettype = 0x12
        self.subtype = subtype
        self.seqnbr = seqnbr
        self.system = system
        self.channel = channel
        self.channel1 = channel & 0xff
        self.channel2 = channel >> 8
        self.cmnd = cmnd
        self.rssi_byte = 0
        self.battery = 0
        self.rssi = 0
        self.data = bytearray([self.packetlength, self.packettype,
                               self.subtype, self.seqnbr, self.system,
                               self.channel1, self.channel2, self.cmnd,
                               self.rssi_byte])
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:1x}:{1:03x}".format(self.system, self.channel)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.cmnd is not None:
            if self.cmnd in self.COMMANDS:
                self.cmnd_string = self.COMMANDS[self.cmnd]
            else:
                self.cmnd_string = self._UNKNOWN_CMND.format(self.cmnd)


###############################################################################
# Lighting4 class
###############################################################################

class Lighting4(Packet):
    """
    Data class for the Lighting4 packet type
    """

    TYPES = {0x00: 'PT2262',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    def __str__(self):
        return ("Lighting4 [subtype={0}, seqnbr={1}, cmd={2}, pulse={3}, " +
                "rssi={4}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.pulse, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Lighting4, self).__init__()
        self.cmd1 = None
        self.cmd2 = None
        self.cmd3 = None
        self.cmd = None
        self.pulsehigh = None
        self.pulselow = None
        self.pulse = None

    def parse_id(self, subtype, id_string):
        """Parse a string id into individual components"""
        try:
            self.packettype = 0x13
            self.subtype = subtype
            self.cmd = int(id_string, 16)
            self.cmd1 = self.cmd >> 16
            self.cmd2 = (self.cmd >> 8) & 0xff
            self.cmd3 = self.cmd & 0xff
            self._set_strings()
        except:
            raise ValueError("Invalid id_string")
        if self.id_string != id_string:
            raise ValueError("Invalid id_string")

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.cmd1 = data[4]
        self.cmd2 = data[5]
        self.cmd3 = data[6]
        self.cmd = (self.cmd1 << 16) + (self.cmd2 << 8) + self.cmd3
        self.pulsehigh = data[7]
        self.pulselow = data[8]
        self.pulse = (self.pulsehigh << 8) + self.pulselow
        self.rssi_byte = data[9]
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def set_transmit(self, subtype, seqnbr, cmd, pulse):
        """Load data from individual data fields"""
        self.packetlength = 0x09
        self.packettype = 0x13
        self.subtype = subtype
        self.seqnbr = seqnbr
        self.cmd = cmd
        self.cmd1 = self.cmd >> 16
        self.cmd2 = (self.cmd >> 8) & 0xff
        self.cmd3 = self.cmd & 0xff
        self.pulse = pulse
        self.pulsehigh = self.pulse >> 8
        self.pulselow = self.pulse & 0xff
        self.rssi_byte = 0
        self.rssi = 0
        self.data = bytearray([self.packetlength, self.packettype,
                               self.subtype, self.seqnbr,
                               self.cmd1, self.cmd2, self.cmd3,
                               self.pulsehigh, self.pulselow, self.rssi_byte])
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:06x}".format(self.cmd)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)


###############################################################################
# Lighting5 class
###############################################################################

class Lighting5(Packet):
    """
    Data class for the Lighting5 packet type
    """

    TYPES = {0x00: 'LightwaveRF, Siemens',
             0x01: 'EMW100 GAO/Everflourish',
             0x02: 'BBSB new types',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    ALIAS_TYPES = {'LightwaveRF': 0x00,
                   'Siemens': 0x00,
                   'EMW100 GAO': 0x01,
                   'Everflourish': 0x01,
                   }
    """
    Mapping of subtype aliases to the corresponding subtype value
    """

    COMMANDS_00 = {0x00: 'Off',
                   0x01: 'On',
                   0x02: 'Group off',
                   0x03: 'Mood1',
                   0x04: 'Mood2',
                   0x05: 'Mood3',
                   0x06: 'Mood4',
                   0x07: 'Mood5',
                   0x0a: 'Unlock',
                   0x0b: 'Lock',
                   0x0c: 'All lock',
                   0x0d: 'Close (inline relay)',
                   0x0e: 'Stop (inline relay)',
                   0x0f: 'Open (inline relay)',
                   0x10: 'Set level',
                   }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    COMMANDS_01 = {0x00: 'Off',
                   0x01: 'On',
                   0x02: 'Learn',
                   }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    COMMANDS_02 = {0x00: 'Off',
                   0x01: 'On',
                   0x02: 'Group off',
                   0x03: 'Group on',
                   }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    COMMANDS_XX = {0x00: 'Off',
                   0x01: 'On',
                   }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    def __str__(self):
        return ("Lighting5 [subtype={0}, seqnbr={1}, id={2}, cmnd={3}, " +
                "level={4}, rssi={5}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.cmnd_string, self.level, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Lighting5, self).__init__()
        self.id1 = None
        self.id2 = None
        self.id3 = None
        self.id_combined = None
        self.unitcode = None
        self.cmnd = None
        self.level = None
        self.cmnd_string = None

    def parse_id(self, subtype, id_string):
        """Parse a string id into individual components"""
        try:
            self.packettype = 0x14
            self.subtype = subtype
            self.id_combined = int(id_string[:6], 16)
            self.id1 = self.id_combined >> 16
            self.id2 = self.id_combined >> 8 & 0xff
            self.id3 = self.id_combined & 0xff
            self.unitcode = int(id_string[7:])
            self._set_strings()
        except:
            raise ValueError("Invalid id_string")
        if self.id_string != id_string:
            raise ValueError("Invalid id_string")

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.id3 = data[6]
        self.id_combined = (self.id1 << 16) + (self.id2 << 8) + self.id3
        self.unitcode = data[7]
        self.cmnd = data[8]
        self.level = data[9]
        self.rssi_byte = data[10]
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def set_transmit(self, subtype, seqnbr, id_combined, unitcode, cmnd,
                     level):
        """Load data from individual data fields"""
        self.packetlength = 0x0a
        self.packettype = 0x14
        self.subtype = subtype
        self.seqnbr = seqnbr
        self.id_combined = id_combined
        self.id1 = id_combined >> 16
        self.id2 = id_combined >> 8 & 0xff
        self.id3 = id_combined & 0xff
        self.unitcode = unitcode
        self.cmnd = cmnd
        self.level = level
        self.rssi_byte = 0
        self.rssi = 0
        self.data = bytearray([self.packetlength, self.packettype,
                               self.subtype, self.seqnbr, self.id1, self.id2,
                               self.id3, self.unitcode, self.cmnd,
                               self.level, self.rssi_byte])
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:06x}:{1}".format(self.id_combined, self.unitcode)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.cmnd is not None:
            if self.subtype == 0x00 and self.cmnd in self.COMMANDS_00:
                self.cmnd_string = self.COMMANDS_00[self.cmnd]
            elif self.subtype == 0x01 and self.cmnd in self.COMMANDS_01:
                self.cmnd_string = self.COMMANDS_01[self.cmnd]
            elif self.subtype == 0x02 and self.cmnd in self.COMMANDS_02:
                self.cmnd_string = self.COMMANDS_02[self.cmnd]
            elif self.subtype >= 0x03 and self.cmnd in self.COMMANDS_XX:
                self.cmnd_string = self.COMMANDS_XX[self.cmnd]
            else:
                self.cmnd_string = self._UNKNOWN_CMND.format(self.cmnd)


###############################################################################
# Lighting6 class
###############################################################################

class Lighting6(Packet):
    """
    Data class for the Lighting6 packet type
    """

    TYPES = {0x00: 'Blyss',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    COMMANDS = {0x00: 'On',
                0x01: 'Off',
                0x02: 'Group on',
                0x03: 'Group off',
                }
    """
    Mapping of command numeric values to strings, used for cmnd_string
    """

    def __str__(self):
        return ("Lighting6 [subtype={0}, seqnbr={1}, id={2}, cmnd={3}, " +
                "cmndseqnbr={4}, rssi={5}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.cmnd_string, self.cmndseqnbr, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Lighting6, self).__init__()
        self.id1 = None
        self.id2 = None
        self.id_combined = None
        self.groupcode = None
        self.unitcode = None
        self.cmnd = None
        self.cmndseqnbr = None
        self.rfu = None
        self.level = None
        self.cmnd_string = None

    def parse_id(self, subtype, id_string):
        """Parse a string id into individual components"""
        try:
            self.packettype = 0x15
            self.subtype = subtype
            self.id_combined = int(id_string[:4], 16)
            self.id1 = self.id_combined >> 8 & 0xff
            self.id2 = self.id_combined & 0xff
            self.groupcode = ord(id_string[5])
            self.unitcode = int(id_string[6:])
            self._set_strings()
        except:
            raise ValueError("Invalid id_string")
        if self.id_string != id_string:
            raise ValueError("Invalid id_string")

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.id_combined = (self.id1 << 8) + self.id2
        self.groupcode = data[6]
        self.unitcode = data[7]
        self.cmnd = data[8]
        self.cmndseqnbr = data[9]
        self.rfu = data[10]
        self.rssi_byte = data[11]
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def set_transmit(self, subtype, seqnbr, id_combined, groupcode, unitcode,
                     cmnd, cmndseqnbr):
        """Load data from individual data fields"""
        self.packetlength = 0x0b
        self.packettype = 0x15
        self.subtype = subtype
        self.seqnbr = seqnbr
        self.id_combined = id_combined
        self.id1 = id_combined >> 8 & 0xff
        self.id2 = id_combined & 0xff
        self.groupcode = groupcode
        self.unitcode = unitcode
        self.cmnd = cmnd
        self.cmndseqnbr = cmndseqnbr
        self.rfu = 0
        self.rssi_byte = 0
        self.rssi = 0
        self.data = bytearray([self.packetlength, self.packettype,
                               self.subtype, self.seqnbr, self.id1, self.id2,
                               self.groupcode, self.unitcode, self.cmnd,
                               self.cmndseqnbr, self.rfu, self.rssi_byte])
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:04x}:{1}{2}".format(self.id_combined,
                                                 chr(self.groupcode),
                                                 self.unitcode)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.cmnd is not None:
            if self.cmnd in self.COMMANDS:
                self.cmnd_string = self.COMMANDS[self.cmnd]
            else:
                self.cmnd_string = self._UNKNOWN_CMND.format(self.cmnd)


###############################################################################
# SensorPacket class
###############################################################################

class SensorPacket(Packet):
    """
    Abstract superclass for all sensor related packets
    """

    HUMIDITY_TYPES = {0x00: 'dry',
                      0x01: 'comfort',
                      0x02: 'normal',
                      0x03: 'wet',
                      -1: 'unknown humidity'}
    """
    Mapping of humidity types to string
    """

    FORECAST_TYPES = {0x00: 'no forecast available',
                      0x01: 'sunny',
                      0x02: 'partly cloudy',
                      0x03: 'cloudy',
                      0x04: 'rain',
                      -1: 'unknown forecast'}
    """
    Mapping of forecast types to string
    """

    def __init__(self):
        """Constructor"""
        super(SensorPacket, self).__init__()


###############################################################################
# Temp class
###############################################################################

class Temp(SensorPacket):
    """
    Data class for the Temp1 packet type
    """

    TYPES = {0x01: 'THR128/138, THC138',
             0x02: 'THC238/268,THN132,THWR288,THRN122,THN122,AW129/131',
             0x03: 'THWR800',
             0x04: 'RTHN318',
             0x05: 'La Crosse TX2, TX3, TX4, TX17',
             0x06: 'TS15C',
             0x07: 'Viking 02811',
             0x08: 'La Crosse WS2300',
             0x09: 'RUBiCSON',
             0x0a: 'TFA 30.3133',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    def __str__(self):
        return ("Temp [subtype={0}, seqnbr={1}, id={2}, temp={3}, " +
                "battery={4}, rssi={5}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.temp, self.battery, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Temp, self).__init__()
        self.id1 = None
        self.id2 = None
        self.temphigh = None
        self.templow = None
        self.temp = None
        self.battery = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.temphigh = data[6]
        self.templow = data[7]
        self.temp = float(((self.temphigh & 0x7f) << 8) + self.templow) / 10
        if self.temphigh >= 0x80:
            self.temp = -self.temp
        self.rssi_byte = data[8]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)


###############################################################################
# Humid class
###############################################################################

class Humid(SensorPacket):
    """
    Data class for the Humid packet type
    """

    TYPES = {0x01: 'LaCrosse TX3',
             0x02: 'LaCrosse WS2300',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    def __str__(self):
        return ("Humid [subtype={0}, seqnbr={1}, id={2}, " +
                "humidity={3}, humidity_status={4}, battery={5}, rssi={6}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.humidity, self.humidity_status,
                    self.battery, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Humid, self).__init__()
        self.id1 = None
        self.id2 = None
        self.humidity = None
        self.humidity_status = None
        self.humidity_status_string = None
        self.battery = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.humidity = data[6]
        self.humidity_status = data[7]
        self.rssi_byte = data[8]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.humidity_status in self.HUMIDITY_TYPES:
            self.humidity_status_string = \
                self.HUMIDITY_TYPES[self.humidity_status]
        else:
            self.humidity_status_string = self.HUMIDITY_TYPES[-1]


###############################################################################
# TempHumid class
###############################################################################

class TempHumid(SensorPacket):
    """
    Data class for the TempHumid packet type
    """

    TYPES = {0x01: 'THGN122/123, THGN132, THGR122/228/238/268',
             0x02: 'THGR810, THGN800',
             0x03: 'RTGR328',
             0x04: 'THGR328',
             0x05: 'WTGR800',
             0x06: 'THGR918, THGRN228, THGN500',
             0x07: 'TFA TS34C, Cresta',
             0x08: 'WT260,WT260H,WT440H,WT450,WT450H',
             0x09: 'Viking 02035,02038',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    def __str__(self):
        return ("TempHumid [subtype={0}, seqnbr={1}, id={2}, temp={3}, " +
                "humidity={4}, humidity_status={5}, battery={6}, rssi={7}]") \
            .format(self.type_string, self.seqnbr, self.id_string,
                    self.temp, self.humidity, self.humidity_status,
                    self.battery, self.rssi)

    def __init__(self):
        """Constructor"""
        super(TempHumid, self).__init__()
        self.id1 = None
        self.id2 = None
        self.temphigh = None
        self.templow = None
        self.temp = None
        self.humidity = None
        self.humidity_status = None
        self.humidity_status_string = None
        self.battery = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.temphigh = data[6]
        self.templow = data[7]
        self.temp = float(((self.temphigh & 0x7f) << 8) + self.templow) / 10
        if self.temphigh >= 0x80:
            self.temp = -self.temp
        self.humidity = data[8]
        self.humidity_status = data[9]
        self.rssi_byte = data[10]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.humidity_status in self.HUMIDITY_TYPES:
            self.humidity_status_string = \
                self.HUMIDITY_TYPES[self.humidity_status]
        else:
            self.humidity_status_string = self.HUMIDITY_TYPES[-1]


###############################################################################
# Baro class
###############################################################################

class Baro(SensorPacket):
    """
    Data class for the Baro packet type
    """

    TYPES = {}
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    def __str__(self):
        return ("Baro [subtype={0}, seqnbr={1}, id={2}, baro={3}, " +
                "forecast={4}, battery={5}, rssi={6}]") \
            .format(self.type_string, self.seqnbr, self.id_string, self.baro,
                    self.forecast, self.battery, self.rssi)

    def __init__(self):
        """Constructor"""
        super(Baro, self).__init__()
        self.id1 = None
        self.id2 = None
        self.baro1 = None
        self.baro2 = None
        self.baro = None
        self.forecast = None
        self.forecast_string = None
        self.battery = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.baro1 = data[6] & 0x0f
        self.baro2 = data[7]
        self.baro = (self.baro1 << 8) + self.baro2
        self.forecast = data[8]
        self.rssi_byte = data[9]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.forecast in self.FORECAST_TYPES:
            self.forecast_string = self.FORECAST_TYPES[self.forecast]
        else:
            self.forecast_string = self.FORECAST_TYPES[-1]


###############################################################################
# TempHumidBaro class
###############################################################################

class TempHumidBaro(SensorPacket):
    """
    Data class for the TempHumidBaro packet type
    """

    TYPES = {0x01: 'BTHR918',
             0x02: 'BTHR918N, BTHR968',
             }
    """
    Mapping of numeric subtype values to strings, used in type_string
    """

    def __str__(self):
        return ("TempHumidBaro [subtype={0}, seqnbr={1}, id={2}, temp={3}, " +
                "humidity={4}, humidity_status={5}, baro={6}, forecast={7}, " +
                "battery={8}, rssi={9}]") \
            .format(self.type_string, self.seqnbr, self.id_string, self.temp,
                    self.humidity, self.humidity_status, self.baro,
                    self.forecast, self.battery, self.rssi)

    def __init__(self):
        """Constructor"""
        super(TempHumidBaro, self).__init__()
        self.id1 = None
        self.id2 = None
        self.temphigh = None
        self.templow = None
        self.temp = None
        self.humidity = None
        self.humidity_status = None
        self.humidity_status_string = None
        self.baro1 = None
        self.baro2 = None
        self.baro = None
        self.forecast = None
        self.forecast_string = None
        self.battery = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.temphigh = data[6]
        self.templow = data[7]
        self.temp = float(((self.temphigh & 0x7f) << 8) + self.templow) / 10
        if self.temphigh >= 0x80:
            self.temp = -self.temp
        self.humidity = data[8]
        self.humidity_status = data[9]
        self.baro1 = data[10] & 0x0f
        self.baro2 = data[11]
        # note this is in hPa
        self.baro = (data[10] << 8) + data[11]
        self.forecast = data[12]
        self.rssi_byte = data[13]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
        if self.humidity_status in self.HUMIDITY_TYPES:
            self.humidity_status_string = \
                self.HUMIDITY_TYPES[self.humidity_status]
        else:
            self.humidity_status_string = self.HUMIDITY_TYPES[-1]
        if self.forecast in self.FORECAST_TYPES:
            self.forecast_string = self.FORECAST_TYPES[self.forecast]
        else:
            self.forecast_string = self.FORECAST_TYPES[-1]


#################
#
##################

class RainGauge(SensorPacket):

    TYPES = {
        0x01: "RGR126/682/918",
        0x02: "PCR800",
        0x03: "TFA",
        0x04: "UPM RG700",
        0x05: "WS2300"}

    def __init__(self):
        """Constructor"""
        super(RainGauge, self).__init__()
        self.id1 = None
        self.id2 = None
        self.rainrate1 = None
        self.rainrate2 = None
        self.rainrate = None
        self.raintotal1 = None
        self.raintotal2 = None
        self.raintotal3 = None
        self.raintotal = None
        self.battery = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.rainrate1 = data[6]
        self.rainrate2 = data[7]
        self.rainrate = ((self.rainrate1 << 8) + self.rainrate2) / 1000.0
        self.raintotal1 = data[8]
        self.raintotal2 = data[9]
        self.raintotal3 = data[10]
        self.raintotal = float((self.raintotal1 << 16) +
                               (self.raintotal2 << 8) +
                               self.raintotal3) / 10
        self.rssi_byte = data[11]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)

#################
#
##################

class Wind(SensorPacket):

    TYPES = {
        0x01:"WTGR800",
        0x02:"WGR800",
        0x03:"STR918, WGR918",
        0x04:"TFA (WIND4)",
        0x05:"UPM WDS500",
        0x06:"WS2300"}

    def __str__(self):
        return (("Wind [subtype={0}, seqnbr={1}, id={2}, direction={3}, " +
                 "average_speed={4}, gust={5}, battery={6}, rssi={7}]").
                format(self.type_string, self.seqnbr, self.id_string,
                       self.direction,
                       self.average_speed, self.gust,
                       self.battery, self.rssi))

    def __init__(self):
        """Constructor"""
        super(Wind, self).__init__()
        self.id1 = None
        self.id2 = None
        self.direction = None
        self.average_speed = None
        self.gust = None
        self.battery = None
        self.rssi = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.direction1 = data[6]
        self.direction2 = data[7]
        self.direction = (self.direction1 << 8) + self.direction2
        # wind units are decimeters/second
        self.av1 = data[8]
        self.av2 = data[9]
        # makes this meters per second
        self.average_speed = ((self.av1 << 8) + self.av2) / 10.0
        self.gust1 = data[10]
        self.gust2 = data[11]
        self.gust = ((self.gust1 << 8) + self.gust2) / 10.0

        if self.subtype == 0x03:
            self.battery = (data[16] + 1) * 10
        else:
            self.rssi_byte = data[16]
            self.battery = self.rssi_byte & 0x0f
            self.rssi = self.rssi_byte >> 4

        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)

#################
#
##################

class UV(SensorPacket):

    TYPES = {
        0x01: "UVN128, UV138",
        0x02: "UVN800",
        0x03: "TFA"}

    def __init__(self):
        """Constructor"""
        super(UV, self).__init__()
        self.id1 = None
        self.id2 = None
        self.uv1 = None
        self.uv2 = None
        self.uv = None
        self.battery = None
        self.rssi = None

    def load_receive(self, data):
        """Load data from a bytearray"""
        self.data = data
        self.packetlength = data[0]
        self.packettype = data[1]
        self.subtype = data[2]
        self.seqnbr = data[3]
        self.id1 = data[4]
        self.id2 = data[5]
        self.uv1 = data[6]
        self.uv2 = data[7]
        self.uv = (self.uv1 << 8) + self.uv2
        self.rssi_byte = data[8]
        self.battery = self.rssi_byte & 0x0f
        self.rssi = self.rssi_byte >> 4
        self._set_strings()

    def _set_strings(self):
        """Translate loaded numeric values into convenience strings"""
        self.id_string = "{0:02x}:{1:02x}".format(self.id1, self.id2)
        if self.subtype in self.TYPES:
            self.type_string = self.TYPES[self.subtype]
        else:
            #Degrade nicely for yet unknown subtypes
            self.type_string = self._UNKNOWN_TYPE.format(self.packettype,
                                                         self.subtype)
