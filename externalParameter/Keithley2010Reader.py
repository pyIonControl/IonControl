# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import visa  #@UnresolvedImport

class Settings:
    pass

class Keithley2010Reader(object):
    _outputChannels = {}
    modeNames = ['Voltage:DC', 'Voltage:AC', 'Current:DC', 'Current:AC', 'Resistance', 'FResistance']
    @staticmethod
    def connectedInstruments():
        rm = visa.ResourceManager()
        return [name for name in rm.list_resources() if name.find('COM')!=0 ]

    def __init__(self, instrument=0, timeout=1000, settings=None):
        self.instrument = instrument
        self.timeout = timeout
        self.conn = None
        self.settings = settings if settings is not None else Settings()
        self.setDefaults()
        
    def setDefaults(self):
        self.settings.__dict__.setdefault('digits', 8)
        self.settings.__dict__.setdefault('averagePoints', 100 )
        self.settings.__dict__.setdefault('channelSettings',  dict())
        self.settings.__dict__.setdefault('mode', 'Voltage:DC')

    def open(self):
        self.rm = visa.ResourceManager()
        self.conn = self.rm.open_resource( self.instrument, timeout=self.timeout)
        self.mode = self.mode
        self.digits = self.digits
        self.averagePoints = self.averagePoints 
        
    @property
    def mode(self):
        return self.settings.mode
    
    @mode.setter
    def mode(self, mode):
        if self.conn:
            self.conn.write(':SENSE:FUNCTION "{0}"'.format(mode))
        self.settings.mode = mode
        self.digits = self.digits
        self.averagePoints = self.averagePoints
        
    @property
    def digits(self):
        return self.settings.digits
    
    @digits.setter
    def digits(self, d):
        self.conn.write(":SENSE:{1}:Digits {0}".format(d, self.settings.mode))
        self.settings.digits = d
        
    @property
    def averagePoints(self):
        return self.settings.averagePoints
    
    @averagePoints.setter
    def averagePoints(self, p):
        self.conn.write(":SENSE:{1}:Average:Count {0}".format(p, self.settings.mode))
        self.settings.averagePoints = p
    
    def close(self):
        self.conn.close()
        
    def value(self):
        #return float(self.conn.query("N5H1"))
        return float(self.conn.query(":SENSE:DATA?"))
    
    def paramDef(self):
        return [{'name': 'timeout', 'type': 'int', 'value': self.settings.digits, 'limits': (4, 8), 'tip': "wait time for communication", 'field': 'digits'},
                {'name': 'average points', 'type': 'int', 'value': self.settings.averagePoints, 'limits': (1, 100), 'tip': "points to average", 'field': 'averagePoints'},
                {'name': 'mode', 'type': 'list', 'values': self.modeNames, 'value': self.settings.mode, 'field': 'mode'}]

    


if __name__=="__main__":
    mks = Keithley2010Reader()
    mks.open()
    mks.pr3()
    mks.close()
    