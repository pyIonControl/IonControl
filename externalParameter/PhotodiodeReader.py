# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import serial  #@UnresolvedImport @UnusedImport
import re
import numpy
import serial.tools.list_ports

from modules.quantity import Q


class Settings:
    pass

class PhotoDiodeReader(object):
    @staticmethod
    def connectedInstruments():
        return [name for name, _, device in serial.tools.list_ports.comports() if device.find('FTDIBUS')!=-1 ]
    
    def __init__(self, instrument='COM1', baud=115200, deviceaddr=253, timeout=1, settings=None):
        self.instrument = instrument
        self.baud = baud
        self.conn = None
        self.deviceaddr = deviceaddr
        self.settings = settings if settings is not None else Settings()
        self.setDefaults()
        self.leftover = ""
        
    def setDefaults(self):
        self.settings.__dict__.setdefault('timeout', Q(500, 'ms'))
        self.settings.__dict__.setdefault('measureSeparation', Q(500, 'ms'))
        
    @property
    def measureSeparation(self):
        return self.settings.measureSeparation
    
    @measureSeparation.setter
    def measureSeparation(self, sep):
        self.settings.measureSeparation = sep
        self.writeMeasureSeparation()    
        
    @property
    def timeout(self):
        return self.settings.timeout
    
    @timeout.setter
    def timeout(self, val):
        self.conn.timeout = val.m_as('s')
        self.settings.timeout = val
        
    def open(self):
        self.conn = serial.Serial( self.instrument, self.baud, timeout=self.settings.timeout.m_as('s'), parity='N', stopbits=1)
        self.conn.write('afe -agc1\n\r')
        self.conn.read(1000)
        self.writeMeasureSeparation()
        
    def writeMeasureSeparation(self):
        self.conn.write('sdds -p{0:04d}\n\r'.format(int(self.settings.measureSeparation.m_as('ms'))))
        self.conn.read(1000)       
        
    def close(self):
        self.conn.close()
        
    def query(self, question=None, length=100, timeout=None):
        if question:
            self.conn.write(question)
        if timeout is not None:
            self.conn.timeout = timeout
            self.settings.timeout = timeout
        return self.conn.read(length)
                
    def value(self):
        raw = self.query(length=500)
        lastlinebreak = raw.rfind("\n\r")
        lines = (self.leftover + raw[:lastlinebreak]).split('\n\r')
        self.leftover = raw[lastlinebreak+2:]
        values = list()
        for line in lines:
            m = re.match('^(\d+)\s+(\d+)$', line)
            if m:
                gain, value = m.group(1), m.group(2)
                gain = int(gain)-1 if gain else 3
                values.append( int(value) / 2.**gain )
        return  numpy.mean(values) if values else None
    
    def paramDef(self):
        return [{'name': 'timeout', 'type': 'magnitude', 'value': self.timeout, 'tip': "wait time for communication", 'field': 'timeout'},
                {'name': 'measure separation', 'type': 'magnitude', 'value': self.measureSeparation, 'tip': "time between two reading", 'field': 'measureSeparation'}]


if __name__=="__main__":
    try:
        mks = PhotoDiodeReader(port=15)
        mks.open()
        result = mks.value()
        print(result)
        mks.close()
    except Exception as e:
        mks.close()
        raise
    