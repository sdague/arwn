from arwn import temperature

class Acurite5n1(object):
    def __init__(self, data):
        self.data = {}
        self.sensor_id = "%s:%s" % (data['id'], data.get('channel', 0))
        self.bat = data['battery_ok']
        if "temperature_F" in data:
            temp = temperature.Temperature(
                    "%sF" % data['temperature_F']).as_F()
            self.data['temp'] = round(temp.to_F(), 1)
            self.data['units'] = 'F'
            self.data['dewpoint'] = round(temp.dewpoint(data['humidity']), 1)
            self.data['humid'] = round(data['humidity'], 1)
        if "wind_avg_km_h" in data:
            self.data['speed'] = round(float(data['wind_avg_km_h']) / 1.609344, 1)
            self.data['direction'] = data['wind_dir_deg']
            self.data['units'] = 'mph'
    
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
    def is_wind(self):
        return "average" in self.data

    def as_json(self, **kwargs):
        data = dict(bat=self.bat, sensor_id=self.sensor_id)
        data.update(self.data)
        data.update(kwargs)
        return data