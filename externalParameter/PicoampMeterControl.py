# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import pytz
from PyQt5 import QtCore
import PyQt5.uic
from functools import partial

from modules.quantity import Q, is_Q
from scan.ScanList import scanList
from trace.TraceCollection import TraceCollection
import numpy
from datetime import datetime
from trace.PlottedTrace import PlottedTrace
from trace import pens
import time

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/PicoampMeterControl.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

def find_index_nearest(array, value):
    index = (numpy.abs(array-value)).argmin()
    return index


class MeterState:
    def __init__(self):
        self.zeroCheck = True
        self.zeroCheck_2 = True
        self.zeroCheck_3 = True
        self.voltageEnabled = False
        self.voltageEnabled_2 = False
        self.voltageEnabled_3 = False
        self.voltageRange = Q(0, "V")
        self.voltageRange_2 = Q(0, "V")
        self.voltageRange_3 = Q(0, "V")
        self.currentLimit = 0
        self.currentLimit_2 = 0
        self.currentLimit_3 = 0
        self.voltage = Q(0, "V")
        self.voltage_2 = Q(0, "V")
        self.voltage_3 = Q(0, "V")
        self.autoRange = False
        self.autoRange_2 = False
        self.autoRange_3 = False
        self.instrument = ""
        self.instrument_2 = ""
        self.instrument_3 = ""
        self.start = Q(0, "V")
        self.stop = Q(10, "V")
        self.steps = Q(10)
        self.scanType = 0
        self.filename = "IV.txt"
        self.timeDelta = Q(1, "s")
        self.settlingDelay = Q(100, 'ms')

    def __setstate__(self, state):
        """this function ensures that the given fields are present in the class object
        after unpickling. Only new class attributes need to be added here.
        """
        self.__dict__ = state
        self.__dict__.setdefault('scanType', 0)
        self.__dict__.setdefault('filename', 'IV.txt')
        self.__dict__.setdefault('timeDelta', Q(1, "s"))
        self.__dict__.setdefault('zeroCheck_2', True )
        self.__dict__.setdefault('zeroCheck_3', True )
        self.__dict__.setdefault('voltageEnabled_2', False )
        self.__dict__.setdefault('voltageEnabled_3', False )
        self.__dict__.setdefault('voltageRange_2', 0 )
        self.__dict__.setdefault('voltageRange_3', 0 )
        self.__dict__.setdefault('currentLimit_2', 0 )
        self.__dict__.setdefault('currentLimit_3', 0 )
        self.__dict__.setdefault('voltage_2', 0 )
        self.__dict__.setdefault('voltage_3', 0 )
        self.__dict__.setdefault('autoRange_2', False )
        self.__dict__.setdefault('autoRange_3', False )
        self.__dict__.setdefault('instrument_2', "" )
        self.__dict__.setdefault('instrument_3', "" )

class PicoampMeterControl(Base, Form):
    def __init__(self,config, traceui, plotdict, parent, meter, meter_2 = None, meter_3 = None):
        self.config = config
        self.traceui = traceui
        self.plotDict = plotdict
        self.parent = parent
        self.meter = meter
        self.meter_2 = meter_2
        self.meter_3 = meter_3
        super(PicoampMeterControl, self).__init__()
        self.meterState = self.config.get("PicoampMeterState", MeterState() )
        self.trace = None
        self.stopRequested = False
        self.scanMode = "V"
        self.loggingActive = False
        self.startTime = datetime.now()
        self.scanRunning = False
            
    def writeAll(self):
        self.onVoltage(self.meterState.voltage)
        self.onEnableOutput( self.meterState.voltageEnabled )
        self.onCurrentLimit( self.meterState.currentLimit )
        self.onVoltageRange( self.meterState.voltageRange )
        self.onZeroCheck(self.meterState.zeroCheck )
        self.onAutoRange( self.meterState.autoRange)

    def writeAll_2(self):
        self.onVoltage_2(self.meterState.voltage_2)
        self.onEnableOutput_2( self.meterState.voltageEnabled_2 )
        self.onCurrentLimit_2( self.meterState.currentLimit_2 )
        self.onVoltageRange_2( self.meterState.voltageRange_2 )
        self.onZeroCheck_2(self.meterState.zeroCheck_2 )
        self.onAutoRange_2( self.meterState.autoRange_2 )
           
    def writeAll_3(self):
        self.onVoltage_3(self.meterState.voltage_3)
        self.onEnableOutput_3( self.meterState.voltageEnabled_3 )
        self.onCurrentLimit_3( self.meterState.currentLimit_3 )
        self.onVoltageRange_3( self.meterState.voltageRange_3 )
        self.onZeroCheck_3(self.meterState.zeroCheck_3 )
        self.onAutoRange_3( self.meterState.autoRange_3 )
           
    def setupUi(self, parent):
        super(PicoampMeterControl, self).setupUi(parent)
        self.instrumentEdit.setText( self.meterState.instrument )
        self.instrumentEdit.returnPressed.connect( self.openInstrument )
        self.instrumentEdit_2.setText( self.meterState.instrument_2 )
        self.instrumentEdit_2.returnPressed.connect( self.openInstrument_2 )
        self.instrumentEdit_3.setText( self.meterState.instrument_3 )
        self.instrumentEdit_3.returnPressed.connect( self.openInstrument_3 )
        self.enableMeasurementBox.stateChanged.connect( self.onZeroCheck )
        self.enableMeasurementBox.setChecked( not self.meterState.zeroCheck )
        self.enableMeasurementBox_2.stateChanged.connect( self.onZeroCheck_2 )
        self.enableMeasurementBox_2.setChecked( not self.meterState.zeroCheck_2 )
        self.enableMeasurementBox_3.stateChanged.connect( self.onZeroCheck_3 )
        self.enableMeasurementBox_3.setChecked( not self.meterState.zeroCheck_3 )
        self.autoRangeBox.stateChanged.connect( self.onAutoRange )
        self.autoRangeBox.setChecked( self.meterState.autoRange )
        self.autoRangeBox_2.stateChanged.connect( self.onAutoRange_2 )
        self.autoRangeBox_2.setChecked( self.meterState.autoRange_2 )
        self.autoRangeBox_3.stateChanged.connect( self.onAutoRange_3 )
        self.autoRangeBox_3.setChecked( self.meterState.autoRange_3 )
        self.voltageRangeSelect.currentIndexChanged[int].connect( self.onVoltageRange )
        self.voltageRangeSelect.setCurrentIndex( self.voltageRangeSelect.findText("{0}".format(self.meterState.voltageRange)))
        self.voltageRangeSelect_2.currentIndexChanged[int].connect( self.onVoltageRange_2 )
        self.voltageRangeSelect_2.setCurrentIndex( self.voltageRangeSelect_2.findText("{0}".format(self.meterState.voltageRange_2)))
        self.voltageRangeSelect_3.currentIndexChanged[int].connect( self.onVoltageRange_3 )
        self.voltageRangeSelect_3.setCurrentIndex( self.voltageRangeSelect_3.findText("{0}".format(self.meterState.voltageRange_3)))
        self.currentLimitSelect.currentIndexChanged[int].connect( self.onCurrentLimit )
        self.currentLimitSelect.setCurrentIndex( self.meterState.currentLimit)
        self.currentLimitSelect_2.currentIndexChanged[int].connect( self.onCurrentLimit_2 )
        self.currentLimitSelect_2.setCurrentIndex( self.meterState.currentLimit_2)
        self.currentLimitSelect_3.currentIndexChanged[int].connect( self.onCurrentLimit_3 )
        self.currentLimitSelect_3.setCurrentIndex( self.meterState.currentLimit_3)
        self.enableOutputBox.stateChanged.connect( self.onEnableOutput )
        self.enableOutputBox.setChecked(False)
        self.enableOutputBox_2.stateChanged.connect( self.onEnableOutput )
        self.enableOutputBox_2.setChecked(False)
        self.enableOutputBox_3.stateChanged.connect( self.onEnableOutput_2 )
        self.enableOutputBox_3.setChecked(False)
        self.voltageEdit.valueChanged.connect( self.onVoltage )
        self.voltageEdit.setValue( self.meterState.voltage )
        self.voltageEdit_2.valueChanged.connect( self.onVoltage_2 )
        self.voltageEdit_2.setValue( self.meterState.voltage_2 )
        self.voltageEdit_3.valueChanged.connect( self.onVoltage_3 )
        self.voltageEdit_3.setValue( self.meterState.voltage_3 )
        self.startEdit.setValue( self.meterState.start )
        self.startEdit.valueChanged.connect( partial( self.onValueChanged, 'start') )
        self.stopEdit.setValue( self.meterState.stop )
        self.stopEdit.valueChanged.connect( partial( self.onValueChanged, 'stop') )
        self.stepsEdit.setValue( self.meterState.steps )
        self.stepsEdit.valueChanged.connect( partial( self.onValueChanged, 'steps') )
        self.settlingDelayEdit.setValue( self.meterState.settlingDelay )
        self.settlingDelayEdit.valueChanged.connect( partial( self.onValueChanged, 'settlingDelay') )
        self.timeDeltaEdit.setValue( self.meterState.timeDelta )
        self.timeDeltaEdit.valueChanged.connect( partial( self.onValueChanged, 'timeDelta') )
        self.zeroButton.clicked.connect( self.onZero )
        self.measureButton.clicked.connect( self.onMeasure )
        self.scanButton.clicked.connect( self.onScan )
        self.scanTypeCombo.setCurrentIndex( self.meterState.scanType )
        self.scanTypeCombo.currentIndexChanged[int].connect( partial(self.onValueChanged, 'scanType') )
        self.filenameEdit.setText( self.meterState.filename )
        self.filenameEdit.textChanged.connect( partial(self.onStringValueChanged, 'filename'))
        self.logButton.clicked.connect( self.onLogging )
        
    def onLogging(self, checked):
        if checked:
            if not self.loggingActive:
                self.startLogging()
        else:
            self.stopLogging()
        
    def startLogging(self):
        self.trace = TraceCollection()
#         self.trace.addColumn('voltage_2')
#         self.trace.addColumn('voltage_3')
#         self.trace.addColumn('current_2')
#         self.trace.addColumn('current_3')
        self.trace.name = "scan"
        self.plottedTrace =  PlottedTrace(self.trace, self.plotDict['Time']['view'], pens.penList )
#         self.plottedTrace_2 =  PlottedTrace(self.trace, self.plotDict['Time']['view'], yColumn='current_2', penList=pens.penList )
#         self.plottedTrace_3 =  PlottedTrace(self.trace, self.plotDict['Time']['view'], yColumn='current_3', penList=pens.penList )
        self.voltagePlottedTrace = PlottedTrace(self.trace, self.plotDict['Voltage']['view'], yColumn='voltage', penList=pens.penList )
#         self.voltagePlottedTrace_2 = PlottedTrace(self.trace, self.plotDict['Voltage']['view'], yColumn='voltage_2', penList=pens.penList )
#         self.voltagePlottedTrace_3 = PlottedTrace(self.trace, self.plotDict['Voltage']['view'], yColumn='voltage_3', penList=pens.penList )
        self.plottedTrace.trace.filenamePattern =  self.meterState.filename
        self.voltagePlottedTrace.trace.filenamePattern =  self.meterState.filename
#         self.plottedTrace_2.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
#         self.voltagePlottedTrace_2.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
#         self.plottedTrace_3.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
#         self.voltagePlottedTrace_3.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
        self.traceAdded = False
        self.stopRequested = False
        QtCore.QTimer.singleShot( 0, self.takeLoggingPoint )
        self.loggingActive = True
        self.startTime = time.time()

    def takeLoggingPoint(self):
        value = float(self.meter.read())
        self.trace.x = numpy.append( self.trace.x, time.time()-self.startTime )
        self.trace.y = numpy.append( self.trace.y, value )
        self.trace['voltage'] = numpy.append( self.trace['voltage'], self.meterState.voltage.m_as('V') )
#         self.trace.voltage_2 = numpy.append( self.trace.voltage_2, self.meterState.voltage_2.m_as('V') )
#         self.trace.voltage_3 = numpy.append( self.trace.voltage_3, self.meterState.voltage_3.m_as('V') )
        if not self.traceAdded:
            self.traceui.addTrace( self.plottedTrace, pen=-1)
            self.traceui.addTrace( self.voltagePlottedTrace, pen=0 )
#             self.traceui.addTrace( self.plottedTrace_2, pen=-1)
#             self.traceui.addTrace( self.voltagePlottedTrace_2, pen=0 )
#             self.traceui.addTrace( self.plottedTrace_3, pen=-1)
#             self.traceui.addTrace( self.voltagePlottedTrace_3, pen=0 )
            self.traceAdded = True
        else:
            self.plottedTrace.replot()
            self.voltagePlottedTrace.replot()
#             self.plottedTrace_2.replot()
#             self.voltagePlottedTrace_3.replot()
#             self.plottedTrace_2.replot()
#             self.voltagePlottedTrace_3.replot()
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
        if not self.scanRunning:
            self.scanList = scanList(self.meterState.start, self.meterState.stop, self.meterState.steps, self.meterState.scanType)
            if self.meterState.scanType in [4, 5]:
                index = find_index_nearest(self.scanList, self.meterState.voltage)
                self.scanList = numpy.roll( self.scanList, -index)
            self.currentIndex = 0
            self.trace = TraceCollection()
            self.trace.name = "scan"
#             self.trace.addColumn('current_2')
#             self.trace.addColumn('current_3')
            self.plottedTrace =  PlottedTrace(self.trace, self.plotDict['Scan']['view'], pens.penList )
#             self.plottedTrace_2 =  PlottedTrace(self.trace, self.plotDict['Scan']['view'], yColumn='current_2', penList=pens.penList )
#             self.plottedTrace_3 =  PlottedTrace(self.trace, self.plotDict['Scan']['view'], yColumn='current_3', penList=pens.penList )
            self.plottedTrace.trace.filenamePattern =  self.meterState.filename
#             self.plottedTrace_2.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
#             self.plottedTrace_3.trace.filenameCallback =  partial( self.plottedTrace.traceFilename, self.meterState.filename )           
            self.traceAdded = False
            self.meter.setZeroCheck(False)
#             self.meter_2.setZeroCheck(False)
#             self.meter_3.setZeroCheck(False)
            self.meter.voltageEnable(True)
#             self.meter_2.voltageEnable(True)
#             self.meter_3.voltageEnable(True)
            self.stopRequested = False
            print("startScan")
            self.scanRunning = True
            QtCore.QTimer.singleShot(0, self.initPoint )
    
    def initPoint(self):
        if self.currentIndex<len(self.scanList) and not self.stopRequested:
            self.meter.setVoltage( self.scanList[self.currentIndex] )
            QtCore.QTimer.singleShot(self.meterState.settlingDelay.m_as('ms'), self.takeScanPoint )
        else:
            self.meter.setVoltage( self.meterState.voltage )
            self.finalizeScan()
    
    def takeScanPoint(self):
        value = float(self.meter.read())
        self.trace.x = numpy.append( self.trace.x, self.scanList[self.currentIndex].m_as('V') )
        self.trace.y = numpy.append( self.trace.y, value )
#         self.trace.current_2 = numpy.append( self.trace.current_2, float( self.meter_2.read() ) )
#         self.trace.current_3 = numpy.append( self.trace.current_3, float( self.meter_3.read() )  )
        if not self.traceAdded:
            self.traceui.addTrace( self.plottedTrace, pen=-1)
#             self.traceui.addTrace( self.plottedTrace_2, pen=-1)
#             self.traceui.addTrace( self.plottedTrace_3, pen=-1)
            self.traceAdded = True
        else:
            self.plottedTrace.replot()
#             self.plottedTrace_2.replot()
#             self.plottedTrace_3.replot()
        self.currentIndex += 1
        QtCore.QTimer.singleShot(0, self.initPoint )
    
    def finalizeScan(self):
        self.trace.description["traceFinalized"] = datetime.now(pytz.utc)
        self.trace.save()
        self.scanRunning = False
        
    def onMeasure(self):
        value = float(self.meter.read())
        self.currentLabel.setText(str(value))
        
    def onMeasure_2(self):
        value = float(self.meter_2.read())
        self.currentLabel_2.setText(str(value))
        
    def onMeasure_3(self):
        value = float(self.meter_3.read())
        self.currentLabel_3.setText(str(value))
        
    def onZero(self):
        self.meter.zero()
        
    def onZero_2(self):
        self.meter_2.zero()
        
    def onZero_3(self):
        self.meter_3.zero()
        
    def onValueChanged(self, attr, value):
        setattr( self.meterState, attr, value )
        
    def onStringValueChanged(self, attr, value):
        setattr( self.meterState, attr, str(value) )
        
    def onVoltage(self, value):
        # if not is_Q(value):
        #     value = Q(value)
        self.meter.setVoltage(value)
        self.meterState.voltage = value
        
    def onVoltage_2(self, value):
        if not is_Q(value):
            value = Q(value)
        raw = value.m_as("V")
        self.meter_2.setVoltage(raw)
        self.meterState.voltage_2 = value
        
    def onVoltage_3(self, value):
        if not is_Q(value):
            value = Q(value)
        raw = value.m_as("V")
        self.meter_3.setVoltage(raw)
        self.meterState.voltage_3 = value
        
    def onEnableOutput(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter.voltageEnable(enable)
        self.meterState.voltageEnabled = enable

    def onEnableOutput_2(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter_2.voltageEnable(enable)
        self.meterState.voltageEnabled_2 = enable

    def onEnableOutput_3(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter_3.voltageEnable(enable)
        self.meterState.voltageEnabled_3 = enable
        
    currentLimits = [2.5e-5, 2.5e-4, 2.5e-3, 2.5e-2]
    def onCurrentLimit(self, index):
        limit = self.currentLimits[index]
        self.meter.setCurrentLimit(limit)
        self.meterState.currentLimit = index
        
    def onCurrentLimit_2(self, index):
        limit = self.currentLimits[index]
        self.meter_2.setCurrentLimit(limit)
        self.meterState.currentLimit_2 = index
        
    def onCurrentLimit_3(self, index):
        limit = self.currentLimits[index]
        self.meter_3.setCurrentLimit(limit)
        self.meterState.currentLimit_3 = index
        
    voltageRanges = [10, 50, 500]
    def onVoltageRange(self, index):
        vrange = self.voltageRanges[index]
        self.meter.setVoltageRange( vrange )
        self.meterState.voltageRange = index
        
    def onVoltageRange_2(self, index):
        vrange = self.voltageRanges[index]
        self.meter_2.setVoltageRange( vrange )
        self.meterState.voltageRange_2 = index
        
    def onVoltageRange_3(self, index):
        vrange = self.voltageRanges[index]
        self.meter_3.setVoltageRange( vrange )
        self.meterState.voltageRange_3 = index
        
    def onZeroCheck(self, value):
        enable = value != QtCore.Qt.Checked
        self.meter.setZeroCheck(enable)
        self.meterState.zeroCheck = enable

    def onZeroCheck_2(self, value):
        enable = value != QtCore.Qt.Checked
        self.meter_2.setZeroCheck(enable)
        self.meterState.zeroCheck_2 = enable

    def onZeroCheck_3(self, value):
        enable = value != QtCore.Qt.Checked
        self.meter_3.setZeroCheck(enable)
        self.meterState.zeroCheck_3 = enable

    def onAutoRange(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter.setAutoRange(enable)
        self.meterState.autoRange = enable

    def onAutoRange_2(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter_2.setAutoRange(enable)
        self.meterState.autoRange_2 = enable

    def onAutoRange_3(self, value):
        enable = value == QtCore.Qt.Checked
        self.meter_3.setAutoRange(enable)
        self.meterState.autoRange_3 = enable

    def openInstrument(self):
        self.meterState.instrument = str(self.instrumentEdit.text())
        self.meter.open( self.meterState.instrument )
        self.meter.reset()
        self.writeAll()
 
    def openInstrument_2(self):
        self.meterState.instrument_2 = str(self.instrumentEdit_2.text())
        self.meter_2.open( self.meterState.instrument_2 )
        self.meter_2.reset()
        self.writeAll_2()
 
    def openInstrument_3(self):
        self.meterState.instrument_3 = str(self.instrumentEdit_3.text())
        self.meter_3.open( self.meterState.instrument_3 )
        self.meter_3.reset()
        self.writeAll_3()
 
    def saveConfig(self):
        self.config["PicoampMeterState"] = self.meterState
        
