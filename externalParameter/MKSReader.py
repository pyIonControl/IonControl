# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import re
import sys

import serial  # @UnresolvedImport @UnusedImport
import serial.tools.list_ports

isPy3 = sys.version_info[0] > 2


class MKSReader:
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
        
    def setupDatalogger(self, time):
        self.write("@{0}DLT!{1};FF".format(self.deviceaddr, time))
        reply = self.read(100)
        print(reply)
        
    def startLogger(self):
        print(self.query("@{0}DLC!START;FF".format(self.deviceaddr)))

    def stopLogger(self):
        print(self.query("@{0}DLC!STOP;FF".format(self.deviceaddr)))
        
    def getLog(self):
        print(self.query("@{0}DL?;FF".format(self.deviceaddr), length=1000))

    def test(self):
        print(self.query("@{0}DLC?;FF".format(self.deviceaddr)))
        print(self.query("@{0}DLT?;FF".format(self.deviceaddr)))

    def pr3(self):
        devicestr = "@{0}".format(self.deviceaddr)
        reply = self.query("{0}PR3?;FF".format(devicestr))  
        m = re.match(devicestr+'ACK([0-9.E+-]+);FF', reply)
        return float(m.group(1))
        
    def value(self):
        return self.pr3()
    
    
if __name__=="__main__":
    mks = MKSReader('COM11')
    mks.open()
    print(mks.pr3())
    mks.close()
    