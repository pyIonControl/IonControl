# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from . import DAQmxUtility as dutil
import ctypes

## This class will generate digital outputs using pyDAQmx.
class DigitalOutput(object):
#-- Sample Rate Property
    ## This function returns the sample rate configured in the DAQmx Task.
    #  @param self The object reference.
    def getSampleRate(self):
        if self.initialized:
            sampleRate = float64()
            self.status = self.taskRef.GetSampClkRate(ctypes.byref(sampleRate))
            self._sampleRate = sampleRate.value
        return self._sampleRate

    ## This function sets the sample rate in the DAQmx Task.
    #  @param self The object reference.
    #  @param value The value to set the sample rate.
    def setSampleRate(self, value):
        if self.initialized:
            self.status = self.taskRef.SetSampClkRate(float64(value))
        self._sampleRate = value

    ## This function deletes the sample rate variable inside the
    #  DigitalOutput object.
    #  @param self The object reference.
    def _delSampleRate(self):
        del self._sampleRate

    sampleRate = property(getSampleRate, setSampleRate, _delSampleRate, doc=
                             """The sample rate of the digital output.""")

#-- Samples Per Channel Property

    ## This function returns the samples per channel configured in the
    #  DAQmx Task.
    #  @param self The object reference.
    def getSamplesPerChannel(self):
        if self.initialized:
            samplesPerChannel = uInt64()
            self.status = self.taskRef.GetSampQuantSampPerChan(
                    ctypes.byref(samplesPerChannel))
            self._samplesPerChannel = samplesPerChannel.value
        return self._samplesPerChannel

    ## This function sets the samples per channel in the DAQmx Task.
    #  @param self The object reference.
    #  @param value The value to set the samples per channel.
    def setSamplesPerChannel(self, value):
        if self.initialized:
            self.status = self.taskRef.SetSampQuantSampPerChan(uInt64(value))
        self._samplesPerChannel = value

    ## This function deletes the samplesPerChannel variable from the
    #  DigitalOutput object.
    #  @param self The object reference.
    def _delSamplesPerChannel(self):
        del self._samplesPerChannel

    samplesPerChannel = property(getSamplesPerChannel, setSamplesPerChannel,
            _delSamplesPerChannel,
            """The samples per channel of the digital output.""")

#-- Clock Source Property

    ## This function returns the sample clock source configured in the
    #  DAQmx Task.
    #  @param self The object reference.
    def getClkSource(self):
        if self.initialized:
            buffSize = uInt32(255)
            buff = ctypes.create_string_buffer(buffSize.value)
            self.status = self.taskRef.GetSampClkSrc(buff, buffSize)
            self._clkSource = buff.value
        return self._clkSource

    ## This function sets the sample clock source in the DAQmx Task.
    #  @param self The object reference.
    #  @param value The value to set the clock source.
    def setClkSource(self, value):
        if self.initialized:
            self.status = self.taskRef.SetSampClkSrc(value)
            value = self.getClkSource()
        self._clkSource = value

    ## This function deletes the clkSource variable within the
    #  DigitalOutput
    #  object.
    #  @param self The object reference.
    def _delClkSource(self):
        del self._clkSource

    clkSource = property(getClkSource, setClkSource, _delClkSource,
    """The clock source for the digital outputsample clock.""")

#-- Start Trigger Property
    ## This function returns the start trigger source configured in the
    #  DAQmx Task.
    #  @param self The object reference.
    def _getStartTriggerSource(self):
        if self.initialized:
            buffSize = uInt32(255)
            buff = ctypes.create_string_buffer(buffSize.value)
            self.status = self.taskRef.GetDigEdgeStartTrigSrc(buff, buffSize)
            self._startTriggerSource = buff.value
        return self._startTriggerSource 

    ## This function sets the start trigger source in the DAQmx Task.
    #  @param self The object reference.
    #  @param value The value to set the start trigger.
    def _setStartTriggerSource(self, value):
        if self.initialized:
            self.status = self.taskRef.SetDigEdgeStartTrigSrc(value)
            value = self.getStartTriggerSource()
        self._startTriggerSource = value

    startTriggerSource = property(_getStartTriggerSource,
            _setStartTriggerSource)

#-- Done Property
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

#-- Pause Trigger Source
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
    

#-------------------- Functions --------------------

    ## This function is a constructor for the DigitalOutput class.
    #
    #  It creates the internal variables required to perform functions
    #  within the class. This function does not initialize any hardware.
    #  @param self This object reference
    def __init__(self):
        ## The DAQmx task reference.
        self.taskRef = Task()

        ## This is the status of the DAQmx task.
        #
        #  A value greater than 0 means that an error has occurred. When
        #  the status is greater than 0 an error should be reported by
        #  the class.
        self.status = int32()

        ## This is a boolean that is true when the DAQmx task has been
        #  initialized.
        self.initialized = False

        ## @var sampleRate
        #  This is the sample rate of the digital output.
        self._sampleRate = 100e3

        ## @var samplesPerChannel
        #  This is the number of samples per channel that will be generated
        #  in Finite mode.
        self._samplesPerChannel = 100

        ## @var clkSource
        #  This is the sample clock source terminal.  It can be set to an
        #  internal clock or external clock such as a PFI line i.e.
        #  "/PXI1Slot3/PFI15."
        self._clkSource = ''

        ## @var startTriggerSource
        #  This is the start trigger source terminal.  It can be set to
        #  a PFI line such as "/PXISlot3/PFI0"
        self._startTriggerSource = ''

        ## @var pauseTriggerSource
        #  The source terminal of the pause trigger.  This can be
        #  any PFI or backplane trigger such as 'PFI5' and 'PXI_TRIG5'
        self._pauseTriggerSource = ''

        ## This is the mode of operation for the digital outputs.
        #
        #  There are currently three modes available.  Static mode is
        #  where one static digital sample is set with no need for a
        #  sample clock.  Finite mode is where a finite number of digital
        #  samples will be set at a sample clock rate. Continuous mode is
        #  where a sequence of voltages are generated at a sample rate and
        #  then repeated until the stop() method is called.
        self.mode = dutil.Mode.Finite

        self.triggerType = dutil.TriggerType.Software

        ## The number of time to iterate over a Finite number of samples.
        #
        #  This value is only useful in the "Finite" mode.  It is the
        #  number of times that a sequence of digital samples will be
        #  looped.  The default is allways 1.
        self.loops = 1

        ##  The time in seconds to wait for a trigger or for a digital
        #   state change.
        self.timeout = 1

        self.timeoutPad = 10

        self._pCh = ''
    
    ## Initialize the digital outputs based on the object's configuration.
    #  @param self The object reference.
    #  @param physicalChannel A string representing the device and digital
    #  output channels. Example value: "PXI1Slot3/ao0:7"
    def init(self, physicalChannel):
        self._pCh = physicalChannel
        self.__createTask(physicalChannel)
        self.initialized = True
        
        #Finite Mode
        if self.mode == dutil.Mode.Finite:
            self.status = self.taskRef.SetWriteRegenMode(
                    DAQmx_Val_AllowRegen)
            self.__configTiming(DAQmx_Val_FiniteSamps)
            
        #Continuous Mode
        if self.mode == dutil.Mode.Continuous:
            self.status = self.taskRef.SetWriteRegenMode(
                    DAQmx_Val_AllowRegen)
            self.__configTiming(DAQmx_Val_ContSamps)
            
        #Static Mode
        if self.mode == dutil.Mode.Static:
            pass
        
    ## This function returns a random 1D numpy array of samples for
    #  writing the buffer of digital output channels.
    #  @param self The objet reference.
    def createTestBuffer(self):
        import numpy
        data = numpy.random.rand(self._samplesPerChannel)
        data = numpy.ubyte(data * 255)
        return data
        
    ## This function returns the number of digital lines configured in
    #  the DAQmx Task.
    #  @param self The object reference.
    def getNumLines(self):
        numLines = uInt32()
        #bufferSize = 255
        #channel = ctypes.create_string_buffer(bufferSize)
        #self.taskRef.GetTaskChannels(channel, bufferSize)
        #print channel.value
        self.taskRef.GetDONumLines('', ctypes.byref(numLines))
        return numLines.value
    
    ## This function returns the number of digital channels configured in
    #  the DAQmx Task.
    #  @param self The object reference.
    def getNumChannels(self):
        numChannels = uInt32()
        self.taskRef.GetTaskNumChans(ctypes.byref(numChannels))
        return numChannels.value
        
    ## This function writes the specified values into the buffer.
    #  @param self The object reference.
    #  @param data This is a 1D 8-bit unsigned integer array that
    #  contians samples for each digital channel. Channels are
    #  non-interleaved (channel1 n-samples then channel2 n-samples).
    def writeToBuffer(self, data):
        autostart = self.mode == dutil.Mode.Static
        samplesWritten = int32()
        self.buff = data
        self.status = self.taskRef.WriteDigitalU8(self._samplesPerChannel,
                autostart, 10, DAQmx_Val_GroupByChannel, data,
                ctypes.byref(samplesWritten), None)
        #print 'Samples Written: ' + str(samplesWritten.value)
        return samplesWritten.value
    
    ## This function writes a static value to the digital line(s)
    #  configured in the init() method.
    #  @param self The object reference.
    #  @param data The static value to send to the digital line(s). 
    def writeStatic(self, data):
        if isinstance(data, bool) and data == True:
            digLineNum = int(self._pCh[len(self._pCh)-1])
            data = 2**digLineNum
        autostart = True
        self.status = self.taskRef.WriteDigitalScalarU32(autostart,
                float64(self.timeout), uInt32(data), None)

    ## This function starts the digital output generation.
    #  @param self The object reference.
    def start(self):
        self.status = self.taskRef.StartTask()
        
    ## This functions waits for the digital output generation to complete.
    #  @param self The object reference.
    def waitUntilDone(self):
        sampPerChan = uInt64()
        self.status = self.taskRef.GetSampQuantSampPerChan(
                ctypes.byref(sampPerChan))
        #print 'DO Samples Per Channel: ' + str(sampPerChan.value)
        estAcqTime = (self.loops * sampPerChan.value) / self._sampleRate
        
        #print "Estimated Acquisition Time: " + str(estAcqTime)
        
        if self.mode != dutil.Mode.Static:
            self.status = self.taskRef.WaitUntilTaskDone(
                    float64(estAcqTime + self.timeoutPad))
    
    ## This function stops the digital output generation.
    #  @param self The object reference.
    def stop(self):
        self.status = self.taskRef.StopTask()
    
    ## This is a private method that creates the Task object for use
    #  inside the DigitalOutput class.
    def __createTask(self, physicalChannel):
        self.status = self.taskRef.CreateDOChan(physicalChannel, '',
                DAQmx_Val_ChanForAllLines)
        
    ## This is a private method that configures the timing for the
    #  DigitalOutput class.
    #  @param self The object reference.
    def __configTiming(self, sampleMode):
        totalSamples = self._samplesPerChannel * self.loops
        if self.triggerType == dutil.TriggerType.Software:
            self.status = self.taskRef.CfgSampClkTiming(self._clkSource,
                    float64(self._sampleRate), DAQmx_Val_Falling, sampleMode,
                    uInt64(totalSamples))
        elif self.triggerType == dutil.TriggerType.Hardware:
            self.status = self.taskRef.CfgSampClkTiming(self._clkSource, 
                    float64(self._sampleRate), DAQmx_Val_Falling, sampleMode,
                    uInt64(totalSamples))
            self.status = self.taskRef.CfgDigEdgeStartTrig(self._startTriggerSource, DAQmx_Val_Falling)


    ## This function will close connection to the digital ouput device and
    #  channels.
    #  @param self The object reference.
    def close(self):
        self.initialized = False
        self.status = self.taskRef.ClearTask()
        self.taskRef = Task()
        
    ## This is the destructor for the DigitalOutput Class.
    #  @param self The object reference.
    def __del__(self):
        if self.initialized:
            self.close()
        
        del self.taskRef
        del self.status
        del self.initialized
        del self.sampleRate
        del self.samplesPerChannel
        del self.clkSource
        del self.mode
        del self.loops
        del self.timeout
        del self.timeoutPad
        del self._pCh
