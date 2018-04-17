# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

# Attempt

import visa  # @UnresolvedImport
import serial  #@UnresolvedImport @UnusedImport
import serial.tools.list_ports

import sys

isPy3 = sys.version_info[0] > 2

class Settings:
    pass


class CryoCon22CReader(object):
    _outputChannels = {}
    sensorNames = ['A', 'B']

    @staticmethod
    def connectedInstruments():
        return [name for name, _, _ in serial.tools.list_ports.comports()]

    def __init__(self, instrument='COM4', baud=9600, deviceaddr=253, timeout=1, settings=None):
        self.instrument = instrument
        self.baud = baud
        self.timeout = timeout
        self.conn = None
        self.settings = settings if settings is not None else Settings()
        self.deviceaddr = deviceaddr
        self.setDefaults()

    def setDefaults(self):
        self.settings.__dict__.setdefault('sensor', 'A')

    @property
    def sensor(self):
        return self.settings.sensor

    @sensor.setter
    def sensor(self, sensor):
        # if self.conn:
        #     self.conn.write(':SENSE:FUNCTION "{0}"'.format(sensor))
        self.settings.sensor = sensor

    def paramDef(self):
        return [{'name': 'sensor', 'type': 'list', 'values': self.sensorNames, 'value': self.settings.sensor,
                     'field': 'sensor'}]

    def open(self):
        self.conn = serial.Serial(self.instrument, self.baud, timeout=self.timeout)

    def close(self):
        self.conn.close()

    def write(self, text):
        if isPy3:
            data = text.encode('ascii')
        self.conn.write(data)

    def read(self, length):
        data = self.conn.read(length)
        return data.decode('ascii') if isPy3 else data

    def query(self, question, length=1024):
        self.write(question)
        return self.read(length)

    def value(self):
        sensor = self.settings.sensor
        reply = self.query("INP? {0}\n".format(sensor)).rstrip('\n\r')
        #reply = self.query("INPUT?\sA\n")
        return float(reply)

    def value2(self):
        sensor = self.settings.sensor
        if sensor == 'A':
            sensor2 = 'B'
        else:
            sensor2 = 'A'
        reply2 = self.query("INP? {0}\n".format(sensor2)).rstrip('\n\r')
        return float(reply2)

if __name__ == "__main__":
    mks = CryoCon22CReader()
    mks.open()
    result = mks.value()
    print(result)
    mks.close()
