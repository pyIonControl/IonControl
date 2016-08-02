# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyDAQmx import Task
from PyDAQmx.DAQmxFunctions import DAQError
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from .DAQmxUtility import TriggerType
import ctypes
import numpy

class digFreqGenerator(object):
    def __init__(self):
        self.counter = ''
        self.Task = Task()
        self.initialized = False
        self.initialDelay = 0
        self.dutyCycle = 0.50
        self.frequency = 1e6
        self._numberOfPulses = 0
        self.status = 0
        self._startTriggerSource = ''
        self.triggerType = TriggerType.Software
        self.timeout = -1

    def _getStartTriggerSource(self):
        if self.initialized:
            buffSize = uInt32(255)
            buff = ctypes.create_string_buffer(buffSize.value)
            self.status = self.Task.GetDigEdgeStartTrigSrc(buff, buffSize)
            self._startTriggerSource = buff.value
        return self._startTriggerSource 

    def _setStartTriggerSource(self, value):
        if self.initialized:
            self.status = self.Task.SetDigEdgeStartTrigSrc(value)
            #value = self._getStartTriggerSource()
        self._startTriggerSource = value

    startTriggerSource = property(_getStartTriggerSource,
            _setStartTriggerSource)

    def _getNumberOfPulses(self):
        if self.initialized:
            sampPerChan = uInt32()
            self.status = self.Task.GetSampQuantSampPerChan(sampPerChan)
            self._numberOfPulses = sampPerChan.value
        return self._numberOfPulses

    def _setNumberOfPulses(self, value):
        if self.initialized:
            self.status = self.Task.SetSampQuantSampPerChan(value)
            if value > 0:
                self.status = self.Task.SetSampQuantSampMode(
                        DAQmx_Val_FiniteSamps)
            else:
                self.status = self.Task.SetSampQuantSampMode(
                        DAQmx_Val_ContSamps)
        self._numberOfPulses = value
            

    numberOfPulses = property(_getNumberOfPulses, _setNumberOfPulses)
        

    def init(self, counter=None):
        if counter is not None:
            self.counter = counter
        self.status = self.Task.CreateCOPulseChanFreq(self.counter, '',
                DAQmx_Val_Hz, DAQmx_Val_Low,
                numpy.float64(self.initialDelay),
                numpy.float64(self.frequency),
                numpy.float64(self.dutyCycle))
        if self._numberOfPulses > 0:
            self.status = self.Task.CfgImplicitTiming(DAQmx_Val_FiniteSamps,
                    uInt64(self._numberOfPulses))
        else:
            self.status = self.Task.CfgImplicitTiming(DAQmx_Val_ContSamps,
                    uInt64(int(1e6)))
        if self.triggerType == TriggerType.Hardware:
            self.status = self.Task.CfgDigEdgeStartTrig(
                    self._startTriggerSource, DAQmx_Val_Rising)
            self.status = self.Task.SetStartTrigRetriggerable(bool32(True))
        self.initialized = True

    def _getOutputTerm(self):
        buffSize = uInt32(255)
        buff = ctypes.create_string_buffer(buffSize.value)
        self.status = self.Task.GetCOPulseTerm(self.counter, buff,
                buffSize)
        return buff.value

    def _setOutputTerm(self, term = 'PFI0'):
        self.status = self.Task.SetCOPulseTerm(self.counter, term)

    outputTerm = property(_getOutputTerm, _setOutputTerm)

    def start(self):
        self.status = self.Task.StartTask()

    def waitUntilDone(self):
        self.status = self.Task.WaitUntilTaskDone(self.timeout)

    def stop(self):
        retriggerable = bool32()
        self.status = self.Task.GetStartTrigRetriggerable(retriggerable)
        try:
            if retriggerable == 0:
                self.status = self.Task.StopTask()
        except DAQError as e:
            print(e.error)
            print(retriggerable.value)
            if e.error == 200010 and retriggerable.value == 1:
                print('caught')
                pass
            else:
                raise e

    def close(self):
        self.status = self.Task.ClearTask()
        self.Task = Task()
        self.initialized = False
    
if __name__ == '__main__':
    from time import sleep
    try:
        clock = digFreqGenerator()
        clock.counter = 'PXI1Slot11/ctr0'
        clock.frequency = 30
        clock.numberOfPulses = 9
        clock.triggerType = 0
        #clock.startTriggerSource = 'Ctr1InternalOutput'
        #clock.startTriggerSource = 'PFI12'
        clock.init()
        clock.outputTerm = 'PFI4'
        clock.start()
        #sleep(2)
        clock.waitUntilDone()
        clock.stop()
    finally:
        clock.close()
    
