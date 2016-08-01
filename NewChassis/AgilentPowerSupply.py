# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import visa
from .PowerSupply import PowerSupply
from numpy import linspace


class AgilentPowerSupply(PowerSupply):

    def __init__(self, alias = "doppler"):
        # Voltage to frequency calibration
        #self.a = -143.364
        #self.b = 1653.218

        #self.a = -142.909
        #self.b = 1580.455

        # 1/8/13
        self.a = 72.27
        self.b = -323.55

    def init(self, **kwargs):
        if kwargs['resourceName']:
            alias = kwargs['resourceName']
        else:
            raise AgilentPSError(code=1)
        self.ps = visa.instrument( alias )

    def set_voltage(self, volts):
        #self.write("volt " + str(volts) )
        self.write("appl " + str(volts) + ", 0" )
    
    def set_current(self, current):
        self.write("curr " + str(current))

    def voltage(self):
        return float( self.ask("meas:volt?") )

    def current(self):
        return float( self.ask("meas:curr?") )

    def move_to_voltage(self, new_voltage, steps=100):
        #curVolt = self.voltage()
        #if curVolt < new_voltage:
        for v in linspace(self.voltage(), new_voltage, steps):
            self.set_voltage(v)
        #else:
        #    for v in linspace(new_voltage, curVolt, steps):
        #        self.set_voltage(v)
        #        print v

    def write(self, cmd):
        self.ps.write(cmd)

    def ask(self, cmd):
        return self.ps.ask(cmd)

    def close(self):
        self.ps.close()

    def freq_to_volt( self, f ):
        #self.a = -143.364
        #self.b = 1653.218
        return (f - self.b)/(self.a)
    
    def set_freq(self, f ):
        self.set_voltage( self.freq_to_volt(f) )

    def move_to_freq(self, f, steps=20):
        self.move_to_voltage( self.freq_to_volt(f), steps)

    def volt_to_freq(x):
    #    return (-143.214)*x + 1689.179
        return self.a*x + self.b


