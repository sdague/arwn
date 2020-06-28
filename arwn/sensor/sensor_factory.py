import logging

from arwn.sensor.acurite5n1 import Acurite5n1

logger = logging.getLogger(__name__)

class SensorFactory(object):
    @staticmethod
    def create(data):
        if "model" not in data:
            return None
        
        if data["model"] == "Acurite-5n1":
            return SensorFactory.create_acurite_5n1(data)

        return None

    @staticmethod
    def create_acurite_5n1(data):
        if Acurite5n1.parse_time(data["time"]) != Acurite5n1.previous_time:
            logger.debug("time (%s) is not equal previous time (%s)" % (data["time"], Acurite5n1.previous_time))
            return Acurite5n1(data)
        else:
            return None