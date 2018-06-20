# uncompyle6 version 3.2.0
# Python bytecode 3.5 (3351)
# Decompiled from: Python 3.5.4 (v3.5.4:3f56838, Aug  8 2017, 02:17:05) [MSC v.1900 64 bit (AMD64)]
# Embedded file name: C:\Users\Public\Documents\Programming\IonControl\externalParameter\Agilent34401Reader.py
# Compiled at: 2018-03-09 14:26:01
# Size of source mod 2**32: 3358 bytes
import visa

class Settings:
    pass


class Agilent34401Reader(object):
    _outputChannels = {}
    modeNames = {'Voltage:DC': 'MEAS:VOLT:DC?', 'Voltage:AC': 'MEAS:VOLT:AC?', 
     'Current:DC': 'MEAS:CURR:DC?', 'Current:AC': 'MEAS:CURR:AC?', 
     'Resistance': 'MEAS:RES?', 'FResistance': 'MEAS:FRES?'}

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
        self.settings.__dict__.setdefault('digits', 8)
        self.settings.__dict__.setdefault('averagePoints', 100)
        self.settings.__dict__.setdefault('channelSettings', dict())
        self.settings.__dict__.setdefault('mode', 'Voltage:DC')

    def open(self):
        self.rm = visa.ResourceManager()
        self.conn = self.rm.open_resource(self.instrument, timeout=self.timeout)
        self.mode = self.mode
        self.digits = self.digits
        self.averagePoints = self.averagePoints

    @property
    def mode(self):
        return self.settings.mode

    @mode.setter
    def mode(self, mode):
        if self.conn:
            pass
        self.settings.mode = mode
        self.digits = self.digits
        self.averagePoints = self.averagePoints

    @property
    def digits(self):
        return self.settings.digits

    @digits.setter
    def digits(self, d):
        self.settings.digits = d

    @property
    def averagePoints(self):
        return self.settings.averagePoints

    @averagePoints.setter
    def averagePoints(self, p):
        self.settings.averagePoints = p

    def close(self):
        self.conn.close()

    def value(self):
        return float(self.conn.query(self.modeNames[self.settings.mode]))

    def paramDef(self):
        return [
         {'name': 'timeout', 'type': 'int', 'value': self.settings.digits, 'limits': (4, 8), 'tip': 'wait time for communication', 'field': 'digits'},
         {'name': 'average points', 'type': 'int', 'value': self.settings.averagePoints, 'limits': (1, 100), 'tip': 'points to average', 'field': 'averagePoints'},
         {'name': 'mode', 'type': 'list', 'values': list(self.modeNames.keys()), 'value': self.settings.mode, 'field': 'mode'}]


if __name__ == '__main__':
    mks = Keithley2010Reader()
    mks.open()
    mks.pr3()
    mks.close()
# okay decompiling C:/Users/Public/Documents/Programming/IonControl/externalParameter/__pycache__\Agilent34401Reader.cpython-35.pyc
