from datetime import datetime

from arwn.temperature import Temperature
from arwn.sensor.sensor import Sensor

class AcuriteTower(Sensor):
    previous_time = datetime.now()

    @staticmethod
    def parse_time(time):
        return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

    def __init__(self, data):
        self.data = {}
        if "id" in data:
            self.sensor_id = "%s:%s" % (data['id'], data.get('channel', 0))
        if "battery_ok" in data:
            self.bat = data['battery_ok']
        if "temperature_C" in data:
            temp = Temperature("%sC" % data['temperature_C']).as_C()
            self.data['temp'] = round(temp.to_F(), 1)
            self.data['units'] = 'F'
            self.data['dewpoint'] = round(temp.dewpoint(data['humidity']), 1)
            self.data['humid'] = round(data['humidity'], 1)
        self.log_historical_data(data)
    
    def log_historical_data(self, data):
        if "time" in data:
            AcuriteTower.previous_time = AcuriteTower.parse_time(data['time'])

    @property
    def is_wind(self):
        return False

    @property
    def is_temp(self):
        return "temp" in self.data

    @property
    def is_baro(self):
        return False

    @property
    def is_rain(self):
        return False

    @property
    def is_moist(self):
        return False

    def as_wind(self):
        return self

    def as_temp(self):
        return self

    def as_baro(self):
        return self

    def as_rain(self):
        return self

    def as_moist(self):
        return self

    def as_json(self, **kwargs):
        data = dict(bat=self.bat, sensor_id=self.sensor_id)
        data.update(self.data)
        data.update(kwargs)
        return data