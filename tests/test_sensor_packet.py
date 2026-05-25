"""Tests for SensorPacket.from_json() and as_json()."""

import pytest

from arwn.engine import IS_NONE, MM2IN, MPS2MPH, SensorPacket


class TestFromJsonTempHumid:
    def make_thgr810(self, **overrides):
        data = {
            "model": "Oregon-THGR810",
            "id": 0xAE,
            "channel": 1,
            "battery_ok": 1,
            "temperature_C": 20.0,
            "humidity": 55,
        }
        data.update(overrides)
        return data

    def test_type_flags(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810())
        assert sp.is_temp
        assert not sp.is_rain
        assert not sp.is_wind
        assert not sp.is_baro

    def test_sensor_id_formatting(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810(id=0xAE, channel=1))
        assert sp.sensor_id == "ae:01"

    def test_temperature_converted_to_fahrenheit(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810(temperature_C=0.0))
        assert sp.data["temp"] == 32.0
        assert sp.data["units"] == "F"

    def test_temperature_100c(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810(temperature_C=100.0))
        assert sp.data["temp"] == 212.0

    def test_humidity_stored(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810(humidity=65.3))
        assert sp.data["humid"] == 65.3

    def test_dewpoint_calculated(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810(temperature_C=20.0, humidity=50.0))
        assert "dewpoint" in sp.data
        assert isinstance(sp.data["dewpoint"], float)

    def test_battery_stored(self):
        sp = SensorPacket()
        sp.from_json(self.make_thgr810(battery_ok=1))
        assert sp.bat == 1


class TestFromJsonBaro:
    def test_bhtr968_has_baro_and_temp(self):
        data = {
            "model": "Oregon-BHTR968",
            "id": 0x5A,
            "channel": 0,
            "battery_ok": 1,
            "temperature_C": 22.5,
            "humidity": 45,
            "pressure_hPa": 1013.25,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.is_temp
        assert sp.is_baro
        assert sp.data["pressure"] == 1013.25
        assert sp.data["temp"] == pytest.approx(72.5, abs=0.1)


class TestFromJsonRain:
    def test_rain_mm_conversion(self):
        data = {
            "model": "Acurite-Rain899",
            "id": 0x12,
            "channel": 0,
            "battery_ok": 1,
            "rain_mm": 25.4,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.is_rain
        assert not sp.is_temp
        assert sp.data["total"] == pytest.approx(25.4 * MM2IN, abs=0.001)
        assert sp.data["units"] == "in"

    def test_rain_in_passthrough(self):
        data = {
            "model": "Acurite-Rain899",
            "id": 0x12,
            "channel": 0,
            "battery_ok": 1,
            "rain_in": 1.5,
            "rain_rate_in_h": 0.25,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.data["total"] == 1.5
        assert sp.data["rate"] == 0.25


class TestFromJsonWind:
    def test_wind_conversion(self):
        data = {
            "model": "Oregon-WGR800",
            "id": 0x33,
            "channel": 0,
            "battery_ok": 1,
            "wind_avg_m_s": 5.0,
            "wind_max_m_s": 10.0,
            "wind_dir_deg": 180,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.is_wind
        assert sp.data["speed"] == pytest.approx(5.0 * MPS2MPH, abs=0.1)
        assert sp.data["gust"] == pytest.approx(10.0 * MPS2MPH, abs=0.1)
        assert sp.data["direction"] == 180
        assert sp.data["units"] == "mph"


class TestFromJsonMoisture:
    def test_springfield_moisture(self):
        data = {
            "model": "Springfield Temperature & Moisture",
            "id": 0x07,
            "channel": 1,
            "battery_ok": 1,
            "temperature_C": 15.0,
            "moisture": 3,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.is_temp
        assert sp.is_moist
        assert sp.data["moisture"] == 3
        assert sp.data["temp"] == pytest.approx(59.0, abs=0.1)


class TestFromJsonSensorId:
    def test_sid_key_used_when_id_absent(self):
        data = {
            "model": "Acurite-Rain899",
            "sid": 0xFF,
            "channel": 2,
            "battery_ok": 1,
            "rain_mm": 10.0,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.sensor_id == "ff:02"


class TestFromJsonUnknownModel:
    def test_unknown_model_stays_none(self, caplog):
        data = {
            "model": "Unknown-Sensor-42",
            "id": 1,
            "channel": 0,
            "battery_ok": 1,
        }
        sp = SensorPacket()
        sp.from_json(data)
        assert sp.stype == IS_NONE
        assert "Unknown sensor type" in caplog.text


class TestAsJson:
    def test_includes_bat_and_sensor_id(self):
        sp = SensorPacket(bat=1, sensor_id="ae:01")
        result = sp.as_json()
        assert result["bat"] == 1
        assert result["sensor_id"] == "ae:01"

    def test_includes_data_fields(self):
        sp = SensorPacket(bat=1, sensor_id="ae:01", temp=72.5, humid=55.0)
        result = sp.as_json()
        assert result["temp"] == 72.5
        assert result["humid"] == 55.0

    def test_kwargs_merged(self):
        sp = SensorPacket(bat=1, sensor_id="ae:01")
        result = sp.as_json(name="Outside", topic="arwn/outside")
        assert result["name"] == "Outside"
        assert result["topic"] == "arwn/outside"

    def test_roundtrip_temp_humid(self):
        data = {
            "model": "Oregon-THGR810",
            "id": 0xAE,
            "channel": 1,
            "battery_ok": 1,
            "temperature_C": 25.0,
            "humidity": 60,
        }
        sp = SensorPacket()
        sp.from_json(data)
        result = sp.as_json()
        assert result["bat"] == 1
        assert result["sensor_id"] == "ae:01"
        assert result["temp"] == pytest.approx(77.0, abs=0.1)
        assert result["humid"] == 60.0
        assert "dewpoint" in result
