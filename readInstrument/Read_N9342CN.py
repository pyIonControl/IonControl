# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from trace import TraceCollection

import numpy
import visa #@UnresolvedImport

from . import ReadGeneric 


class N9342CN(ReadGeneric.ReadGeneric):
    def __init__(self, address):
        self.rm = visa.ResourceManager()
        self.GPIB = self.rm.open_resource( address)
        
    def readTrace(self):
        self.t = TraceCollection.TraceCollection()
        self.t.description["Instrument"] = self.GPIB.query("*IDN?")
        self.t.description["Center"] = float(self.GPIB.query(":FREQuency:CENTer?"))
        self.t.description["Start"] = float(self.GPIB.query(":FREQuency:STARt?") )
        self.t.description["Stop"] = float(self.GPIB.query(":FREQuency:STOP?"))
        self.t.description["Attenuation"] = self.GPIB.query(":POWer:ATTenuation?")
        self.t.description["PreAmp"] = self.GPIB.query(":POWer:GAIN:STATe?")
        #self.t.description["IntegrationBandwidth"] = self.GPIB.query("BANDwidth:INTegration?")
        self.t.description["ResolutionBandwidth"] = float(self.GPIB.query(":BANDwidth:RESolution?"))
        self.t.description["VideoBandwidth"] = float(self.GPIB.query(":BANDwidth:VIDeo?"))
        #self.t.description["ReferenceLevel"] = self.GPIB.query(":DISPlay:WINDow:TRACe:Y:NRLevel?")
        self.t.rawTrace = numpy.array(self.GPIB.query(":TRACe:DATA? TRACe1").split(","), dtype=float)
        self.t.Trace = self.t.rawTrace
        self.t.description["Step"] = (self.t.description["Stop"]-self.t.description["Start"])/(self.t.Trace.size-1)
        self.t.x = numpy.arange(self.t.description["Start"], self.t.description["Stop"]+0.5*self.t.description["Step"], self.t.description["Step"])
        self.t.y = self.t.Trace
        return self.t
        

if __name__== "__main__":
    Inst = N9342CN("USB0::0x0957::0xFFEF::SG05300073")
    t = Inst.readTrace()
    print(t.description)
    print(t.Trace)
    print(t.Trace.size)
    print(t.TraceX.size)
    Inst.save("Resonator_4.txt")
