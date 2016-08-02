# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .WaveformGenerator import WaveformGenerator
from .itfParser import itfParser
from .eMapParser import eMapParser
from .Timing import Timing
import threading
from PyDAQmx import DAQError
from . import DAQmxUtility as dutil
from .chassisConfigParser import chassisConfigParser
import numpy 
from scipy.interpolate import interp1d
from re import search
#from time import sleep

## This class contains a list of WaveformGenerator objects and a Timing object.
#  It is intended to represent a chasis with a NiSync Card and a number
#  of PXI-6733s. It contains low level functions for the Wavefrom Chassis class.
class WCLowLevel(object):
    ## This function is a constructor for the WCLowLevel class. It
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
        self.gens = []

        ## This is the sample rate of all the Analog and Digital outputs.
        #  The sample rate must be the same for all devices configured in the
        #  WaveformChassis.
        self._sampleRate = 100e3

        ## This is the number of channels configured for the WaveformChassis.
        #
        #  The samples per channel must be the same for all devices
        #  configured in the WaveformChassis.
        self._samplesPerChannel = 1000

        self._pauseTriggerSource = ''

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

    def _getSamplesPerChannel(self):
        if len(self.gens) != 0:
            self._samplesPerChannel = self.gens[0].samplesPerChannel
        return self._samplesPerChannel

    def _setSamplesPerChannel(self, samplesPerChannel):
        if len(self.gens) != 0:
            for i, generator in enumerate(self.gens):
                if self.mode == dutil.Mode.Static:
                    generator.samplesPerChannel = 1
                else:
                    generator.samplesPerChannel = samplesPerChannel

        self._samplesPerChannel = samplesPerChannel

    samplesPerChannel = property(_getSamplesPerChannel,
            _setSamplesPerChannel)

    def _getSampleRate(self):
        if self.useTiming:
            self._sampleRate = self.timing.sampleRate
        elif len(self.gens) != 0:
            self._sampleRate = self.gens[0].sampleRate
        return self._sampleRate

    def _setSampleRate(self, sampleRate):
        self._sampleRate = sampleRate
        if self.useTiming:
            self.timing.sampleRate = self._sampleRate
        if len(self.gens) != 0:
            for generator in self.gens:
                generator.sampleRate = self._sampleRate

    sampleRate = property(_getSampleRate, _setSampleRate)

    def _getPauseTriggerSource(self):
        if len(self.gens) != 0:
            source = self.gens[0].pauseTriggerSource
        else:
            source = ''
        return source

    def pauseTriggerOn(self):
        self._pauseTriggerSource = 'PXI_TRIG5'
        for gen in self.gens:
            gen.pauseTriggerSource = self._pauseTriggerSource

    def pauseTriggerOff(self):
        self._pauseTriggerSource = ''
        for gen in self.gens:
            gen.pauseTriggerSource =  self._pauseTriggerSource

    ## @var pauseTriggerSource
    #  This is the pause trigger source terminal for every
    #  WaveformGenerator configured in the WaveformChassis.  It is defaulted to
    #  "PXI_Trig5"
    pauseTriggerSource = property(_getPauseTriggerSource)
        
    def _getAoBuff(self):
        for i, gen in enumerate(self.gens):
            if i<=0:
                buff = gen.aoBuff
            else:
                buff = numpy.append(buff, gen.aoBuff)
        return buff

    ## This is the data stored on the analog output buffer.
    #  This property contains the data that was last stored on the buffer.
    #  It does not query the device for what is on the buffer, so you must
    #  write to the buffer for the data to be returned accurately.
    aoBuff = property(_getAoBuff)

    def _getDone(self):
        done = True
        for gen in self.gens:
            done = done & gen.done
        return done

    done = property(_getDone)

    ## Initializes the waveform chassis based on the object's
    #  configuration.
    #  @param self The object pointer.
    #  @param aoDevsAndChnls This is a list of strings representing
    #  the devices and analog output channels.
    #  @param doDevsAndChnls This is a list of strings representing
    #  the divices and digital output channels.
    #  @param syncDevice This is the device name for the NI Sync card.
    def init(self, aoDevsAndChnls, doDevsAndChnls=None, syncDevice=None):
        numAoDevs = len(aoDevsAndChnls)
        numDoDevs = len(doDevsAndChnls) if doDevsAndChnls is not None else 0
        numDevs = numAoDevs if aoDevsAndChnls > doDevsAndChnls else numDoDevs
        
        self.gens = [WaveformGenerator() for i in range(numDevs)]
        
        
        if syncDevice is not None:
            self.timing.sampleRate = self._sampleRate
            self.timing.init(syncDevice) 
        else:
            self.useTiming = False
        
        self.samplesPerChannel = self._samplesPerChannel

        for i, generator in enumerate(self.gens):
            generator.mode = self.mode
            generator.sampleRate = self._sampleRate
            generator.loops = self.loops
            generator.triggerType = self.triggerType
            device = search('[^/]*', aoDevsAndChnls[i]).group(0)
            #print 'Device: ' + str(device)
            generator.clkSource = '/{0}/{1}'.format(device, self.clkSource)
            #print 'Clock Source:' + generator.clkSource
            generator.startTriggerSource = '/{0}/{1}'.format(device,
                    self.startTriggerSource)
            #print 'Start Trigger: ' + generator.startTriggerSource
            generator.ao.startTriggerSyncCard = '/{0}/{1}'.format(syncDevice,
                    self.startTriggerSource)
            #print 'Sync Card Start Trigger: ' + generator.ao.startTriggerSyncCard
            
            if doDevsAndChnls is None:
                generator.init(aoDevsAndChnls[i])
            else:
                generator.init(aoDevsAndChnls[i], doDevsAndChnls[i])

        if self.mode == dutil.Mode.Static or self._pauseTriggerSource == '':
            self.pauseTriggerOff()
        else:
            self.pauseTriggerOn()

    ## This function will initialize the waveform chassis based on the
    #  configuration file specified by the filePath parameter.
    #  @param self The object pointer
    #  @param filePath The file path to the configuration file.
    def initFromFile(self, filePath):
        config = chassisConfigParser()
        ao, do, sync, edge, clock = config.read(filePath)
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
                testData = numpy.append(testData, data)
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
                testData = numpy.append(testData, data)
            i+=1
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
        sampsPerChannel = len(data)/totalNumChnls
        #sampsPerChannel = self.samplesPerChannel
        #print 'samples per channel: ' + str(sampsPerChannel)
        
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
        #threads = []
        for i, generator in enumerate(self.gens):
            #t = threading.Thread(target=generator.start())
            #threads.append(t)
            #t.start()
            generator.start()
        #for thread in threads:
            #thread.join()
            
        if self.useTiming == True:
            self.timing.sendSoftwareTrigger()
    
    ## This functions waits for the analog and digital output generation to
    #  complete.
    #  @param self The object pointer.
    def waitUntilDone(self):
        #threads = [] 
        for idx, generator in enumerate(self.gens):
            #t = threading.Thread(target=self._waitUntilDoneWorker, args=
            #        (idx, generator))
            #threads.append(t)
            #t.start()
            generator.waitUntilDone()

        #for thread in threads:
            #thread.join()
        '''
        estAcqTime = self.gens[0].ao.estAcqTime
        if estAcqTime < 0.01:
            print 'Sleeping {0}s...'.format(estAcqTime+1)
            sleep(estAcqTime+1)
        '''

    def _waitUntilDoneWorker(self, idx, generator):
        #print 'wait generator: {0}'.format(idx)
        generator.waitUntilDone()
        '''
        estAcqTime = self.gens[0].ao.estAcqTime
        if estAcqTime < 0.01:
            print 'Sleeping {0}s...'.format(estAcqTime+1)
            sleep(estAcqTime+1)
        '''
    
    ## This function stops the analog and digital output generation.
    #  @param self The object pointer.
    def stop(self):
        #threads = []
        for idx, generator in enumerate(self.gens):
            #t = threading.Thread(target=self._stopWorker, args=
            #        (idx, generator))
            #threads.append(t)
            #t.start()
            self._stopWorker(idx, generator)
        #for thread in threads:
        #    thread.join()
    
    def _stopWorker(self, idx, generator):
        try:
            generator.stop()

        except DAQError as e:
            #catch error number 200010 and ignore
            #error number 200010 is actually just a warning
            if e.error == 200010:
                #This will ignore error 200010
                print('stop generator: ' + str(idx))
                #pass
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

    ## This function will interpolate analog outptut data passed as a
    #  parameter.
    #  @param self The object pointer.
    #  @param data analog
    def interp(self, aoData, newSampsPerChnl, **kwargs):
        # valid kinds: linear, nearest, zero, slinear, quadratic, cubic
        # an integer for kind specifys the order of the spline interplator
        if self.samplesPerChannel >= newSampsPerChnl:
            errStr = 'The requested samples per channel must be \n' +     \
            'greater than the current samples per channel.\n\n' +         \
            'samples per channel: {0}\n'.format(self.samplesPerChannel) + \
            'requested samples per channel: {0}'.format(newSampsPerChnl)
            raise ValueError(errStr)
        x = numpy.arange(0, self.samplesPerChannel)
        stop = float(self.samplesPerChannel-1)
        xnew = numpy.linspace(0, stop, newSampsPerChnl)
        kind = kwargs.get('kind', 'linear')
        chnls = len(aoData)/self.samplesPerChannel
        data2d = numpy.reshape(aoData, [chnls, self.samplesPerChannel])
        data2dNew = numpy.reshape(numpy.zeros(chnls * newSampsPerChnl),
                [chnls, newSampsPerChnl])
        for i in range(chnls):
            chnlData = data2d[i]
            f = interp1d(x, chnlData, kind=kind)
            data2dNew[i] = f(xnew)
        return numpy.reshape(data2dNew, chnls * newSampsPerChnl)

    ## This function will close connection to the WaveformChassis.
    #  @param self The object pointer.
    def close(self):
        for generator in self.gens:
            generator.close()
        if self.useTiming == True:
            self.timing.close()

## This class contains a list of WaveformGenerator objects and a Timing object.
#  It is intended to represent a chasis with a NiSync Card and a number
#  of PXI-6733s. It contains low level functions from the WCLowLevel class
#  as well as high level functions.
class WaveformChassis(WCLowLevel):
    ## This function is a constructor for the WaveformChassis class. It
    #  creates the internal variables required to perform functions within the
    #  class. This function does not initialize any hardware.
    def __init__(self):
        ## This is a object containing information about the itf file.
        self.itf = itfParser()
        ## This is the path of the eMap file.
        self.eMapPath = ''
        ## This is a dictionary representation of the data in the eMap file.
        self.eMapDict = None
        super(WaveformChassis, self).__init__()

    ## A high level function to load the data in the itf file into memory.
    #  @param self The object reference.
    #  @param itfPath The file path for an itf file.
    #  @param eMapPath A file path for the eMap file.  This parameter is
    #  optional.  An emap file will not be utilized if one is not specified.
    def loadItf(self, itfPath, eMapPath = None):
        self.itf.open(itfPath)
        self.itf.eMapFilePath = self.eMapPath
        self.itflines = self.itf.totalLines
        self.itfData = self.itf.eMapReadLines(self.itf.totalLines)
        self.itf.close()

    def _getLastLine(self):
        aoData = self.aoBuff
        samps = self.samplesPerChannel
        start = samps-1
        stop = len(aoData)
        step = samps
        #print 'aoData[{0},{1},{2}]'.format(start,stop,step)
        return aoData[start:stop:step]

    lastLine = property(_getLastLine)

    def _readEmap(self):
        emap = eMapParser()
        emap.open(self.eMapPath)
        emap.read()
        self.eMapDict = emap.eMapDict 
        emap.close()

    def _getLastLineDict(self):
        lastLine = self._getLastLine()
        if not self.eMapDict:
            self._readEmap()
        electrodes = []
        for electrode in self.eMapDict['electrodes']:
            electrodes.append(int(electrode))
        lastLineDict = {}
        for i, chnl in enumerate(lastLine):
            eName = 'e%02d' % electrodes[i]
            lastLineDict[eName] = chnl
        return lastLineDict

    lastLineDict = property(_getLastLineDict)

    def _buildData(self, start, stop):
        numChnls = len(self.itfData)/self.itflines
        arraySize = (stop-start)*numChnls
        aoData = numpy.zeros(arraySize)
        for i in range(numChnls):
            aoDataStart = i*(stop-start)
            aoDataStop = (stop-start)+aoDataStart
            itfDataStart = start + (self.itflines*i)
            itfDataStop = (stop-start) + itfDataStart
            itfData = self.itfData[itfDataStart:itfDataStop]
            aoData[aoDataStart:aoDataStop]= itfData
        return aoData

    def _fixOneSample(self, start, stop):
        samps = stop - start
        if samps >= 0:
            aoData = self._buildData(start, stop)
        else:
            #Rotate the aoData numpy array
            samps *= -1
            aoData = self._buildData(stop, start)
            chnls = len(aoData)/samps
            aoData = numpy.reshape(aoData, (chnls, samps))
            aoData = numpy.fliplr(aoData)
            aoData = numpy.reshape(aoData, (1, (chnls * samps)))
        if samps == 1:
            cpData = numpy.empty((aoData.size*2,),
                    dtype = aoData.dtype)
            cpData[0::2] = aoData
            cpData[1::2] = aoData
            aoData = cpData
            samps = 2
        self.samplesPerChannel = samps
        return aoData

    ## This function allows the user to step through an itf file by
    #  generating the voltages in the loaded itf file based on the
    #  start and stop input parameters.
    #  @param self The object reference.
    #  @param start The start index of a row in the loaded itf file.
    #  @param stop The stop index of a row in the loaded itf file.
    def stepItf(self, start, stop):
        try:
            aoData = self._fixOneSample(start, stop)
            self.writeAoBuffer(aoData)
            self.start()
            self.waitUntilDone()
        except DAQError as e:
            if e.error == -200560:
                pass
            else:
                raise
        finally:
            self.stop()
        return aoData

    def stepItfInterp(self, start, stop, newSamps, **kwargs):
        tempSamps = self.samplesPerChannel
        try:
            aoData = self._fixOneSample(start, stop)
            aoData = self.interp(aoData, newSamps, **kwargs) 
            self.samplesPerChannel = newSamps
            self.writeAoBuffer(aoData)
            self.start()
            self.waitUntilDone()
        except DAQError as e:
            if e.error == -200560:
                pass
            else:
                raise
        finally:
            self.stop()
            self.samplesPerChannel = tempSamps
        return aoData

    def _ignoreDaqError(self, e):
        if e.error == -200560:
            pass
        else:
            raise

    ## This function will run through an entire itf file
    #  by generating the voltages in the loaded itf file.
    #  @param self The object reference.
    def runItf(self):
        try:
            aoData = self.itfData
            self.samplesPerChannel = self.itflines
            self.writeAoBuffer(aoData)
            #self.writeDoBuffer(doData)
            self.start()
            self.waitUntilDone()
        except DAQError as e:
            self._ignoreDaqError(e)
        finally:
            self.stop()

    ## This function will take an array of data and generate
    #  the voltages contained in the array.
    #  @param self The object reference.
    #  @param aoData A numpy ndarray representing data to
    #  generate from the Analog Outputs.
    #  @param doData (optional) A numpy ndarray representing
    #  data to generate from the Digital Outputs.
    def applyArray(self, aoData, doData = None):
        try:
            cpData = numpy.empty((aoData.size*2,),
                    dtype = aoData.dtype)
            cpData[0::2] = aoData
            cpData[1::2] = aoData
            aoData = cpData
            self.samplesPerChannel = 2
            self.writeAoBuffer(aoData)
            if doData:
                self.writeDoBuffer(doData)
            self.start()
            self.waitUntilDone()
        except DAQError as e:
            self._ignoreDaqError(e)
        finally:
            self.stop()

if __name__ == '__main__':
    WCS = WaveformChassis()
    try:
        WCS.samplesPerChannel = 1000
        homePath = 'c:\\Workspace\\'
        #WCS.initFromFile(homePath + 'Chassis.git\\config\\analog_only.cfg')
        WCS.initFromFile(homePath + 'Chassis.git\\config\\sana118.cfg')
        WCS.eMapPath = homePath + 'Chassis.git\\config\\test_map.txt'
        itfFile = homePath + 'Chassis.git\\config\\SineWave.itf'
        WCS.loadItf(itfFile)
        WCS.stepItf(0, 500)
        WCS.stepItf(500, 1000)
        WCS.runItf()
    
    finally:
        pass
    #    WCS.close()
