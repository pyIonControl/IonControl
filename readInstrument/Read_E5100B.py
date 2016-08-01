# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from trace import TraceCollection

import numpy
import visa #@UnresolvedImport

from . import ReadGeneric


class E5100B(ReadGeneric.ReadGeneric):
    def __init__(self, address):
        self.rm = visa.ResourceManager()
        self.GPIB = self.rm.open_resource( address)
        
    def readTrace(self):
        self.t = TraceCollection.TraceCollection()
        self.t.description["Instrument"] = self.GPIB.query("*IDN?")
        self.t.description["Center"] = float(self.GPIB.query("CENT?"))
        self.t.description["Start"] = float(self.GPIB.query("STAR?") )
        self.t.description["Stop"] = float(self.GPIB.query("STOP?"))
        self.t['rawTrace'] = numpy.array(self.GPIB.query("OUTPDATA?").split(","), dtype=float)
        self.t.Trace = self.t.rawTrace.view(complex)
        self.t.description["Step"] = (self.t.description["Stop"]-self.t.description["Start"])/(self.t.Trace.size-1)
        self.t['x'] = numpy.arange(self.t.description["Start"], self.t.description["Stop"]+self.t.description["Step"], self.t.description["Step"])
        self.t['y'] = 10*numpy.log(numpy.abs(self.t.Trace))
        self.t['real'] = numpy.real(self.Trace)
        self.t['imaginary'] = numpy.imag(self.Trace)
        self.t['amplitude'] = numpy.imag(self.Trace)
        return self.t
        
if __name__== "__main__":
    Inst = E5100B("GPIB::17")
    t = Inst.readTrace()
    print(t.description)
    print(numpy.abs(t.Trace))
    print(t.Trace.size)
    print(t.TraceX.size)
    Inst.save("Resonator_4.txt") 