from datetime import datetime
from arwn.temperature import Temperature
from arwn.sensor.sensor import Sensor

class Acurite5n1(Sensor):
    previous_time = datetime.now()
    previous_rain_in = 0.000

    @staticmethod
    def parse_time(time):
        return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

    def __init__(self, data):
        self.data = {} 
        if "id" in data:
            self.sensor_id = "%s:%s" % (data['id'], data.get('channel', 0))
        if "battery_ok" in data:
            self.bat = data['battery_ok']
        if "temperature_F" in data:
            temp = Temperature("%sF" % data['temperature_F']).as_F()
            self.data['temp'] = round(temp.to_F(), 1)
            self.data['temp_units'] = 'F'
            self.data['dewpoint'] = round(temp.dewpoint(data['humidity']), 1)
            self.data['humid'] = round(data['humidity'], 1)
        if "wind_dir_deg" in data:
            self.data['speed'] = round(float(data['wind_avg_km_h']) / 1.609344, 1)
            self.data['direction'] = data['wind_dir_deg']
            self.data['wind_units'] = 'mph'
        if "rain_in" in data:
            self.data['total'] = round(data['rain_in'], 2)
            self.data['rain_rate'] = round(self.calculate_rain_rate(data['time'], data['rain_in']), 2)
            self.data['rain_units'] = 'in'
        self.log_historical_data(data)
    
    def log_historical_data(self, data):
        if "time" in data:
            Acurite5n1.previous_time = Acurite5n1.parse_time(data['time'])
        if "rain_in" in data:            
            Acurite5n1.previous_rain_in = data['rain_in']

    def calculate_rain_rate(self, time, rain_in):
        parsed_time = Acurite5n1.parse_time(time)        
        rain_amount = rain_in - Acurite5n1.previous_rain_in
        time_difference = (parsed_time - Acurite5n1.previous_time).seconds
        rain_rate_per_minute = (rain_amount / time_difference) * 60

        return rain_rate_per_minute
    
    @property
    def is_temp(self):
        return "temp" in self.data

    @property
    def is_baro(self):
        return False

    @property
    def is_rain(self):
        return "total" in self.data

    @property
    def is_wind(self):
        return "speed" in self.data

    @property
    def is_moist(self):
        return False

    def as_wind(self):
        newSensor = Acurite5n1({})
        newSensor.bat = self.bat
        newSensor.sensor_id = self.sensor_id
        newSensor.data['speed'] = self.data['speed']
        newSensor.data['direction'] = self.data['direction']
        newSensor.data['units'] = self.data['wind_units']
        return newSensor
    
    def as_temp(self):
        newSensor = Acurite5n1({})
        newSensor.bat = self.bat
        newSensor.sensor_id = self.sensor_id
        newSensor.data['temp'] = self.data['temp']
        newSensor.data['units'] = self.data['temp_units']
        newSensor.data['dewpoint'] = self.data['dewpoint']
        newSensor.data['humid'] = self.data['humid']
        return newSensor

    def as_baro(self):
        return self

    def as_rain(self):
        newSensor = Acurite5n1({})
        newSensor.bat = self.bat
        newSensor.sensor_id = self.sensor_id
        newSensor.data['total'] = self.data['total']
        newSensor.data['units'] = self.data['rain_units']
        newSensor.data['rate'] = self.data['rain_rate']
        return newSensor

    def as_moist(self):
        return self

    def as_json(self, **kwargs):
        data = dict(bat=self.bat, sensor_id=self.sensor_id)
        data.update(self.data)
        data.update(kwargs)
        return data