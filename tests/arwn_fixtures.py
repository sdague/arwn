
import os.path

import fixtures


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
