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

## This class will generate analog outputs using pyDAQmx.
class AnalogOutput(object):
   
    ## This function is a constructor for the AnalogOutput class.
    #
    # It creates the internal variables required to perform functions within the
    # class. This function does not initialize any hardware.
    def __init__(self):

        ## The DAQmx task reference.
        self.taskRef = Task()

        ## This is a boolean that is true when the DAQmx task has been initialized.
        self.initialized = False

        ## This is the status of the DAQmx task.
        #
        #  A value greater than 0 means that an error has occurred. When the status
        #  is greater than 0 an error should be reported by the class.
        self.status = int32()

        ## @var sampleRate
        #  This is the sample rate of the analog output.
        self._sampleRate = 100e3
        
        ## @var numChannels
        #  This is the number of channels configured in the task.
        self._numChannels = 0

        ## @var samplesPerChannel
        #  This is the number of samples per channel that will be
        #  generated in Finite mode.
        self._samplesPerChannel = 100

        ## @var clkSource
        #  This is the sample clock source terminal.  It can be set to an
        #  internal clock or external clock such as a PFI line i.e. "/PXI1Slot3/PFI15."
        self._clkSource = ''

        ## @var startTriggerSource
        #  This is the start trigger source terminal.  The software
        #  ignores this value when the triggerType is set to "Software". Otherwise when
        #  the triggerType is "Hardware," this terminal is used to start analog
        #  generation.  Example Value: "/PXI1Slot3/PFI0"
        self._startTriggerSource = ''

        ## @var pauseTriggerSource
        #  The source terminal of the pause trigger.  This can be
        #  any PFI or backplane trigger such as 'PFI5' and 'PXI_TRIG5'
        self._pauseTriggerSource = ''
        
        ## This is the start trigger terminal of the NI-Sync card.
        #  
        #  Setting this value will make sure that the start trigger will be
        #  propogated through the PXI backplane. If there is no sync card needed
        #  leave the value default.
        self.startTriggerSyncCard = ''

        ## This is the mode of operation for the analog outputs.
        #
        #  There are currently three modes available.  Static mode is where one
        #  static voltage is set with no need for a sample clock.  Finite mode is
        #  where a finite number of voltages will be set at a sample clock rate.
        #  Continuous mode is where a sequence of voltages are generated at a sample
        #  rate and then repeated until the stop() method is called.
        self.mode = dutil.Mode.Finite

        ## The trigger type for the analog outputs.
        #
        #  There are currently two trigger types - "Software" and
        #  "Hardware."  The "Software" mode means that analog output channels are not
        #  syncronized. While "Hardware" means that analog output channels are
        #  syncronized to a start trigger.  The startTriggerSouce attribute must be
        #  configured appropriately.
        self.triggerType = dutil.TriggerType.Software

        ## The number of times to iterate over a Finite number of samples.
        #
        #  This value is only useful in the "Finite" mode.  It is the number of
        #  times that a sequence of voltages will be looped.  The default is allways 1.
        self.loops = 1

        ## The estimated time to generate the samples for a Finite generation.
        #
        #  Once the input buffer of the analog input is configured, the
        #  amount of time it takes to generate the voltages in the buffer can be
        #  estimated.  This is a function of the sample rate and the number of samples
        #  per channel. (This attribute is for internal use only.  This attribute may
        #  not return an accurate value.)
        self.estAcqTime = 0

        ## The analog output buffer.
        #
        #  This is the data that is stored in the buffer of the Analog Output card.
        self.buff = None

        self._timeoutPad = 0.01
    
    def _getDone(self):
        done = bool32()
        if self.initialized:
            self.status = self.taskRef.GetTaskComplete(
                    ctypes.byref(done))
        else:
            done.value = 1 
        return bool(done.value)

    ## @var done
    #  Returns the task done status.
    #
    #  This mode works differently depending on the mode. <br />
    #  <ul>
    #  <li><B>Static and Continuous</B>: done is false after a start
    #  method and true</li>
    #  only after a stop method.
    #  <li><B>Finite</B>: done is false until all samples are
    #  generated.</li></ul>
    done = property(_getDone)

    def _getPauseTriggerSource(self):
        if self.initialized:
            buffSize = uInt32(255)
            buff = ctypes.create_string_buffer(buffSize.value)
            self.status = self.taskRef.GetDigLvlPauseTrigSrc(buff, buffSize)
            self._pauseTriggerSource = buff.value
        return self._pauseTriggerSource

    def _setPauseTriggerSource(self, value):
        if self.initialized:
            if value == '':
                self.status = self.taskRef.SetPauseTrigType(
                        DAQmx_Val_None)
                self.status = self.taskRef.ResetDigLvlPauseTrigSrc()
            else:
                self.status = self.taskRef.SetDigLvlPauseTrigWhen(
                        DAQmx_Val_High)
                self.status = self.taskRef.SetPauseTrigType(
                        DAQmx_Val_DigLvl)
                self.status = self.taskRef.SetDigLvlPauseTrigSrc(value)
        self._pauseTriggerSource = value

    pauseTriggerSource = property(_getPauseTriggerSource,
            _setPauseTriggerSource)

    ## Initializes the analog outputs based on the object's configuration.
    #  @param self The object pointer.
    #  @param physicalChannel A string representing the device and analog
    #  output channels. Example Value: "PXI1Slot3/ao0:7"
    def init(self, physicalChannel):
        self.__createTask(physicalChannel)
        self.initialized = True

        #Finite Mode
        if self.mode == dutil.Mode.Finite:
            self.status = self.taskRef.SetWriteRegenMode(DAQmx_Val_AllowRegen)
            self.__configTiming(DAQmx_Val_FiniteSamps)
            
        #Continuous Mode   
        elif self.mode == dutil.Mode.Continuous:
            self.status = self.taskRef.SetWriteRegenMode(DAQmx_Val_AllowRegen)
            self.__configTiming(DAQmx_Val_ContSamps)
        
        #Static Mode
        elif self.mode == dutil.Mode.Static:
            self.setSampleRate(self._sampleRate)
            self.setSamplesPerChannel(1)

        self.pauseTriggerSource = self._pauseTriggerSource
        #print self.samplesPerChannel
        #print self._sampleRate
        #print self.clkSource
        #print self.startTriggerSource
    
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

    ## This funciton deletes the samplesPerChannel variable inside the AnalogOutput
    #  object.
    #
    #  It is an internal function that is called in the class destructor. It should
    #  not be called. 
    def _delSamplesPerChannel(self):
        """
        This funciton deletes the samplesPerChannel variable inside the AnalogOutput
        object.  It is an internal function that is called in the class destructor.
        It should not be called.
        """
        del self._samplesPerChannel

    samplesPerChannel = property(getSamplesPerChannel, setSamplesPerChannel,
            _delSamplesPerChannel)

    ## This function returns the sample clock source configured in the DAQmx Task.
    #  @param self The object pointer.
    def getClkSource(self):
        if self.initialized:
            buffSize = uInt32(255)
            buff = ctypes.create_string_buffer(buffSize.value)
            self.status = self.taskRef.GetSampClkSrc(buff, buffSize)
            self._clkSource = buff.value
        return self._clkSource 

    ## This function sets the sample clock source in the DAQmx Task.
    #  @param self The object pointer.
    #  @param value The string value for the clock source terminal.
    def setClkSource(self, value):
        if self.initialized:
            self.status = self.taskRef.SetSampClkSrc(value)
            value = self.getClkSource()
        self._clkSource = value

    ## This function deletes the clkSource variable within the AnalogOutput object.
    #
    #   It is an internal function that is called in the class destructor.  It should
    #   not be called.
    def _delClkSource(self):
        del self._clkSource

    clkSource = property(getClkSource, setClkSource, _delClkSource)

    ## This function return the start trigger source configured in the DAQmx Task.
    #  @param self The object pointer.
    def getStartTriggerSource(self):
        if self.initialized:
            buffSize = uInt32(255)
            buff = ctypes.create_string_buffer(buffSize.value)
            self.status = self.taskRef.GetDigEdgeStartTrigSrc(buff, buffSize)
            self._startTriggerSource = buff.value
        return self._startTriggerSource 

    ## This function sets the start trigger source in the DAQmx Task.
    #  @param self The object pointer.
    #  @param value The string vaue of the start trigger source.
    #  Example value: "\PXI1Slot3\PFI0"
    def setStartTriggerSource(self, value):
        if self.initialized:
            self.status = self.taskRef.SetDigEdgeStartTrigSrc(value)
            value = self.getStartTriggerSource()
        self._startTriggerSource = value

    ## This function deletes the startTriggerSource variable within the AnalogOutput object.
    #
    #   It is an internal function that is called in the class destructor.  It should
    #   not be called.
    def _delStartTriggerSource(self):
        del self._startTriggerSource

    startTriggerSource = property(getStartTriggerSource, setStartTriggerSource, _delStartTriggerSource)
    
    ## This function returns the number of channels configured in the DAQmx Task.
    #  @param self The object pointer.
    def getNumChannels(self):
        if self.initialized:
            numChannels = uInt32()
            self.status = self.taskRef.GetTaskNumChans(ctypes.byref(numChannels))
            self._numChannels = numChannels.value
        return self._numChannels 

    numChannels = property(getNumChannels)
    
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
        
    ## This function deletes the sample rate variable inside the AnalogOutput object.
    #  @param self The object pointer.
    def _delSampleRate(self):
        del self._sampleRate
    
    sampleRate = property(getSampleRate, setSampleRate, _delSampleRate)
    
    ## This function returns a 1D numpy array of samples with random voltages.
    #  The returned value is intended to be used to write samples to the buffer with
    #  the writeToBuffer() method.
    #  @param self The object pointer.
    #  @param numChannels The number of channels to generate. If this parameter is
    #  not provided, Then the function will generate the number of channels configured
    #  in the analog output task.
    def createTestBuffer(self, numChannels=0):
        numChannels = numChannels if numChannels > 0 else self.getNumChannels()
        return numpy.float64(numpy.random.rand(self._samplesPerChannel * numChannels))
    
    ## This function returns a 1D numpy array of sine waves.  The returned
    #  value is intended to be used to write samples to the buffer with the
    #  writeToBuffer() method.
    #  @param self The object pointer.
    def createSineTestBuffer(self):
        from .createSineWave import createSineWave
        
        numChannels = self.getNumChannels()
        for i in range(numChannels):
            data = createSineWave(10, 100e3, self._sampleRate,
                    self._samplesPerChannel, ((2*numpy.pi)/numChannels) * i)
            if i == 0:
                sineData = data['amplitude']
            else:
                sineData = numpy.append(sineData, data['amplitude'])
            
        return sineData
        
    ## This function writes the specified values into the buffer.
    #  @param self The object pointer. 
    #  @param data This is a 1D 64-bit floating point numpy array that contians data
    #  for each channel.  Channels are non-interleaved (channel1 n-samples then 
    #  channel2 n-samples).
    def writeToBuffer(self, data):
        autostart = self.mode == dutil.Mode.Static
        self.buff = data
        
        samplesWritten = int32()
        self.status = self.taskRef.WriteAnalogF64(self._samplesPerChannel, autostart,
                10, DAQmx_Val_GroupByChannel, data, ctypes.byref(samplesWritten),
                None)
        return samplesWritten.value
    
    ## This function starts the analog output generation.
    #  @param self The object pointer.
    def start(self):
        self.status = self.taskRef.StartTask()
    
    ## This functions waits for the analog output generation to complete.
    #  @param self The object pointer.
    def waitUntilDone(self):
        sampPerChan = uInt64()
        self.status = self.taskRef.GetSampQuantSampPerChan(ctypes.byref(sampPerChan))
        self.estAcqTime = (self.loops * sampPerChan.value) / self._sampleRate
        #print 'SamplesPerChannel: ' + str(sampPerChan.value)
        #print 'Estimated Acquisition Time: ' + str(self.estAcqTime)
        #if (self.estAcqTime >= 0.01 and self.mode != dutil.Mode.Static):
        if self.mode != dutil.Mode.Static:
            self.status = self.taskRef.WaitUntilTaskDone(float64(self.estAcqTime + self._timeoutPad))
    
    ## This function stops the analog output generation.
    #  @param self The object pointer.
    def stop(self):
        self.status = self.taskRef.StopTask()
    
    def __createTask(self, physicalChannel):
        """
        This is a private method that creates the Task object for use inside the
        AnalogOutput class."""
        self.status = self.taskRef.CreateAOVoltageChan(physicalChannel, "", -10, 10,
                                                       DAQmx_Val_Volts, None)
    
    def __configTiming(self, sampleMode):
        """
        This is a private method that configures the timing for the Analog Output
        class.
        """
        totalSamples = self._samplesPerChannel * self.loops
        onDemand = bool32()
        self.status = self.taskRef.GetOnDemandSimultaneousAOEnable(
                ctypes.byref(onDemand))
        #print 'On Demand: ' + str(onDemand.value)
        #print 'Trigger Type: ' + str(self.triggerType)
        #print 'Software Trigger Type: ' + str(dutil.TriggerType.Software)
        if self.triggerType == dutil.TriggerType.Software:
            #print 'Software Timing'
            self.status = self.taskRef.CfgSampClkTiming('OnboardClock',
                    float64(self._sampleRate), DAQmx_Val_Rising, sampleMode,
                    uInt64(totalSamples))
                
        elif self.triggerType == dutil.TriggerType.Hardware:
            #print 'Hardware Timing'
            self.status = self.taskRef.CfgSampClkTiming(self._clkSource,
                    float64(self._sampleRate), DAQmx_Val_Falling, sampleMode,
                    uInt64(totalSamples))
            self.status = self.taskRef.CfgDigEdgeStartTrig(self._startTriggerSource,
                    DAQmx_Val_Rising)
            if self.startTriggerSyncCard != '':
                DAQmxConnectTerms(self.startTriggerSyncCard,
                        self._startTriggerSource, DAQmx_Val_DoNotInvertPolarity)
        
    ## This function will close connection to the analog output device and channels.
    #  @param self The object pointer.
    def close(self):
        self.initialized = False
        if self.startTriggerSyncCard != '':
            DAQmxDisconnectTerms(self._startTriggerSource, self.startTriggerSyncCard)
            
        self.status = self.taskRef.ClearTask()
        self.taskRef = Task()
        

    ## This is the destructor for the AnalogOutput Class.
    #  @param self The object pointer.
    def __del__(self):
        if self.initialized:
            self.close()
       
        del self.taskRef
        del self.initialized
        del self.status
        del self.sampleRate
        del self._numChannels
        del self.samplesPerChannel
        del self.clkSource
        del self.startTriggerSource
        del self.startTriggerSyncCard
        del self.mode
        del self.triggerType
        del self.loops
        del self.estAcqTime
