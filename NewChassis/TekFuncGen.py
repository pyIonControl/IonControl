# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import visa
from .RFSource import RFSource

class TekFuncGen(RFSource):
    def __init__(self, **kwargs):
        self.inst = None
        self.timeout = 1

    ## Initialize using pyVisa
    def init(self, **kwargs):
        if kwargs['resourceName']:
            self.inst = visa.instrument(kwargs['resourceName'])
            self.inst.timeout = self.timeout
        else:
            raise TekFuncGenError(code=1)

    ## Returns the frequency setting in Hz.
    def getFreq(self, **kwargs):
        if kwargs['channel']:
            channel = kwargs['channel']
        else:
            raise TekFuncGenError(code=3)
        cmd = 'sour{0}:freq?'.format(channel)
        freq = self.inst.ask(cmd)
        return float(freq)

    ## Sets the frequency setting in Hz.
    def setFreq(self, freq, **kwargs):
        if kwargs['channel']:
            channel = kwargs['channel']
        else:
            raise TekFuncGenError(code=3)
        cmd = 'sour{0}:freq {1}'.format(channel, freq)
        self.inst.write(cmd)
    
    ## Returns the amplitude setting in Volts. 
    def getAmp(self, **kwargs):
        if kwargs['channel']:
            channel = kwargs['channel']
        else:
            raise TekFuncGenError(code=3)
        cmd = 'sour{0}:volt:imm:ampl?'.format(channel)
        amp = self.inst.ask(cmd)
        return float(amp)

    ## Sets the amplitude setting in Volts.
    def setAmp(self, amp, **kwargs):
        if kwargs['channel']:
            channel = kwargs['channel']
        else:
            raise TekFuncGenError(code=3)
        cmd = 'sour{0}:volt:ampl {1}'.format(channel, amp)
        self.inst.write(cmd)

    def getPhase(self, **kwargs):
        raise TekFuncGenError(code=2)

    def setPhase(self, phase, **kwargs):
        raise TekFuncGenError(code=2)

    # Turns on the rf source.
    def turnOn(self, **kwargs):
        if kwargs['channel']:
            channel = kwargs['channel']
        else:
            raise TekFuncGenError(code=3)
        cmd = 'outp{0}:stat on'.format(channel)
        self.inst.write(cmd)

    # Turns off the rf source.
    def turnOff(self, **kwargs):
        if kwargs['channel']:
            channel = kwargs['channel']
        else:
            raise TekFuncGenError(code=3)
        cmd = 'outp{0}:stat off'.format(channel)
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

class TekFuncGenError(Exception):
    def __init__(self, code):
        self.code = code
        if code == 1:
            self.msg = '''The init funciton must have a resourceName
            argument. For example: init(resourceName='COM1').'''
        elif code == 2:
            self.msg = '''The command is currently unsupported.'''
        elif code == 3:
            self.msg = '''The function must have a channel argument.
            For example: getFreq(channel=0)'''

    def __str__(self):
        ret = '\n\tCode: {0} \n\tMessage: {1}'.format(self.code,
                self.msg)

