# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools
from re import search

from numpy import append
import numpy
import logging
from modules.stringutilit import ensureAsciiBytes

from . import DAQmxUtility as dutil
from PyDAQmx import DAQError
from .Timing import Timing
from .WaveformGenerator import WaveformGenerator
from .chassisConfigParser import chassisConfigParser


#from time import sleep
## This class contains a list of WaveformGenerator objects and a Timing object.
#  It is intended to represent a chasis with a NiSync Card and a number
#  of PXI-6733s.
class WaveformChassis(object):
    ## This function is a constructor for the WaveformChassis class. It
    #  creates the internal variables required to perform functions within the
    #  class. This function does not initialize any hardware.
    def __init__(self):
        ## This is a Timing object created using the Timing class.
        #
        #  It is used to synchronize all of the PXI cards.
        self.timing = Timing()

        ## This is a boolean value that will be true if the WaveformChassis
        #  is configured to use Timing.
        self.useTiming = True

        ## This is a list of WaveformGenerator objects created using the
        #  WaveformGenerator class.
        #
        #  It is a list of PXI6733 cards configured for the WaveformChassis.
        self.gens = type([])

        ## This is the sample rate of all the Analog and Digital outputs.
        #  The sample rate must be the same for all devices configured in the
        #  WaveformChassis.
        self.sampleRate = 100e3

        ## This is the number of channels configured for the WaveformChassis.
        #
        #  The samples per channel must be the same for all devices
        #  configured in the WaveformChassis.
        self.samplesPerChannel = 100

        ## This is the mode of operation for all generators.
        #  
        #  There are currently three modes available.  Static mode is where one
        #  static voltage is set with no need for a sample clock.  Finite mode is
        #  where a finite number of voltages will be set at a sample clock rate.
        #  Continuous mode is where a sequence of voltages are generated at a sample
        #  rate and then repeated until the stop() method is called.
        self.mode = dutil.Mode.Finite

        ## The number of times to iterate over a Finite number of samples.
        #  
        #  This value is only useful in the "Finite" mode.  It is the number of
        #  times that a sequence of voltages will be looped.  The default is allways 1.
        self.loops = 1

        ##  The trigger type for the analog outputs.
        #
        #   There are currently two trigger types - "Software" and
        #  "Hardware."  The "Software" mode means that analog output channels are not
        #  syncronized. While "Hardware" means that analog output channels are
        #  syncronized to a start trigger.  The startTriggerSouce attribute must be
        #  configured appropriately.
        self.triggerType = dutil.TriggerType.Hardware

        ## This is the sample clock source terminal for every
        #  WaveformGenerator configured in the WaveformChassis.  It is defaulted to
        #  "PXI_Star."
        self.clkSource = 'PXI_Star'

        ## This is the start trigger source terminal for every
        #  WaveformGenerator configured in the WaveformChassis.  It is defaulted to
        #  "PXI_Trig1"
        self.startTriggerSource = 'PXI_Trig1'
        

    ## Initializes the waveform chassis based on the object's configuration.
    #  @param self The object pointer.
    #  @param aoDevsAndChnls This is a list of strings representing the devices
    #  and analog output channels.
    #  @param doDevsAndChnls This is a list of strings representing the divices
    #  and digital output channels.
    #  @param syncDevice This is the device name for the NI Sync card.
    def init(self, aoDevsAndChnls, doDevsAndChnls=None, syncDevice=None):
        numAoDevs = len(aoDevsAndChnls)
        numDoDevs = len(doDevsAndChnls) if doDevsAndChnls is not None else 0
        numDevs = numAoDevs if aoDevsAndChnls > doDevsAndChnls else numDoDevs
        
        self.gens = [WaveformGenerator() for i in range(numDevs)]
        
        
        if syncDevice is not None:
            self.timing.sampleRate = self.sampleRate
            if syncDevice:
                self.timing.init(ensureAsciiBytes(syncDevice))
        else:
            self.useTiming = False
        
        for i, generator in enumerate(self.gens):
            generator.mode = self.mode
            generator.sampleRate = self.sampleRate
            if self.mode == dutil.Mode.Static:
                generator.samplesPerChannel = 1
            else:
                generator.samplesPerChannel = self.samplesPerChannel
            generator.loops = self.loops
            generator.triggerType = self.triggerType
            device = search(b'[^/]*', aoDevsAndChnls[i]).group(0)
            #print 'Device: ' + str(device)
            generator.clkSource = ensureAsciiBytes('/{0}/{1}'.format(device.decode('ascii'), self.clkSource))
            #print 'Clock Source:' + generator.clkSource
            generator.startTriggerSource = ensureAsciiBytes('/{0}/{1}'.format(device.decode('ascii'),
                    self.startTriggerSource))
            #print 'Start Trigger: ' + generator.startTriggerSource
            generator.ao.startTriggerSyncCard = ensureAsciiBytes('/{0}/{1}'.format(syncDevice.decode('ascii'),
                    self.startTriggerSource))
            #print 'Sync Card Start Trigger: ' + generator.ao.startTriggerSyncCard
            if doDevsAndChnls is None:
                generator.init(aoDevsAndChnls[i])
            else:
                generator.init(aoDevsAndChnls[i], doDevsAndChnls[i])

    ## This function will initialize the waveform chassis based on the
    #  configuration file specified by the filePath parameter.
    #  @param self The object pointer
    #  @param filePath The file path to the configuration file.
    def initFromFile(self, filePath):
        config = chassisConfigParser()
        ao, do, sync = config.read(filePath)
        self.init(ao, do, sync)

    ## This function returns the total number of AO channels configured.
    #  @param self The object pointer.
    def getNumAoChannels(self):
        totalNumChnls = 0
        for generator in self.gens:
            totalNumChnls = generator.ao.getNumChannels() + totalNumChnls
        return totalNumChnls
        
    ## This function returns the total number of AO channels configured.
    #  @param self The object pointer.
    def getNumDoChannels(self):
        totalNumChnls = 0
        for generator in self.gens:
            totalNumChnls = generator.do.getNumChannels() + totalNumChnls
        return totalNumChnls
        
    ## This function returns a 1D numpy array of sine waves - one for each
    #  channel configured by the init function.
    #  @param self The object pointer.
    def createAoSineBuffer(self):
        for i, generator in enumerate(self.gens):
            data = generator.ao.createSineTestBuffer()
            if i<= 0:
                testData = data
            else:
                testData = append(testData, data)
            #print data
            #print len(data)
            #raw_input('Press entor to continue...')
        return testData
        
    #def plotAoBuffer(self, data):
        #pass
    
    ## This function returns a 1d array of random U8s for writing to the
    #  buffer of digital output channels.
    #  @param self The object pointer.
    def createDoTestBuffer(self):
        for i, generator in enumerate(self.gens):
            data = generator.do.createTestBuffer()
            if i<=0:
                testData = data
            else:
                testData = append(testData, data)
            i+=1
        return testData
        
    def createFalseDoBuffer(self):
        testData =  numpy.array( [0]*len(self.gens), dtype=numpy.uint8)
        print("createFalseDoBuffer", testData)
        return testData
        
        
    ## This function will write data into the buffer of the analog outputs that
    #  are a part of the WaveformChassis class.
    #  @param self The object pointer
    #  @param data This is a 1D 8-bit unsigned integer array that contians data
    #  for each digital channel. Channels are non-interleaved (channel1 n-samples
    #  then channel2 n-samples).
    def writeAoBuffer(self, data):
        # first get the total number of channels from the generators
        totalNumChnls = self.getNumAoChannels()

        #calculate the samples per channel from the length of data and the total
        #number of channels
        #print 'total number of channels: ' + str(totalNumChnls)
        sampsPerChannel = len(data)//totalNumChnls
        if sampsPerChannel == 0:
            logging.getLogger(__name__).error("samples per channel: 0, no voltages will be written")
        else:
            logging.getLogger(__name__).debug('samples per channel: {0}'.format(sampsPerChannel))
        
        #take a subset of data and input into the buffer for each generator
        for i, generator in enumerate(self.gens):
            numChannels = generator.ao.getNumChannels()
            #print "Number of Channels: " + str(numChannels)
            startIndex = i*numChannels * sampsPerChannel
            stopIndex = startIndex + sampsPerChannel * numChannels
            #print 'start index: ' + str(startIndex)
            #print 'stop index: '  + str(stopIndex)
            dataSubset = data[startIndex:stopIndex]
            #print 'Data Subset: ' + str(dataSubset)
            generator.writeAoBuffer(dataSubset)
    
    ## This function will write data into the buffer of the digital outputs
    #  that are a part of the WaveformChassis.
    #  @param self The object pointer.
    #  @param data This is a 1D 8-bit unsigned integer array that contians data for
    #  each digital channel. Channels are non-interleaved (channel1 n-samples then
    #  channel2 n-samples).
    def writeDoBuffer(self, data):
        #first get the total number of channels from the generators
        totalNumChnls = self.getNumDoChannels()

        #calculate the samples per channel from the length of data and the total
        #number of channels
        #print "Number of Channels: " + str(totalNumChnls)
        sampsPerChannel = len(data)/totalNumChnls
        #print 'samples per channel: ' +str(sampsPerChannel)
        
        #taks a subset of data and input into the buffer for each generator
        for i, generator in enumerate(self.gens):
            numChannels = generator.do.getNumChannels()
            generator.writeDoBuffer(data[i*numChannels:i*numChannels +
                sampsPerChannel])
        
    
    ## This function starts the analog and digital output generation.
    #  @param self The object pointer.
    def start(self):
        for generator in self.gens:
            generator.start()
            
        if self.useTiming == True:
            self.timing.sendSoftwareTrigger()
    
    ## This functions waits for the analog and digital output generation to
    #  complete.
    #  @param self The object pointer.
    def waitUntilDone(self):
        for i, generator in enumerate(self.gens):
            #print 'wait generator: {0}'.format(i)
            generator.waitUntilDone()
        '''
        estAcqTime = self.gens[0].ao.estAcqTime
        if estAcqTime < 0.01:
            print 'Sleeping {0}s...'.format(estAcqTime+1)
            sleep(estAcqTime+1)
        '''
    ## This function is used to set a callback function that will get called when the analog 
    # output generation is complete
    # the callbackFunction takes two arguments: the generator id and the completion status
    def setOnDoneCallback(self, callbackFunction):
        for i, generator in enumerate(self.gens):
            generator.setOnDoneCallback( functools.partial(callbackFunction, i) )
    
    ## This function stops the analog and digital output generation.
    #  @param self The object pointer.
    def stop(self):
        for i, generator in enumerate(self.gens):
            #print 'stop generator: ' + str(i)
            try:
                generator.stop()

            except DAQError as e:
                #catch error number 200010 and ignore
                #error number 200010 is actually just a warning
                if e.error == 200010:
                    #This will ignore error 200010
                    pass
                else:
                    #This will pass the error through
                    raise
            
    
    ## This function will perform the write, start, waitUntilDone, and stop
    #  functions wrapped in one funciton.
    #  This funciton is no complete and may not exist in a later release!!!
    #  @param self The object pointer.
    def writeStartStop(self, aoData, doData = None):
        for i, generator in enumerate(self.gens):
            generator.writeStartStop(aoData, doData)

    ## This function will close connection to the WaveformChassis.
    #  @param self The object pointer.
    def close(self):
        for generator in self.gens:
            generator.close()
        if self.useTiming == True:
            self.timing.close()
