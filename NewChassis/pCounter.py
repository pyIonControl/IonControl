# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyDAQmx import Task
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
import ctypes
import numpy as np
from math import sqrt
from .gui.PyQwtPlotDlg import AutoUpdatePlot

class IBinPCounter(object):
    def __init__(self, **kwargs):
        raise NotImplementedError('__init__() method not implemented')

    def _calcBinAndAcq(self):
        self._binTime = 1000./self._sampleRate
        self._acqTime = (self._samples -1.) * self._binTime

    def _calcSampsAndSampRate(self):
        self._sampleRate = 1000/self._binTime
        self._samples = int((self._acqTime / self._binTime) + 1)

    def _getSamples(self):
        raise NotImplementedError('_getSamples() method not implemented')

    def _setSamples(self):
        raise NotImplementedError('_getSamples() method not implemented')

    samples = property(_getSamples, _setSamples)

    def _getSampleRate(self, value):
        raise NotImplementedError('_getSampleRate() method not implemented')

    def _setSampleRate(self):
        raise NotImplementedError('_setSampleRate() method not implemented')

    sampleRate = property(_getSampleRate, _setSampleRate)

    def _getBinTime(self):
        raise NotImplementedError('_getBinTime() method not implemented')

    def _setBinTime(self, value):
        raise NotImplementedError('_setBinTime() method not implemented')

    binTime = property(_getBinTime, _setBinTime)

    def _getAcqTime(self):
        raise NotImplementedError('_getAcqTime() method not implemented')

    def _setAcqTime(self):
        raise NotImplementedError('_setAcqTime() method not implemented')

    acqTime = property(_getAcqTime, _setAcqTime)

    def init(self, **kwargs):
        raise NotImplementedError('init() method not implemented')

    def initFromFile(self, filepath):
        raise NotImplementedError('initFromFile() method not implemented')

    def start(self):
        raise NotImplementedError('start() method not implemented')

    def stop(self):
        raise NotImplementedError('stop() method not implemented')

    def read(self):
        raise NotImplementedError('read() method not implemented')

    def measure(self):
        raise NotImplementedError('measure() method not implemented')

    def close(self):
        raise NotImplementedError('close() method not implemetned')

## This class will count edges of a ditial signal at a sample clock rate
#  specified, and has capability of being triggered to start.
class pCounter(object):
    ## This function is the constructor for the pCounter class.
    #
    #  It creates internal variables required to perform functions within
    #  the class. This function does not initialize any hardware.
    #  @param self The object pointer.
    def __init__(self, **kwargs):
        #super(pCounter, self).__init__()
        ## The string that identifies the DAQmx device and counter
        #  for the counter that is used to count edges.
        #
        #  Example: PXISlot5/ctr0
        self.edgeCounter = ''

        ## The string that identifies the DAQmx device and counter
        #  for the counter that is used to create the sample clock.
        #
        #  Example: /PXI1Slot5/ctr0
        self.clockCounter = ''

        ##  A boolean that enables the start trigger.
        #
        #  The default is false, which disables the start trigger.
        #  The measurement will immediately start when the start()
        #  method is called.
        #  A true value will make the measurement start when a digital
        #  trigger is received on the line specified by the triggerSource
        #  variable.
        self.enableStartTrigger = False

        ## A string that identifies the DAQmx digital line that will
        #  be used as an input to the edge counter.
        #
        #  Default: PFI0
        self.edgeCntrTerm = kwargs.get('edgeCntrTerm', 'PFI0')

        self._triggerClkSource = 'Ctr0InternalOutput'

        ## A string that identifies the DAQmx digital line that will
        #  be used as the start trigger.
        #
        #  Default: PFI1
        self.triggerSource = 'PFI1'

        ## A string that identifies the DAQmx digital line that will
        #  output the sample clock.
        #
        #  Default: PFI12
        self.clockSourceTerm = kwargs.get('clockSourceterm', 'PFI12')

        ## The task reference for the edge counter.
        self.edgeCntrTask = Task()

        ## The task reference for the sample clock counter.
        self.clockCntrTask = Task()

        ## @var samples
        #  This is the number of samples to take.  It is the size
        #  of the data array returned by the read() method.
        self._samples = kwargs.get('samples', None)

        ## @var sampleRate
        #  This is the sample rate to use when counting edges.
        self._sampleRate = kwargs.get('sampleRate', None)

        ## @var acqTime
        #  This is the time in milliseconds for a full acquisition
        #  period.
        self._acqTime = None

        ## @var binTime
        #  This is the time in millisenconds to take a single sample.
        self._binTime = None

        self._status = int32()

        ## This is the time to wait for a start trigger.
        #
        #  If the timeout passes, then an error is generated. Ignore
        #  this variable if the start trigger is disabled.
        self.timeout = kwargs.get('timeout', 1)
        self._samplesRead = None

    def _calcBinAndAcq(self):
        self._binTime = 1000./self._sampleRate
        self._acqTime = (self._samples -1.) * self._binTime

    def _calcSampsAndSampRate(self):
        self._sampleRate = 1000/self._binTime
        self._samples = int((self._acqTime / self._binTime) + 1)

    def _getSamples(self):
        return self._samples

    def _setSamples(self, value):
        self._samples = value
        if self._sampleRate:
            self._calcBinAndAcq()

    samples = property(_getSamples, _setSamples)

    def _getSampleRate(self):
        return self._sampleRate

    def _setSampleRate(self, value):
        self._sampleRate = value
        if self._samples:
            self._calcBinAndAcq()

    sampleRate = property(_getSampleRate, _setSampleRate)

    def _getBinTime(self):
        return self._binTime

    def _setBinTime(self, value):
        self._binTime = value
        if self._acqTime:
            self._calcSampsAndSampRate()

    binTime = property(_getBinTime, _setBinTime)

    def _getAcqTime(self):
        return self._acqTime

    def _setAcqTime(self, value):
        self._acqTime = value
        if self._binTime:
            self._calcSampsAndSampRate()

    acqTime = property(_getAcqTime, _setAcqTime)

    ## This function initializes the pCounter class and opens a
    #  reference to the DAQmx device(s).
    #
    #  If specifiying a acqTime and binTime or samples and sampleRate,
    #  only one pair of parameters need to be provided.  When specifying
    #  acqTime and binTime, the samples and sampleRate are calculated.
    #  When specifying the samples and sampleRate, the acqTime and
    #  binTime are calculated.
    #
    #  @param self The object pointer.
    #  @param clockCounter The string that identifies the DAQmx
    #  device and counter for the counter that is used to create
    #  the sample clock.
    #  @param edgeCounter The string that identifies the DAQmx
    #  device and counter for the counter that is used to count edges.
    #  @param acqTime This is the time in milliseconds for a full
    #  acquisition period.
    #  @param binTime This is the time in millisenconds to take a
    #  single sample.
    #  @param samples The number of samples for the pCounter to take.
    #  @param sampleRate The frequency of the samples taken by the 
    #  pCounter.
    def init(self, clockCounter=None, edgeCounter=None, acqTime=None, 
            binTime=None, samples=None, sampleRate=None):
        if edgeCounter:
            self.edgeCounter = edgeCounter
        if clockCounter:
            self.clockCounter = clockCounter

        if samples and sampleRate:
            self._samples = samples
            self._sampleRate = sampleRate
            self._calcBinandAcq()

        if acqTime and binTime:
            self._acqTime = acqTime
            self._binTime = binTime
            self._calcSampsAndSampRate()

        # Setup the Edge Counter
        self._status = self.edgeCntrTask.CreateCICountEdgesChan(
                self.edgeCounter, '', DAQmx_Val_Rising, 0,
                DAQmx_Val_CountUp)
        self._status = self.edgeCntrTask.SetCICountEdgesTerm(
                self.edgeCounter, self.edgeCntrTerm)
        self._status = self.edgeCntrTask.CfgSampClkTiming(
                self._triggerClkSource,
                float64(self._sampleRate), DAQmx_Val_Rising,
                DAQmx_Val_FiniteSamps, uInt64(self._samples+1))

        # Setup the Clock Source Counter
        self._status = self.clockCntrTask.CreateCOPulseChanFreq(
                self.clockCounter, '', DAQmx_Val_Hz, DAQmx_Val_Low,
                0, float64(self._sampleRate), float64(0.5))
        self._status = self.clockCntrTask.SetCOPulseTerm(self.clockCounter,
                self.clockSourceTerm)
        self._status = self.clockCntrTask.CfgImplicitTiming(
                DAQmx_Val_ContSamps, uInt64(self._samples+1))
        if self.enableStartTrigger:
            self._status = self.clockCntrTask.CfgDigEdgeStartTrig(
                    self.triggerSource, DAQmx_Val_Rising)

    ## This function initializes the pCounter class using the
    #  chassis config file and opens a reference to the DAQmx device(s).
    #
    #  @param self The object reference.
    #  @param filepath The path to the chassis config file.
    def initFromFile(self, filepath):
        from .chassisConfigParser import chassisConfigParser
        config = chassisConfigParser()
        edgeCounter, clockCounter = config.readCntrSection(filepath)
        self.init(clockCounter, edgeCounter)

    ## This function starts the measurement.
    #
    #  If the start trigger is enabled, then a the pCounter waits
    #  for that digital trigger.  Otherwise the measurement takes
    #  place immediately.
    #  @param self The object pointer.
    def start(self):
        self._status = self.edgeCntrTask.StartTask()
        self._status = self.clockCntrTask.StartTask()

    ## This function stops the measurement.
    #
    #  It needs to be called everytime the start() method is called.
    #  @param self The object pointer.
    def stop(self):
        self._status = self.edgeCntrTask.StopTask()
        self._status = self.clockCntrTask.StopTask()

    ## This function returns an array of the edge counts with an
    #  array size equal to the number of samples.
    #
    #  @param self The object pointer.
    def read(self):
        samplesRead = int32()
        data = np.zeros(self._samples+1, dtype = np.uint32)

        self._status = self.edgeCntrTask.ReadCounterU32(
                int32(self._samples+1),
                float64(self.timeout), data, uInt32(self._samples+1), 
                ctypes.byref(samplesRead), None)
        self._samplesRead = samplesRead.value

        dataDelta = []
        for i, item in enumerate(data):
            if i >0:
                dataDelta.append(item - preValue)
            preValue = item

        length = len(dataDelta)
        dataSum = 0
        for item in dataDelta:
            dataSum += item
        mean = float(dataSum/length)

        sqSum = 0
        for item in dataDelta:
            sq = np.square(item - mean)
            sqSum += sq
        stdDev = sqrt(sqSum/length)

        return dataDelta, mean, stdDev

    ## This function performs the start(), read(), and stop() methods
    #  in one function call.
    #
    #  This is useful for when the results of the read() method can be
    #  retrieved immediately after a start()
    #  @param self The object pointer.
    def measure(self):
        # Start the Tasks
        self.start()

        # Read the data
        data, mean, stdDev = self.read()


        # Stop the Tasks
        self.stop()

        return data, mean, stdDev

    ## This function closes the refences to the DAQmx devices.
    #
    #  @param self The object pointer.
    def close(self):
        self._status = self.edgeCntrTask.ClearTask()
        self.edgeCntrTask = Task()

        self._status = self.clockCntrTask.ClearTask()  
        self.clockCntrTask = Task()

    ## This function is the destructor for the pCounter class.
    #
    #  It deletes internal variables and closes the references to
    #  the DAQmx devices if they are not already closed.
    #  @param self The object pointer.
    def __del__(self):
        self.close()

        del self.edgeCounter
        del self.clockCounter
        del self.enableStartTrigger
        del self.edgeCntrTerm
        del self._triggerClkSource
        del self.triggerSource
        del self.clockSourceTerm
        del self.edgeCntrTask
        del self.clockCntrTask
        del self._samples
        del self._sampleRate
        del self._acqTime
        del self._binTime
        del self._status
        del self.timeout
        del self._samplesRead

        

class PCntrPlotDlg(pCounter, AutoUpdatePlot):
    def __init__(self, **kwargs):
        from PyQt5.Qt import Qt
        kwargs['chartXAxisTitle'] = kwargs.get('chartXAxisTitle',
                'Time (Units)')
        kwargs['chartYAxisTitle'] = kwargs.get('chartYAxisTitle',
                'Counts')
        AutoUpdatePlot.__init__(self, **kwargs)
        pCounter.__init__(self, **kwargs)
        self._curveTitle = 'counts'
        self.addCurve(self._curveTitle, curveColor=Qt.blue)
        self._closed = False
        '''
        self.dlg = AutoUpdatePlot(chartHistoryLen = chartHistoryLen,
                chartTitle = 'Counts', chartXAxisTitle = '',
                chartYAxisTitle = 'Counts', winTitle = 'pCounter')
        self.dlg.timerEvent = self.timerEvent
        self._curveTitle = 'counts'
        self.dlg.addCurve(self._curveTitle, curveColor=Qt.green)
        '''

    def timerEvent(self, e):
        if not self._closed:
            data, mean, stdDev = super(PCntrPlotDlg,
                    self).measure()
            self.update(self._curveTitle, mean)

    def close(self):
        super(PCntrPlotDlg, self).close()
        self._closed = True
