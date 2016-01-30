# Copyright 2016 Sean Dague
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import math
import re

regex = '(-?\d+(\.\d+)?)(F|C|K)'

# The scale factor between C and F
CScale = 1.8
# The offset between C and F
FOffset = 32
# The offset between K and C
KOffset = 273.15
# The offset between R and F
ROffset = 459.67

# Dewpoint constants
a = 17.271
b = 237.7  # degC


class Temperature(object):
    units = "F"
    temp = 0.0

    def __init__(self, data="0F"):
        m = re.match(regex, data)
        self.temp = float(m.group(1))
        self.units = m.group(3)

    def __str__(self):
        return "%f%s" % (self.temp, self.units)

    def is_F(self):
        return self.units == "F"

    def is_C(self):
        return self.units == "C"

    def is_K(self):
        return self.units == "K"

    def _convert_to(self, unit):
        if unit == self.units:
            return self.temp

        if unit == "C":
            if self.is_F():
                return (self.temp - FOffset) / CScale
            elif self.is_K():
                return (self.temp + KOffset)
        elif unit == "F":
            if self.is_C():
                return (self.temp * CScale) + FOffset
            elif self.is_K():
                return ((self.temp + KOffset) * CScale) + FOffset
        elif unit == "K":
            if self.is_F():
                return ((self.temp - FOffset) / CScale) + KOffset
            elif self.is_C():
                return (self.temp - KOffset)

        return self.temp

    def to_C(self):
        return self._convert_to("C")

    def to_F(self):
        return self._convert_to("F")

    def to_K(self):
        return self._convert_to("K")

    def as_C(self):
        temp = self._convert_to("C")
        return Temperature("%fC" % temp)

    def as_F(self):
        temp = self._convert_to("F")
        return Temperature("%fF" % temp)

    def as_K(self):
        temp = self._convert_to("K")
        return Temperature("%fK" % temp)

    # TODO(sdague): unit tests
    def dewpoint(self, humid):
        def _gamma(t, humid):
            return (a * t / (b + t)) + math.log(humid / 100.0)
        t = self.as_C()
        T = t.temp
        t.temp = (b * _gamma(T, humid)) / (a - _gamma(T, humid))

        return t._convert_to(self.units)
