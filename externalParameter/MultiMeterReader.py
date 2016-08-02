# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import visa   #@UnresolvedImport

class MultiMeterReader:
    @staticmethod
    def connectedInstruments():
        rm = visa.ResourceManager()
        return [name for name in rm.list_resources() if name.find('COM')!=0 ]

    def __init__(self, instrument=0, timeout=1000, settings=None):
        self.instrument = instrument
        self.timeout = timeout
        self.conn = None
        
    def open(self):
        self.rm = visa.ResourceManager()
        self.conn = self.rm.open_resource( self.instrument, timeout=self.timeout)
        self.conn.write("F1T4R-2RAZ1N5")
        
    def close(self):
        self.conn.close()
        
    def value(self):
        #return float(self.conn.query("N5H1"))
        return float(self.conn.query("F1T3"))
    
    


if __name__=="__main__":
    mks = MultiMeterReader()
    mks.open()
    mks.pr3()
    mks.close()
    