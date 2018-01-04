# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import PyQt5.uic
import logging

from PyQt5 import QtCore

from modules.RollingUpdate import rollingUpdate
from trace.PlottedTrace import PlottedTrace 
from trace.TraceCollection import TraceCollection
from operator import attrgetter, methodcaller
import numpy
import functools
from modules.DataDirectory import DataDirectory
from datetime import datetime

from .controller.ControllerClient import frequencyQuantum, voltageQuantum, binToFreq, binToVoltage, sampleTime
from modules.quantity import Q
import math
from digitalLock.controller.ControllerClient import voltageQuantumExternal
from pulser.Encodings import decode, decodeMg

Form, Base = PyQt5.uic.loadUiType(r'digitalLock\ui\LockStatus.ui')

from modules.PyqtUtility import updateComboBoxItems

class StatusData:
    pass

class Settings:
    def __init__(self):
        self.averageTime = Q(100, 'ms')
        self.maxSamples = Q(2000, '')
        self.frequencyPlot = None
        self.errorSigPlot = None
        
    def __setstate__(self, s):
        self.__dict__ = s
        self.__dict__.setdefault( 'averageTime', Q(100, 'ms') )
        self.__dict__.setdefault( 'maxSamples', Q(2000, '') )
        self.__dict__.setdefault( 'frequencyPlot', None )
        self.__dict__.setdefault( 'errorSigPlot', None )

class LockStatus(Form, Base):
    newDataAvailable = QtCore.pyqtSignal( object )
    def __init__(self, controller, config, traceui, plotDict, settings, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.controller = controller
        self.config = config
        self.lockSettings = None
        self.lastLockData = list()
        self.traceui = traceui
        self.errorSigCurve = None
        self.trace = None
        self.freqCurve = None
        self.plotDict = plotDict
        self.settings = self.config.get("LockStatus.settings", Settings())
        self.lastXValue = 0
        self.logFile = None
        self.hardwareSettings = settings

    def setupSpinBox(self, localname, settingsname, updatefunc, unit ):
        box = getattr(self, localname)
        value = getattr(self.settings, settingsname)
        box.setValue( value )
        box.dimension = unit
        box.valueChanged.connect( updatefunc )
        updatefunc( value )
   
    def setupUi(self):
        Form.setupUi(self, self)
        self.setupSpinBox('magHistoryAccum', 'averageTime', self.setAverageTime, 'ms')
        self.setupSpinBox('magMaxHistory', 'maxSamples', self.setMaxSamples, '')
        self.controller.streamDataAvailable.connect( self.onData )
        self.controller.lockStatusChanged.connect( self.onLockChange )
        self.addTraceButton.clicked.connect( self.onAddTrace )
        self.controller.setStreamEnabled(True)
        self.initPlotCombo( self.frequencyPlotCombo, 'frequencyPlot', self.onChangeFrequencyPlot)
        self.initPlotCombo( self.errorSigPlotCombo, 'errorSigPlot', self.onChangeErrorSigPlot)
        self.clearButton.clicked.connect( self.onClear )
        
    def initPlotCombo(self, combo, plotAttrName, onChange ):
        combo.addItems( list(self.plotDict.keys()) )
        plotName = getattr(self.settings, plotAttrName)
        if plotName is not None and plotName in self.plotDict:
            combo.setCurrentIndex( combo.findText(plotName))
        else:   
            setattr( self.settings, plotAttrName, str( combo.currentText()) )
        combo.currentIndexChanged[str].connect( onChange )

    def onPlotConfigurationChanged(self, plotDict):
        self.plotDict = plotDict
        if self.settings.frequencyPlot not in self.plotDict:
            self.settings.frequencyPlot = list(self.plotDict.keys())[0]
        if self.settings.errorSigPlot not in self.plotDict:
            self.settings.errorSigPlot = list(self.plotDict.keys())[0]
        updateComboBoxItems( self.frequencyPlotCombo, list(self.plotDict.keys()) )
        updateComboBoxItems( self.errorSigPlotCombo, list(self.plotDict.keys()) )       
        
    def onChangeFrequencyPlot(self, name):
        name = str(name)
        if name!=self.settings.frequencyPlot and name in self.plotDict:
            self.settings.frequencyPlot = name
            if self.freqCurve is not None:
                self.freqCurve.setView( self.plotDict[name]['view'])                      
    
    def onChangeErrorSigPlot(self, name):
        name = str(name)
        if name!=self.settings.errorSigPlot and name in self.plotDict:
            self.settings.errorSigPlot = name
            if self.errorSigCurve is not None:
                self.errorSigCurve.setView( self.plotDict[name]['view'])
        
    def setAverageTime(self, value):
        self.settings.averageTime = value        
        mySampleTime = sampleTime.copy()
        if self.lockSettings is not None and self.lockSettings.filter >0:
            mySampleTime *= 2
        accumNumber = int(value / mySampleTime)
        self.controller.setStreamAccum(accumNumber)
        
    def setMaxSamples(self, samples):
        self.settings.maxSamples = samples
        
    def onLockChange(self, data=None):
        pass
    
    def onControlChanged(self, value):
        self.lockSettings = value
        self.setAverageTime(self.settings.averageTime)
        self.onLockChange()
    
    def convertStatus(self, item):
        logger = logging.getLogger(__name__)
        if self.lockSettings is None:
            return None
        status = StatusData()

        status.regulatorFrequency = binToFreq(item.freqSum / float(item.samples))
        # setSignificantDigits(status.regulatorFrequency, frequencyQuantum)
        status.referenceFrequency = self.lockSettings.referenceFrequency + status.regulatorFrequency
        # setSignificantDigits(status.referenceFrequency, frequencyQuantum)

        status.outputFrequency = self.lockSettings.outputFrequency + binToFreq(item.freqSum / float(item.samples) )* self.lockSettings.harmonic
        # setSignificantDigits(status.outputFrequency, frequencyQuantum)

        binvalue = (item.freqMax - item.freqMin) 
        status.referenceFrequencyDelta = binToFreq(binvalue) 
        # setSignificantDigits(status.referenceFrequencyDelta, frequencyQuantum)        
        status.referenceFrequencyMax = binToFreq(item.freqMax)
        # setSignificantDigits(status.referenceFrequencyMax, frequencyQuantum)
        status.referenceFrequencyMin = binToFreq(item.freqMin)
        # setSignificantDigits(status.referenceFrequencyMin, frequencyQuantum)

        binvalue *= self.lockSettings.harmonic
        status.outputFrequencyDelta = abs(binToFreq(binvalue))
        # setSignificantDigits(status.outputFrequencyDelta, frequencyQuantum*self.lockSettings.harmonic)
        status.outputFrequencyMax = self.lockSettings.outputFrequency + binToFreq(item.freqMax)* self.lockSettings.harmonic
        # setSignificantDigits(status.outputFrequencyMax, frequencyQuantum)
        status.outputFrequencyMin = self.lockSettings.outputFrequency + binToFreq(item.freqMin)* self.lockSettings.harmonic
        # setSignificantDigits(status.outputFrequencyMin, frequencyQuantum)
        
        status.errorSigAvg = binToVoltage( item.errorSigSum/float(item.samples) )
        # setSignificantDigits( status.errorSigAvg, voltageQuantum )
        binvalue = item.errorSigMax - item.errorSigMin
        status.errorSigDelta = binToVoltage(binvalue )
        # setSignificantDigits( status.errorSigDelta, voltageQuantum )            
        status.errorSigMax = binToVoltage(item.errorSigMax)
        # setSignificantDigits( status.errorSigMax, voltageQuantum )            
        status.errorSigMin = binToVoltage(item.errorSigMin)
        # setSignificantDigits( status.errorSigMin, voltageQuantum )
        
        status.errorSigRMS = binToVoltage( math.sqrt(item.errorSigSumSq/float(item.samples)) )
        # setSignificantDigits( status.errorSigRMS, voltageQuantum )
        
        status.externalMin = decodeMg(item.externalMin, self.hardwareSettings.onBoardADCEncoding)
        # setSignificantDigits( status.externalMin, voltageQuantumExternal )
        status.externalMax = decodeMg(item.externalMax, self.hardwareSettings.onBoardADCEncoding)
        # setSignificantDigits( status.externalMax, voltageQuantumExternal )
        if item.externalCount>0:
            status.externalAvg = decodeMg( item.externalSum / float(item.externalCount), self.hardwareSettings.onBoardADCEncoding )
            # setSignificantDigits( status.externalAvg, voltageQuantumExternal/(math.sqrt(item.externalCount) if item.externalCount>0 else 1))
            status.externalDelta = abs(status.externalMax - status.externalMin)
            # setSignificantDigits( status.externalDelta, voltageQuantumExternal )
        else:
            status.externalAvg = None
            status.externalDelta = None
        status.lockStatus = item.lockStatus if self.lockSettings.mode & 1 else -1
        logger.debug("External min: {0} max: {1} samples: {2} sum: {3}".format(item.externalMin, item.externalMax, item.externalCount, item.externalSum))
        
        status.time = item.samples * sampleTime.m_as('s')
        return status
    
    logFrequency = ['regulatorFrequency', 'referenceFrequency', 'referenceFrequencyMin', 'referenceFrequencyMax', 
                      'outputFrequency', 'outputFrequencyMin', 'outputFrequencyMax']
    logVoltage = ['errorSigAvg', 'errorSigMin', 'errorSigMax', 'errorSigRMS', 'externalAvg', 'externalMin', 'externalMax']                 
    def writeToLogFile(self, status):
        if self.lockSettings and self.lockSettings.mode & 1 == 1:  # if locked
            if not self.logFile:
                self.logFile = open( DataDirectory().sequencefile("LockLog.txt")[0], "w" )
                self.logFile.write( " ".join( self.logFrequency + self.logVoltage ) )
                self.logFile.write( "\n" )
            self.logFile.write( "{0} ".format(datetime.now()))
            self.logFile.write(  " ".join( map( repr, list(map( methodcaller('m_as', 'Hz'), (getattr(status, field) for field in self.logFrequency) )) ) ) )
            self.logFile.write(  " ".join( map( repr, list(map( methodcaller('m_as', 'mV'), (getattr(status, field) for field in self.logVoltage) )) ) ) )
            self.logFile.write("\n")
            self.logFile.flush()
        
    background = { -1: "#eeeeee", 0: "#ff0000", 3: "#00ff00", 1:"#ffff00", 2:"#ffff00" }
    statusText = { -1: "Unlocked", 0:"No Light", 3: "Locked", 1: "Partly no light", 2: "Partly no light"}
    def onData(self, data=None ):
        logger = logging.getLogger()
        logger.debug( "received streaming data {0} {1}".format(len(data), data[-1] if len(data)>0 else ""))
        if data is not None:
            self.lastLockData = list()
            for item in data:
                converted = self.convertStatus(item)
                if converted is not None:
                    self.lastLockData.append( converted )
                    if converted.lockStatus==3:
                        self.writeToLogFile(converted)
        if self.lastLockData is not None:
            self.plotData()
            if self.lastLockData:
                item = self.lastLockData[-1]
                
                self.referenceFreqLabel.setText( str(item.referenceFrequency) )
                self.referenceFreqRangeLabel.setText( str(item.referenceFrequencyDelta) )
                self.outputFreqLabel.setText( str(item.outputFrequency))
                self.outputFreqRangeLabel.setText( str(item.outputFrequencyDelta))
                
                self.errorSignalLabel.setText( str(item.errorSigAvg))
                self.errorSignalRangeLabel.setText( str(item.errorSigDelta))
                self.errorSignalRMSLabel.setText( str(item.errorSigRMS))
                
                self.externalSignalLabel.setText( str(item.externalAvg))
                self.externalSignalRangeLabel.setText( str(item.externalDelta) )
                logger.debug("error  signal min {0} max {1}".format(item.errorSigMin, item.errorSigMax ))
                
                self.statusLabel.setStyleSheet( "QLabel {{ background: {0} }}".format( self.background[item.lockStatus]) )
                self.statusLabel.setText( self.statusText[item.lockStatus] )
                self.newDataAvailable.emit( item )
        else:
            logger.info("no lock control information")
            
    def plotData(self):
        if len(self.lastLockData)>0:
            to_plot = list(zip(*(attrgetter('errorSigAvg', 'errorSigMin', 'errorSigMax', 'time')(e) for e in self.lastLockData)))
            x = numpy.arange( self.lastXValue, self.lastXValue+len(to_plot[0] ))
            self.lastXValue += len(to_plot[0] )
            y = numpy.array([v.m_as('V') for v in to_plot[0]])
            bottom = numpy.array([(v0 - v1).m_as('V') for v0, v1 in zip(to_plot[0], to_plot[1])])
            top = numpy.array([(v2 - v0).m_as('V') for v0, v2 in zip(to_plot[0], to_plot[2])])
            if self.trace is None:
                self.trace = TraceCollection()
                self.trace['x'] = x
                self.trace['y'] = y
                self.trace['bottom'] = bottom
                self.trace['top'] = top
                self.trace.name = "History"
            else:
                self.trace['x'] = rollingUpdate(self.trace['x'], x, self.settings.maxSamples)
                self.trace['y'] = rollingUpdate(self.trace['y'], y, self.settings.maxSamples)
                self.trace['bottom'] = rollingUpdate(self.trace['bottom'], bottom, self.settings.maxSamples)
                self.trace['top'] = rollingUpdate(self.trace['top'], top, self.settings.maxSamples)
            if self.errorSigCurve is None:
                self.errorSigCurve = PlottedTrace(self.trace, self.plotDict[self.settings.errorSigPlot], pen=-1, style=PlottedTrace.Styles.points, name="Error Signal", windowName=self.settings.errorSigPlot)  #@UndefinedVariable
                self.errorSigCurve.plot()
                self.traceui.addTrace( self.errorSigCurve, pen=-1 )
            else:
                self.errorSigCurve.replot()            
               
            to_plot = list(zip(*(attrgetter('regulatorFrequency', 'referenceFrequencyMin', 'referenceFrequencyMax')(e) for e in self.lastLockData)))
            y = numpy.array([v.m_as('Hz') for v in to_plot[0]])
            bottom = numpy.array([(v0 - v1).m_as('Hz') for v0, v1 in zip(to_plot[0], to_plot[1])])
            top = numpy.array([(v2 - v0).m_as('Hz') for v0, v2 in zip(to_plot[0], to_plot[2])])
            self.trace['freq'] = rollingUpdate(self.trace['freq'], y, self.settings.maxSamples)
            self.trace['freqBottom'] = rollingUpdate(self.trace['freqBottom'], bottom, self.settings.maxSamples)
            self.trace['freqTop'] = rollingUpdate(self.trace['freqTop'], top, self.settings.maxSamples)
            if self.freqCurve is None:
                self.freqCurve = PlottedTrace(self.trace, self.plotDict[self.settings.frequencyPlot], pen=-1, style=PlottedTrace.Styles.points, name="Repetition rate", #@UndefinedVariable
                                              xColumn='x', yColumn='freq', topColumn='freqTop', bottomColumn='freqBottom', windowName=self.settings.frequencyPlot)  
                self.freqCurve.plot()
                self.traceui.addTrace( self.freqCurve, pen=-1 )
            else:
                self.freqCurve.replot()                        
             
    def onClear(self):
        if self.trace:
            self.trace['x'] = numpy.array([])
            self.trace['y'] = numpy.array([])
            self.trace['bottom'] = numpy.array([])
            self.trace['top'] = numpy.array([])
            self.trace['freq'] = numpy.array([])
            self.trace['freqBottom'] = numpy.array([])
            self.trace['freqTop'] = numpy.array([])
           
    def onAddTrace(self):
        self.trace = None
        self.errorSigCurve = None
        self.freqCurve = None
        
    def saveConfig(self):
        self.config["LockStatus.settings"] = self.settings
        
