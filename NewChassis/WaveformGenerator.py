# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .AnalogOutput import AnalogOutput
from .DigitalOutput import DigitalOutput
from . import DAQmxUtility as dutil
import re
import threading

'''
class writeStartStop(threading.Thread):
    def __init__(self, wfrmGenObject, aoBuffer, doBuffer = None):
        self.wfrmGen = wfrmGenObject
        self.aoBuffer = aoBuffer
        self.doBuffer = doBuffer

    def run(self):
        pass
'''
        

## This class contains an AnalogOutput and DigitalOutput object.  It is intended
#  to represent a single PXI-6733 in software.
class WaveformGenerator(object):
    ## This function is a constructor for the WaveformGenerator class.  
    #
    #  It creates the internal variables required to perform functions within the
    #  class. This function does not initialize any hardware.
    def __init__(self):
        ## This is an AnalogOutput object created using the AnalogOutput class.
        self.ao = AnalogOutput()

        ## This is a DigitalOutput object created using the DigitaOutput class.
        self.do = DigitalOutput()

        self._sampleRate = 100e3

        ## This is the number of channels configured in the waveform generator.
        self.samplesPerChannel = 100

        ## This is the sample clock source terminal.  It can be set to an
        #  internal clock or external clock such as a PFI line i.e. "/PXI1Slot3/PFI15."
        self.clkSource = ''

        ## This is the start trigger source terminal.  The software
        #  ignores this value when the triggerType is set to "Software". Otherwise when
        #  the triggerType is "Hardware," this terminal is used to start analog
        #  generation.  Example Value: "/PXI1Slot3/PFI0"
        self.startTriggerSource = ''

        ## There are currently three modes available.  Static mode is where one
        #  static voltage is set with no need for a sample clock.  Finite mode is
        #  where a finite number of voltages will be set at a sample clock rate.
        #  Continuous mode is where a sequence of voltages are generated at a sample
        #  rate and then repeated until the stop() method is called.
        self.mode = dutil.Mode.Finite

        ## This value is only useful in the "Finite" mode.  It is the number of
        #  times that a sequence of voltages will be looped.  The default is allways 1.
        self.loops = 1

        ## There are currently two trigger types - "Software" and
        #  "Hardware."  The "Software" mode means that analog output channels are not
        #  syncronized. While "Hardware" means that analog output channels are
        #  syncronized to a start trigger.  The startTriggerSouce attribute must be
        #  configured appropriately.
        self.triggerType = dutil.TriggerType.Hardware
        
        ## This is a boolean value that will be true if the WaveformGenerator
        #  is configured to utilize analog outputs.
        self.useAo = False

        ## This is a boolean value that will be true if the WaveformGenerator
        #  is configured to utilize digital outputs.
        self.useDo = True
            
    def _getSampleRate(self):
        self._sampleRate = self.ao.sampleRate
        return self._sampleRate

    def _setSampleRate(self, sampleRate):
        self._sampleRate = sampleRate
        self.ao.sampleRate = sampleRate
        if self.useDo:
            self.do.sampleRate = sampleRate

    ## This is the sample rate of the waveform generator.
    sampleRate = property(_getSampleRate, _setSampleRate)

    def _getSamplesPerChannel(self):
        return self.ao.samplesPerChannel

    def _setSamplesPerChannel(self, samplesPerChannel):
        self.ao.samplesPerChannel = samplesPerChannel
        self.do.samplesPerChannel = samplesPerChannel

    samplesPerChannel = property(_getSamplesPerChannel, _setSamplesPerChannel)

    def _getClkSource(self):
        return self.ao.clkSource

    def _setClkSource(self, clkSource):
        self.ao.clkSource = clkSource
        if self.do.clkSource == '':
            #device = re.search('[^/]*', aoChannels).group(0)
            self.do.clkSource = 'ao/SampleClock'
            #self.do.clkSource = '/{0}/ao/SampleClock'.format(device)
    
    clkSource = property(_getClkSource, _setClkSource)

    def _getStartTriggerSource(self):
        return self.ao.startTriggerSource

    def _setStartTriggerSource(self, startTriggerSource):
        self.ao.startTriggerSource = startTriggerSource
        self.do.startTriggerSource = startTriggerSource

    startTriggerSource = property(_getStartTriggerSource,
            _setStartTriggerSource)

    def _getPauseTriggerSource(self):
        return self.ao.pauseTriggerSource

    def _setPauseTriggerSource(self, pauseTriggerSource):
        self.ao.pauseTriggerSource = pauseTriggerSource
        self.do.pauseTriggerSource = pauseTriggerSource

    pauseTriggerSource = property(_getPauseTriggerSource, _setPauseTriggerSource)

    def _getLoops(self):
        return self.ao.loops

    def _setLoops(self, loops):
        self.ao.loops = loops
        self.do.loops = loops

    loops = property(_getLoops, _setLoops)

    def _getMode(self):
        return self.ao.mode

    def _setMode(self, mode):
        self.ao.mode = mode
        self.do.mode = mode

    mode = property(_getMode, _setMode)

    def _getTriggerType(self):
        return self.ao.triggerType

    def _setTriggerType(self, triggerType):
        self.ao.triggerType = triggerType
    
    triggerType = property(_getTriggerType, _setTriggerType)

    def _getAoBuffer(self):
        return self.ao.buff

    aoBuff = property(_getAoBuffer)

    def _getDone(self):
        return self.ao.done

    ## @var done
    #  Returns the done status.
    #
    #  This mode works differently depending on the mode. <br />
    #  <ul>
    #  <li><B>Static and Continuous</B>: done is false after a start
    #  method and true</li>
    #  only after a stop method.
    #  <li><B>Finite</B>: done is false until all samples are
    #  generated.</li></ul>
    done = property(_getDone)

    ## Initialize the analog and digital outputs based on the object's
    #  configuration.
    #  @param self The object pointer.
    #  @param aoChannels This is a string representing the device and analog output
    #  channels. Example value: "PXI1Slot3/ao0:7"
    #  @param doChannels This is a string representing the device and digital output
    #  channels. Example value: "PXI1Slot3/port0/line0:7"
    def init(self, aoChannels, doChannels=''):
        self.useAo = aoChannels != ''
        self.useDo = doChannels != ''
        
        #Initialize Analog and Digital Outputs
        if self.useAo:
            self.ao.init(aoChannels)
        if self.useDo:
            self.do.init(doChannels)
            
    ## This function writes the specified values into the buffer.
    #  @param self The object pointer.
    #  @param data This is a 1D 64-bit float numpy array that contians data for each
    #  analog output.  Channels are non-interleaved (channel1 n-samples then
    #  channel2 n-samples).
    def writeAoBuffer(self, data):
        samplesWritten = self.ao.writeToBuffer(data)
        return samplesWritten
    
    ## This function writes the specified values into the buffer.
    #  @param self The object pointer.
    #  @param data This is a 1D 8-bit unsigned integer array that contians data for
    #  each digital line. Lines are non-interleaved (line1 n-samples then line2
    #  n-samples).
    def writeDoBuffer(self, data):
        samplesWritten = self.do.writeToBuffer(data)
        return samplesWritten
    
    ## This function starts the analog and digital output generation.
    #  @param self The object pointer.
    def start(self):
        # The do object must be started before the ao object because it is a slave
        # to the ao object and must rely on the analog output sample clock to
        # generate digital outputs.
        # Otherwise, not all of the digital output samples will be generated.
        if self.useDo:
            self.do.start()

        if self.useAo:
            self.ao.start()
    
    ## This functions waits for the analog and digital output generation to
    #  complete.
    def waitUntilDone(self):
        if self.useAo:
            self.ao.waitUntilDone()
        if self.useDo:
            self.do.waitUntilDone()
    
    ## This function stops the analog and digital output generation.
    #  @param self The object pointer.
    def stop(self):
        if self.useAo:
            self.ao.stop()
        if self.useDo:
            self.do.stop()

    def writeStartStop(self, aoData, doData = None):
        self.writeAoBuffer(aoData)
        if doData:
            self.writeDoBuffer(doData)
        self.start()
        self.waitUntilDone()
        self.stop()
    
    ## This function will close connection to the analog and digital ouput
    #  device and channels.
    def close(self):
        if self.useAo:
            self.ao.close()
        if self.useDo:
            self.do.close()
