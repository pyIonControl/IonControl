# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyDAQmx import Task, DAQmxConnectTerms, DAQmxDisconnectTerms
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from . import DAQmxUtility as dutil
import ctypes
import numpy

## This class will acquire data from analog inputs using pyDAQmx.
class AnalogInput(object):
    ## This function is a constructor for the AnalogInput class.
    #
    # It creates the internal variables required to perform functions within the
    # class. This function does not initialize any hardware.
    def __init__(self):

        ## The DAQmx task reference.
        self.taskRef = Task()

        ## A boolean that is set to True when the AnalogInput card is initialized.
        self.initialized = False

        ## This is the status of the DAQmx task.
        #
        #  A value greater than 0 means that an error has occurred. When the status
        #  is greater than 0 an error should be reported by the class.
        self.status = int32()

        ## @var sampleRate
        #  This is the sample rate of the analog input.
        self._sampleRate = 100e3

        ## @var samplesPerChannel
        #  This is the number of samples per channel that will be
        #  acquired in Finite mode.
        self._samplesPerChannel = 100

        ## @var numChannels
        #  This is the number of channels configured in the task.
        self._numChannels = 0

        ## This is the timeout in seconds for functions in the task to timeout.
        self.timeout = 1

        ## This is the mode of operation for the analog inputs.
        #
        #  There are currently three modes available.
        #  Static mode is where one static voltage is acquired with no need
        #  for a sample clock.
        #  Finite mode is where a finite number of voltages will be acquired at a
        #  sample clock rate.
        #  Continuous mode is where a sequence of voltages are generated at a sample
        #  rate and then repeated until the stop() method is called.
        self.mode = dutil.Mode.Static

    ## Initializes the analog inputs based on the object's configuration.
    #  @param self The object pointer.
    #  @param physicalChannel A string representing the device and analog
    #  input channels. Example Value: "PXI1Slot3/ao0:7"
    def init(self, physicalChannel):
        self.__createTask(physicalChannel)
        self.getNumChannels()
        self.initialized = True

        #Static Mode
        if self.mode == dutil.Mode.Static:
            self.setSampleRate(self._sampleRate)
            self.setSamplesPerChannel(1)

    def __createTask(self, physicalChannel):
        """
        This is a private method that creates the Task object for use inside the
        AnalogInput class."""
        terminalConfig = DAQmx_Val_Cfg_Default
        self.status = self.taskRef.CreateAIVoltageChan(physicalChannel, "",
                terminalConfig, -10, 10, DAQmx_Val_Volts, None)

    ## This function returns the sample rate configured in the DAQmx Task.
    #  @param self The object pointer.
    def getSampleRate(self):
        if self.initialized:
            sampleRate = float64()
            self.status = self.taskRef.GetSampClkRate(ctypes.byref(sampleRate))
            self._sampleRate = sampleRate.value
        return self._sampleRate

    ## This funciton sets the sample rate in the DAQmx Task.
    #  @param self The object pointer.
    #  @param value The value of the sample rate.
    def setSampleRate(self, value):
        if self.initialized:
            self.status = self.taskRef.SetSampClkRate(float64(value))
        self._sampleRate = value

    sampleRate = property(getSampleRate, setSampleRate)

    ## This function returns the samples per channel configured in the DAQmx Task.
    #  @param self The object pointer.
    def getSamplesPerChannel(self):
        if self.initialized:
            samplesPerChannel = uInt64()
            self.status = self.taskRef.GetSampQuantSampPerChan(
                    ctypes.byref(samplesPerChannel))
            self._samplesPerChannel = samplesPerChannel.value
        return self._samplesPerChannel

    ## This function sets the samples per channel in the DAQmx Task.
    #  @param self The object pointer.
    #  @param value The value to set the samples per channel.
    def setSamplesPerChannel(self, value):
        if self.initialized:
            self.status = self.taskRef.SetSampQuantSampPerChan(uInt64(value))
        self._samplesPerChannel = value

    samplesPerChannel = property(getSamplesPerChannel, setSamplesPerChannel)

    ## This function returns the number of channels configured in the DAQmx Task.
    #  @param self The object pointer.
    def getNumChannels(self):
        if self.initialized:
            numChannels = uInt32()
            self.status = self.taskRef.GetTaskNumChans(ctypes.byref(numChannels))
            self._numChannels = numChannels.value
        return self._numChannels 

    numChannels = property(getNumChannels)

    ## This function reads the data from the analogn input based on previous
    #  configuration.
    #  @param self The object reference.
    def read(self):
        timeout = float64(self.timeout)
        arraySize = uInt32(self._numChannels * self._samplesPerChannel)
        readArray = numpy.zeros((arraySize.value,), dtype = numpy.float64)
        samplesRead = int32()
        self.taskRef.ReadAnalogF64(self._samplesPerChannel, timeout,
                DAQmx_Val_GroupByChannel, readArray, arraySize,
                ctypes.byref(samplesRead), None) 
        return readArray
    
    ## This function will close connection to the analog output device and channels.
    #  @param self The object pointer.
    def close(self):
        self.initialized = False
        '''
        if self.startTriggerSyncCard != '':
            DAQmxDisconnectTerms(self._startTriggerSource, self.startTriggerSyncCard)
        '''    
        self.status = self.taskRef.ClearTask()
        self.taskRef = Task()

    ## This is the destructor for the AnalogInput Class.
    #  @param self The object pointer.
    def __del__(self):
        if self.initialized:
            self.close()

if __name__ == '__main__':
    try:
        ai = AnalogInput()
        ai.init('PXI1Slot9/ai0:3')
        print(ai.numChannels)
        print(ai.samplesPerChannel)
        print(ai.sampleRate)
        for i in range(10):
            print(ai.read())
    finally:
        ai.close()
