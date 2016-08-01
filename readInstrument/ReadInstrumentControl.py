# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore
import PyQt5.uic
from functools import partial
from scan.ScanList import scanList
from trace.TraceCollection import TraceCollection
import numpy
from datetime import datetime
from trace.PlottedTrace import PlottedTrace
from trace import pens
import time

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ReadInstrument.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class ReadInstrumentState:
    def __init__(self):
        self.filename =""
        self.autoSave = False
        self.plotName = None


class ReadInstrumentControl(Base, Form):
    def __init__(self, config, traceui, plotdict, parent, meter):
        self.config = config
        self.traceui = traceui
        self.plotDict = plotdict
        self.parent = parent
        super(ReadInstrumentControl, self).__init__()
        self.state = self.config.get("PicoampMeterState", ReadInstrumentState() )
                      
    def setupUi(self, parent):
        super(ReadInstrumentControl, self).setupUi(parent)
        self.instrumentEdit.setText( self.meterState.instrument )
        self.instrumentEdit.returnPressed.connect( self.openInstrument )
#         if self.meterState.instrument:
#             self.openInstrument()
        self.enableMeasurementBox.stateChanged.connect( self.onZeroCheck )
        self.enableMeasurementBox.setChecked( not self.meterState.zeroCheck )
        self.autoRangeBox.stateChanged.connect( self.onAutoRange )
        self.autoRangeBox.setChecked( self.meterState.autoRange )
        self.voltageRangeSelect.currentIndexChanged[int].connect( self.onVoltageRange )
        self.voltageRangeSelect.setCurrentIndex( self.voltageRangeSelect.findText("{0}".format(self.meterState.voltageRange)))
        self.currentLimitSelect.currentIndexChanged[int].connect( self.onCurrentLimit )
        self.currentLimitSelect.setCurrentIndex( self.meterState.currentLimit)
        self.enableOutputBox.stateChanged.connect( self.onEnableOutput )
        self.enableOutputBox.setChecked(False)
        self.voltageEdit.valueChanged.connect( self.onVoltage )
        self.voltageEdit.setValue( self.meterState.voltage )
        self.startEdit.setValue( self.meterState.start )
        self.startEdit.valueChanged.connect( partial( self.onValueChanged, 'start') )
        self.stopEdit.setValue( self.meterState.stop )
        self.stopEdit.valueChanged.connect( partial( self.onValueChanged, 'stop') )
        self.stepsEdit.setValue( self.meterState.steps )
        self.stepsEdit.valueChanged.connect( partial( self.onValueChanged, 'steps') )
        self.timeDeltaEdit.setValue( self.meterState.timeDelta )
        self.timeDeltaEdit.valueChanged.connect( partial( self.onValueChanged, 'timeDelta') )
        self.zeroButton.clicked.connect( self.onZero )
        self.measureButton.clicked.connect( self.onMeasure )
        self.scanButton.clicked.connect( self.onScan )
        self.scanTypeCombo.setCurrentIndex( self.meterState.scanType )
        self.scanTypeCombo.currentIndexChanged[int].connect( partial(self.onValueChanged, 'scanType') )
        self.filenameEdit.setText( self.meterState.filename )
        self.filenameEdit.textChanged.connect( partial(self.onValueChanged, 'filename'))
        self.logButton.clicked.connect( self.onLogging )
        
    def onLogging(self, checked):
        if checked:
            if not self.loggingActive:
                self.startLogging()
        else:
            self.stopLogging()
        
    def startLogging(self):
        self.trace = TraceCollection()
        self.trace.name = "scan"
        self.plottedTrace =  PlottedTrace(self.trace, self.plotDict['Time']['view'], pens.penList )
        self.plottedTrace.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
        self.traceAdded = False
        self.stopRequested = False
        QtCore.QTimer.singleShot( 0, self.takeLoggingPoint )
        self.loggingActive = True
        self.startTime = time.time()

    def takeLoggingPoint(self):
        value = float(self.meter.read())
        self.trace.x = numpy.append( self.trace.x, time.time()-self.startTime )
        self.trace.y = numpy.append( self.trace.y, value )
        if not self.traceAdded:
            self.traceui.addTrace( self.plottedTrace, pen=-1)
            self.traceAdded = True
        else:
            self.plottedTrace.replot()
        if self.stopRequested:
            self.finalizeScan()
            self.loggingActive = False
        else:
            QtCore.QTimer.singleShot(self.meterState.timeDelta.m_as('ms'), self.takeLoggingPoint )
        
    def stopLogging(self):
        self.stopRequested = True
       
    def onScan(self):
        self.startScan()
        
    def onStop(self):
        self.stopRequested = True
                
    def startScan(self):
        self.scanList = scanList(self.meterState.start, self.meterState.stop, self.meterState.steps, self.meterState.scanType)
        self.currentIndex = 0
        self.trace = TraceCollection()
        self.trace.name = "scan"
        self.plottedTrace =  PlottedTrace(self.trace, self.plotDict['Scan']['view'], pens.penList )
        self.plottedTrace.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
        self.traceAdded = False
        self.meter.setZeroCheck(False)
        self.meter.voltageEnable(True)
        self.stopRequested = False
        QtCore.QTimer.singleShot(0, self.initPoint )
    
    def initPoint(self):
        if self.currentIndex<len(self.scanList) and not self.stopRequested:
            self.meter.setVoltage( self.scanList[self.currentIndex] )
            QtCore.QTimer.singleShot(0, self.takeScanPoint )
        else:
            self.meter.setVoltage( self.meterState.voltage )
            self.finalizeScan()
    
    def takeScanPoint(self):
        value = float(self.meter.read())
        self.trace.x = numpy.append( self.trace.x, self.scanList[self.currentIndex].m_as('V') )
        self.trace.y = numpy.append( self.trace.y, value )
        if not self.traceAdded:
            self.traceui.addTrace( self.plottedTrace, pen=-1)
            self.traceAdded = True
        else:
            self.plottedTrace.replot()
        self.currentIndex += 1
        QtCore.QTimer.singleShot(0, self.initPoint )
    
    def finalizeScan(self):
        self.trace.description["traceFinalized"] = datetime.now()
        self.trace.resave(saveIfUnsaved=False)
        
    def onMeasure(self):
        value = float(self.meter.read())
        self.currentLabel.setText(str(value))
        
    def onZero(self):
        self.meter.zero()
        
    def onValueChanged(self, attr, value):
        setattr( self.meterState, attr, value )
        
    def onVoltage(self, value):
        raw = value.m_as("V")
        self.meter.setVoltage(raw)
        self.meterState.voltage = value
        
    def onEnableOutput(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter.voltageEnable(enable)
        self.meterState.voltageEnabled = enable
        
    currentLimits = [2.5e-5, 2.5e-4, 2.5e-3, 2.5e-2]
    def onCurrentLimit(self, index):
        limit = self.currentLimits[index]
        self.meter.setCurrentLimit(limit)
        self.meterState.currentLimit = index
        
    voltageRanges = [10, 50, 500]
    def onVoltageRange(self, index):
        vrange = self.voltageRanges[index]
        self.meter.setVoltageRange( vrange )
        self.meterState.voltageRange = index
        
    def onZeroCheck(self, value):
        enable = value != QtCore.Qt.Checked
        self.meter.setZeroCheck(enable)
        self.meterState.zeroCheck = enable

    def onAutoRange(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter.setAutoRange(enable)
        self.meterState.autoRange = enable

    def openInstrument(self):
        self.meterState.instrument = str(self.instrumentEdit.text())
        self.meter.open( self.meterState.instrument )
        self.meter.reset()
        self.writeAll()
 
    def saveConfig(self):
        self.config["PicoampMeterState"] = self.meterState
        
