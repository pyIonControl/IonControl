# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import visa
from .RFSource import RFSource

class AFG3102(RFSource):
    def __init__(self, **kwargs):
        self.inst = None
        self.timeout = 1

    ## Initialize using pyVisa
    def init(self, **kwargs):
        if kwargs['resourceName']:
            self.inst = visa.instrument(kwargs['resourceName'])
            self.inst.timeout = self.timeout
        else:
            raise AFG3102Error(code=1)

    ## Returns the frequency setting in Hz.
    def getFreq(self, **kwargs):
        cmd = 'sour1:freq?'
        freq = self.inst.ask(cmd)
        return float(freq)

    def setFreq(self, freq, **kwargs):
        cmd = 'sour1:freq {0}'.format(str(freq))
        self.inst.write(cmd)

    def getAmp(self, **kwargs):
        cmd = 'sour1:volt:imm:ampl?'
        amp = self.inst.ask(cmd)
        return float(amp)

    def setAmp(self, amp, **kwargs):
        cmd = 'sour1:volt:ampl {0}'.format(str(amp))
        self.inst.write(cmd)

    def getPhase(self, **kwargs):
        raise AFG3102Error(code=2)

    def setPhase(self, phase, **kwargs):
        raise AFG3102Error(code=2)

    # Turns on the rf source.
    def turnOn(self, **kwargs):
        cmd = 'outp1:stat on'
        self.inst.write(cmd)

    # Turns off the rf source.
    def turnOff(self, **kwargs):
        cmd = 'outp1:stat off'
        self.inst.write(cmd)

    # Closes connetion to the rf source.
    def close(self, **kwargs):
        self.inst.close()
        self.inst = None

    def __del__(self):
        if self.inst:
            self.inst.close()

        del self.inst
        del self.timeout

class AFG3102Error(Exception):
    def __init__(self, code):
        self.code = code
        if code == 1:
            self.msg = '''The init funciton must have a resourceName
            argument. For example: init(resourceName='COM1').'''
        elif code == 2:
            self.msg = '''The command is currently unsupported.'''

    def __str__(self):
        ret = '\n\tCode: {0} \n\tMessage: {1}'.format(self.code,
                                                      self.msg)
