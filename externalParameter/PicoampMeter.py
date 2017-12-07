# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import re
from modules.quantity import Q, is_Q

try:
    import visa  #@UnresolvedImport
    hasVisa = True
except:
    hasVisa = False
    logging.getLogger(__name__).info( "visa loading failed. Proceeding without." )

def boolValue(boolean):
    return "ON" if boolean else "OFF"

class ZeroCheckRestore:
    """Encapsulate ZeroCheck in __enter__ __exit__ idiom"""
    def __init__(self, meter):
        self.meter = meter
    
    def __enter__(self):
        self.oldstate = self.meter.zeroCheck
        return self.meter

    def __exit__(self, exittype, value, traceback):
        self.meter.setZeroCheck(self.oldstate)

class PicoampMeterException(Exception):
    pass

class PicoampMeter:
    def __init__(self):
        self.zeroCheck = False
        self.voltageEnabled = False
        self.voltageRange = 10
        self.currentLimit = 25e-6
        self.voltage = 0
        self.autoRange = False
        self.isOpen = False
        self.instrument = None
    
    def open(self, instrument):
        self.close()
        if hasVisa:
            self.rm = visa.ResourceManager()
            self.instrument = self.rm.open_resource(instrument) #open visa session
            self.isOpen = True
        
    def close(self):
        if hasVisa and self.isOpen:
            self.instrument.close()
        
    def zero(self):
        if self.instrument:
            with ZeroCheckRestore(self):
                self.setZeroCheck(True)
                self.setCurrentRange(2e-9)
                self.instrument.write("INIT")
                self.instrument.write("SYST:ZCOR:ACQ")
                self.instrument.write("SYST:ZCOR ON")
                self.setAutoRange(False)
        else:
            logging.getLogger(__name__).error("Meter is not available")
        
    def reset(self):
        if self.instrument:        
            self.instrument.write("*RST")
        else:
            logging.getLogger(__name__).error("Meter is not available")
        
    
    def setVoltage(self, voltage):
        # if not is_Q(voltage):
        #     voltage = Q(voltage)
        if self.instrument:        
            self.instrument.write("SOUR:VOLT {0}".format(voltage.m_as("V")))
            self.voltage = voltage
        else:
            logging.getLogger(__name__).error("Meter is not available")
        
   
    def setCurrentLimit(self, limit):
        if limit in [25e-6, 25e-5, 25e-4, 25e-3]:
            if self.instrument:
                self.instrument.write("SOUR:VOLT:ILIM {0:.1e}".format(limit))
                self.currentLimit = limit
            else:
                logging.getLogger(__name__).error("Meter is not available")
        else:
            raise PicoampMeterException("{0:.1e} is not a valid current limit. Possible values are 2.5e-5, 2.5e-4, 2.5e-3, 2.5e-2 (Ampere)".format(limit))
    
    def read(self):
        if self.instrument:        
            answer = self.instrument.query("READ?")
            m = re.match("([-.+0-9E]+)([^,]*),([-.+0-9E]+),([-.+0-9E]+)", answer)
            if m:
                value, unit, second, third = m.groups()  #@UnusedVariable
                return float(value) 
        else:
            logging.getLogger(__name__).error("Meter is not available")
        return 0
    
    def setCurrentRange(self, currentRange):
        if self.instrument:        
            self.instrument.write("RANG {0:.1e}".format(currentRange))
        else:
            logging.getLogger(__name__).error("Meter is not available")
    
    def setVoltageRange(self, voltageRange):
        if voltageRange in [10, 50, 500]:
            if self.instrument:        
                self.instrument.write("SOUR:VOLT:RANG {0}".format(voltageRange))
                self.voltageRange = voltageRange
            else:
                logging.getLogger(__name__).error("Meter is not available")
        else:
            raise PicoampMeterException("{0} is not a valid voltage range. Possible values are 10, 50, 500 (Volt)".format(voltageRange))
            
    def voltageEnable(self, enable):
        if self.instrument:        
            self.instrument.write("SOUR:VOLT:STAT {0}".format(boolValue(enable)))
            self.voltageEnabled = enable
        else:
            logging.getLogger(__name__).error("Meter is not available")
    
    def setZeroCheck(self, enable):
        if self.instrument:        
            self.instrument.write("SYST:ZCH {0}".format( boolValue(enable)))
            self.zeroCheck = enable
        else:
            logging.getLogger(__name__).error("Meter is not available")
        
    def setAutoRange(self, enable):
        if self.instrument:        
            self.instrument.write("RANG:AUTO {0}".format( boolValue(enable)))
            self.autoRange = enable
        else:
            logging.getLogger(__name__).error("Meter is not available")
   
    