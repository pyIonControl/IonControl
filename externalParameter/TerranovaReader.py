# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import serial  #@UnresolvedImport @UnusedImport
import serial.tools.list_ports
import re
import math

import sys

isPy3 = sys.version_info[0] > 2

class TerranovaReader:
    @staticmethod
    def connectedInstruments():
        return [name for name, _, _ in serial.tools.list_ports.comports() ]

    def __init__(self, instrument='COM1', baud=9600, deviceaddr=253, timeout=1, settings=None):
        self.instrument = instrument
        self.baud = baud
        self.timeout = timeout
        self.conn = None
        self.deviceaddr = deviceaddr

    def open(self):
        self.conn = serial.Serial( self.instrument, self.baud, timeout=self.timeout)
        
    def close(self):
        self.conn.close()

    def write(self, text):
        if isPy3:
            data = text.encode('ascii')
        self.conn.write(data)

    def read(self, length):
        data = self.conn.read(length)
        return data.decode('ascii') if isPy3 else data

    def query(self, question, length=100):
        self.write(question)
        return self.read(length)
                
    def value(self):
        reply = self.query("F").rstrip('\n\r')
        m = re.match('\s*(\d+)\s+([-0-9]+)\s*', reply)
        if m is None:
            return 0
        mantissa = float(m.group(1))
        exponent = int(m.group(2))
        return mantissa * math.pow(10, exponent)

if __name__=="__main__":
    mks = TerranovaReader()
    mks.open()
    result = mks.value()
    print(result)
    mks.close()
    