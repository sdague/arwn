"""Tests for temperature conversion logic."""

import math

import pytest

from arwn.temperature import Temperature


class TestFahrenheitConversions:
    def test_f_to_c_freezing(self):
        t = Temperature("32F")
        assert t.to_C() == pytest.approx(0.0)

    def test_f_to_c_boiling(self):
        t = Temperature("212F")
        assert t.to_C() == pytest.approx(100.0)

    def test_f_to_k_freezing(self):
        t = Temperature("32F")
        assert t.to_K() == pytest.approx(273.15)

    def test_f_to_k_absolute_zero(self):
        t = Temperature("-459.67F")
        assert t.to_K() == pytest.approx(0.0, abs=0.01)


class TestCelsiusConversions:
    def test_c_to_f_freezing(self):
        t = Temperature("0C")
        assert t.to_F() == pytest.approx(32.0)

    def test_c_to_f_boiling(self):
        t = Temperature("100C")
        assert t.to_F() == pytest.approx(212.0)

    def test_c_to_k_freezing(self):
        t = Temperature("0C")
        assert t.to_K() == pytest.approx(273.15)

    def test_c_to_k_absolute_zero(self):
        t = Temperature("-273.15C")
        assert t.to_K() == pytest.approx(0.0, abs=0.01)


class TestKelvinConversions:
    def test_k_to_c_water_freezing(self):
        t = Temperature("273.15K")
        assert t.to_C() == pytest.approx(0.0)

    def test_k_to_c_absolute_zero(self):
        t = Temperature("0K")
        assert t.to_C() == pytest.approx(-273.15)

    def test_k_to_f_water_freezing(self):
        t = Temperature("273.15K")
        assert t.to_F() == pytest.approx(32.0)

    def test_k_to_f_boiling(self):
        t = Temperature("373.15K")
        assert t.to_F() == pytest.approx(212.0)


class TestIdentityConversions:
    def test_f_to_f(self):
        t = Temperature("72F")
        assert t.to_F() == 72.0

    def test_c_to_c(self):
        t = Temperature("25C")
        assert t.to_C() == 25.0

    def test_k_to_k(self):
        t = Temperature("300K")
        assert t.to_K() == 300.0


class TestDewpoint:
    def test_dewpoint_typical(self):
        t = Temperature("72F")
        dp = t.dewpoint(50)
        assert 50 < dp < 60

    def test_dewpoint_saturated(self):
        t = Temperature("20C")
        dp = t.dewpoint(100)
        assert dp == pytest.approx(20.0, abs=0.5)
