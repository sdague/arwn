

import os.path
import subprocess
import time

import fixtures
import paho.mqtt.client as mqtt


class CaptureStdout(fixtures.Fixture):

    def setUp(self):
        super(CaptureStdout, self).setUp()
        self.stdout = fixtures.StringStream('stdout')
        self.useFixture(self.stdout)
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout.stream))

    def __str__(self):
        return self.stdout._details["stdout"].as_text()


class SampleConfig(fixtures.Fixture):

    def setUp(self):
        super(SampleConfig, self).setUp()
        tmpdir = self.useFixture(fixtures.TempDir()).path
        self._path = os.path.join(tmpdir, "config.yml")
        with open(self._path, 'w') as f:
            f.write("""device: /dev/ttyUSB0
logfile: test.log
mqtt:
  server: 10.42.0.3
names:
  "ec:01": "Outside"
  "65:00": "Rain"
  "33:00": "Wind"
  "a9:04": "Freezer"
  "8c:00": "Refrigerator"
  "ce:08": "Arwen Room"
  "07:05": "Office"
  "e3:02": "Bomb Shelter"
  "de:01": "Subaru"
  "8e:01": "Cold Frame"
  "55:09": "Bed Room"
  "e9:04": "Garage"
""")

    @property
    def path(self):
        return self._path


class MosquittoSetupFail(Exception):
    pass


class MosquittoFail(Exception):
    pass


class MosquittoReal(fixtures.Fixture):

    def _pick_port(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        addr, self.port = s.getsockname()
        s.close()

    def setUp(self):
        super(MosquittoReal, self).setUp()
        tmpdir = self.useFixture(fixtures.TempDir()).path
        self._pick_port()
        config = os.path.join(tmpdir, "mqtt.conf")
        with open(config, 'w') as f:
            f.write("""
pid_file %(tmpdir)s/mosquitto.pid
persistence true
persistence_location %(tmpdir)s
log_dest file %(tmpdir)s/mosquitto.log
listener %(port)d
""" % {'tmpdir': tmpdir, 'port': self.port})

        try:
            self.mqtt = subprocess.Popen(["mosquitto", "-c", config])
        except OSError:
            raise MosquittoSetupFail("Couldn't find installed mosquitto")
        self.addCleanup(self.mqtt.kill)

        for x in range(100):
            try:
                c = mqtt.Client()
                c.connect("localhost", self.port)
                c.disconnect()
                break
            except:
                time.sleep(0.1)
        else:
            raise MosquittoFail("couldn't start mosquitto")
