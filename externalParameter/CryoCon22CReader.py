# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

# Attempt

import visa  # @UnresolvedImport


class Settings:
    pass


class CryoCon22CReader(object):
    _outputChannels = {}
    sensorNames = ['A', 'B']

    @staticmethod
    def connectedInstruments():
        rm = visa.ResourceManager()
        return [name for name in rm.list_resources() if name.find('COM') != 0]

    def __init__(self, instrument=0, timeout=1000, settings=None):
        self.instrument = instrument
        self.timeout = timeout
        self.conn = None
        self.settings = settings if settings is not None else Settings()
        self.setDefaults()

    def setDefaults(self):
        #self.settings.__dict__.setdefault('digits', 8)
        #self.settings.__dict__.setdefault('averagePoints', 100)
        #self.settings.__dict__.setdefault('channelSettings', dict())
        self.settings.__dict__.setdefault('sensor', 'A')

    def open(self):
        self.rm = visa.ResourceManager()
        self.conn = self.rm.open_resource(self.instrument, timeout=self.timeout)
        self.sensor = self.sensor
        #self.digits = self.digits
        #self.averagePoints = self.averagePoints

    @property
    def sensor(self):
        return self.settings.sensor

    @sensor.setter
    def sensor(self, sensor):
       # if self.conn:
       #     self.conn.write(':SENSE:FUNCTION "{0}"'.format(sensor))
        self.settings.sensor = sensor
       # self.digits = self.digits
       # self.averagePoints = self.averagePoints

   # @property
   # def digits(self):
   #     return self.settings.digits

   # @digits.setter
   # def digits(self, d):
   #     self.conn.write(":SENSE:{1}:Digits {0}".format(d, self.settings.mode))
   #     self.settings.digits = d

   # @property
   # def averagePoints(self):
   #     return self.settings.averagePoints

   # @averagePoints.setter
   # def averagePoints(self, p):
   #     self.conn.write(":SENSE:{1}:Average:Count {0}".format(p, self.settings.mode))
   #     self.settings.averagePoints = p

    def close(self):
        self.conn.close()

    def value(self):
        # return float(self.conn.query("N5H1"))
        return float(self.conn.query("INP? {0}".format(sensor)))

   # def paramDef(self):
   #     return [{'name': 'timeout', 'type': 'int', 'value': self.settings.digits, 'limits': (4, 8),
   #              'tip': "wait time for communication", 'field': 'digits'},
   #             {'name': 'average points', 'type': 'int', 'value': self.settings.averagePoints, 'limits': (1, 100),
   #              'tip': "points to average", 'field': 'averagePoints'},
   #             {'name': 'mode', 'type': 'list', 'values': self.modeNames, 'value': self.settings.mode,
   #              'field': 'mode'}]


if __name__ == "__main__":
    mks = CryoCon22CReader()
    mks.open()
    mks.pr3()
    mks.close()
