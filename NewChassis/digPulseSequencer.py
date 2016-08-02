# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os
import numpy
from .DigitalOutput import DigitalOutput
from .DAQmxUtility import Mode, TriggerType
from .digFreqGenerator import digFreqGenerator
from .digitalBufferManipulation import digitalBufferManipulation
from .digitalBufferManipulation import digitalBufferManipulationU16

## This class implements a digital pulse sequencer using digital lines on a
#  DAQmx compatible device.
class digPulseSequencer(object):
    ## This funciton is a constructor for the digPulseSequencer class.
    #
    #  It creates the internal variables required to perform functions within the
    #  class. This function does not initialize any hardware.
    def __init__(self):
        self._clock = digFreqGenerator()
        self._do = DigitalOutput()
        self._digBuff = digitalBufferManipulation()

        ## The frequency of the sample clock in Hz.
        self.sampleClockFreq = 10E6

        ## The DAQmx counter port that generates the sample clock.
        self.sampleClockCounter = 'PXI1Slot9/ctr0'

        ## The DAQmx digital lines to use to generate the digital data.
        self.channels = 'PXI1Slot9/port0/line0:7' 

        ## A list representing the last value of the digital lines (default 0).
        #
        #  Sometimes the final value of a digital waveform needs to be something
        #  other than 0.
        self.lastValues = []
        for i in range(8):
            self.lastValues.append(False)

        ## The generation mode (default None).
        self.mode = 'Finite'

    def _getMode(self):
        mode = self._do.mode
        if mode == Mode.Finite:
            modeStr = 'Finite'
        elif mode == Mode.Static:
            modeStr = 'Static'
        elif mode == Mode.Continuous:
            modeStr = 'Continuous'
        else:
            modeStr = 'Unknown'
        return modeStr

    def _setMode(self, value):
        if value == 'Finite':
            self._do.mode = Mode.Finite
        elif value == 'Static':
            self._do.mode = Mode.Static
        elif value == 'Continuous':
            self._do.mode = Mode.Continuous
        else:
            errorStr = '''Invalid value "{0}".
            Expecting "Finite", "Static", or "Continuous"'''
            errorStr.format(str(value))
            raise ValueError()

    mode = property(_getMode, _setMode)

    def _getStartTriggerSource(self):
        return self._clock.startTriggerSource

    def _setStartTriggerSource(self, value):
        #self.startTriggerSource = ''
        self._clock.startTriggerSource = value

    ## A DAQmx PFI line used to trigger digital generation.
    startTriggerSource = property(_getStartTriggerSource,
            _setStartTriggerSource)

    def _getClockTerm(self):
        self._clockTerm = self._clock.outputTerm
        return self._clockTerm

    def _setClockTerm(self, value):
        self._clockTerm = value
        self._clock.outputTerm = value

    ## A DAQmx terminal to use for the sample clock.
    clockTerm = property(_getClockTerm, _setClockTerm)
    

    ## This method will initialize the DAQmx card according to its input
    #  parameters.
    #  @param self The object reference.
    #  @param **kwargs Keword arguments.  The following keyworks are available:
    #  clockTerm - The DAQmx counter used to generated the clock.
    #  triggerTerm - The DAQmx terminal to use as a start trigger.
    def init(self, **kwargs):
        modeStr = kwargs.get('mode', None)
        clockTerm = kwargs.get('clockTerm', 'Ctr0Out')
        triggerTerm = kwargs.get('triggerTerm', 'Ctr1Out')
        if modeStr is not None:
            self._setMode(modeStr)
        self._digBuff.sampleRate = self.sampleClockFreq

        if self.triggerType == TriggerType.Hardware:
            self._clock.triggerType = TriggerType.Hardware
            digPS.do.mode = Mode.Continuous

        self._clock.frequency = self.sampleClockFreq
        self._clock.init(self.sampleClockCounter)
        self._clock.outputTerm = clockTerm

        self._do.clkSource = 'Ctr0InternalOutput'
        self._do.sampleClock = self.sampleClockFreq
        self._do.init(self.channels)

    def writeDelayWidth(self, delayWidthDict):
        self._digBuff.delayAndWidth(delayWidthDict)
        self._digBuff.lastValues(self.lastValues)
        self._do.samplesPerChannel = len(self._digBuff.data)
        if self.triggerType == TriggerType.Hardware:
            self._clock.numberOfPulses = self._do.samplesPerChannel
        self._do.writeToBuffer(self._digBuff.data)

    ## This method will start the digital generation.
    #  @param self The object reference.
    def start(self):
        if self.mode == 'Continuous':
            self._do.start()
            self._clock.start()
        else:
            self._do.start()
            self._clock.start()
            self._do.waitUntilDone()
            self._do.stop()

    ## This method will stop the digital generation.
    #  @param self The object reference.
    def stop(self):
        self._clock.stop()
        self._do.stop()

    ## This method will clock the connection to the DAQmx device.
    def close(self):
        if self._clock:
            print('closing clock')
            self._clock.stop()
            self._clock.close()

        if self._do:
            print('closing do')
            self._do.close()

## This is an interface class for implementing a digital pulse sequencer.  Classes
#  should only inherit from this class.  Calling methods from this class directly
#  will result in errors.
class IPulseSequencer(object):
    ## Interface method for the IPulseSequence class constructor. 
    def __init__(self):
        raise NotImplementedError('__init__() method not implemented')

    ## Interface method for initializing hardware.
    def init(self, **kwargs):
        raise NotImplementedError('init() method not implemented')

    ## Interface method for writing digital data to the device generating the
    #  pulse sequence.
    def writeDelayWidth(self, delayWidthDict):
        raise NotImplementedError('writeDelayWidth() method not implemented')

    ## Interface method for starting the pulse generation.
    def start(self):
        raise NotImplementedError('start() method not implemented')

    ## Interface method for stoping the pulse generation.
    def stop(self):
        raise NotImplementedError('stop() method not implemented')

    ## Interface method for closing the connection to the device generating the
    #  pulse sequence.
    def close(self):
        raise NotImplementedError('close() method not implemented')

class DDSRioPulseSequencer(IPulseSequencer):
    def __init__(self, **kwargs):
        from devices.ddsRio import ddsRio
        if 'clientType' in kwargs:
            clientType = kwargs.pop('clientType')
        else:
            clientType = 'serial'
        if 'device' not in kwargs:
            kwargs['device'] = 'COM1'

        print(clientType)
        self.rio = ddsRio(clientType, **kwargs)
        self.DOPort = self.rio.DOPort
        self._digBuff = digitalBufferManipulationU16()
        self._digBuff.sampleRate = self.DOPort.sampleRate
        self.lastValues = []
        for i in range(16):
            self.lastValues.append(False)

    def _getSampleRate(self):
        sampleRate = self.DOPort.sampleRate
        self._digBuff.sampleRate = sampleRate
        return sampleRate

    def _setSampleRate(self, sampleRate):
        self.DOPort.sampleRate = sampleRate
        self._digBuff.sampleRate = sampleRate

    sampleRate = property(_getSampleRate, _setSampleRate)

    def _getRepeats(self):
        return self.DOPort.repeats

    def _setRepeats(self, repeats):
        self.DOPort.repeats = repeats

    repeats = property (_getRepeats, _setRepeats)

    def writeDelayWidth(self, delayWidthDict):
        self._digBuff.delayAndWidth(delayWidthDict)
        self._digBuff.lastValues(self.lastValues)
        buff = self._digBuff.data.tolist()
        buffLen = len(buff)
        maxBuffSize = 2048
        if buffLen > maxBuffSize:
            errStr = ''' The buffer size is too big.
                value: {0}
                max: {1}

                Try changing the sampleRate to a smaller value.
                sampleRate: {2}
                '''
            raise ValueError(errStr.format(buffLen, maxBuffSize,
                self.DOPort.sampleRate))
        self.DOPort.writeBuffer(buff)

    def start(self):
        self.DOPort.swTrig()

    def close(self):
        self.rio.close()

if __name__== '__main__':
    from time import sleep
    from PyDAQmx.DAQmxTypes import *

    try:
        ## Setup the trigger
        digTrig = digFreqGenerator()
        digTrig.counter = 'PXI1Slot11/ctr0'
        digTrig.frequency = 30
        digTrig.numberOfPulses = 20
        digTrig.triggerType = 0
        digTrig.init()
        digTrig.outputTerm = 'PFI4'

        digPS = digPulseSequencer()
        digPS.sampleClockFreq = 100E3
        digPS.triggerFreq = 100
        digPS.sampleClockCounter = 'PXI1Slot9/ctr0'
        digPS.triggerCounter = 'PXI1Slot11/ctr0'
        digPS.channels = 'PXI1Slot9/port0/line0:7' 
        digPS.triggerType = 1
        digPS.init(clockTerm = 'PFI3',
                triggerTerm = 'PFI4')
        digPS.startTriggerSource = 'PFI12'
        testData = {0: ((0, 1e-3), (3e-3, 2e-3))}
        print(testData)
        digPS.writeDelayWidth(testData)
        print(digPS.digBuff.data)
        digPS.start()
        digTrig.start()
        digTrig.waitUntilDone()
        digPS.stop()
        digTrig.stop()

    finally:
        digTrig.close()
        digPS.close()
