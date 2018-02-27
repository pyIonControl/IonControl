# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
Experiment code to scan a parameter that is controlled by the FPGA.

The Pulse Program for each point od the scan, the Pulse Program receives the
address and value of the scanned parameter on its pipe input. It is expected to
echo those on the pipe output followed by the measurement results.
It is expected to send an endlabel (0xffffffff) when finished.

"""
import json
from datetime import datetime, timedelta
import functools
import logging
import time
from pathlib import Path

import itertools

import yaml

from dedicatedCounters.WavemeterInterlock import LockStatus
from modules.InkscapeConversion import addPdfMetaData
from modules.doProfile import doprofile
from persist.StringTable import DataStore
from pygsti_addons.QubitDataSet import QubitDataSet
from trace import Traceui
from trace import NamedTraceui

from trace import pens
import os.path

from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic
import numpy
from pyqtgraph.dockarea import DockArea, Dock
from pyqtgraph.graphicsItems.ViewBox import ViewBox
from pyqtgraph.exporters.ImageExporter import ImageExporter
from pyqtgraph.exporters.SVGExporter import SVGExporter

from trace.PlottedStructure import PlottedStructure
from .AverageViewTable import AverageViewTable
from . import MainWindowWidget
from trace import RawData
from scan.ScanControl import ScanControl
from scan.EvaluationControl import EvaluationControl
from .ScanProgress import ScanProgress
from fit.FitUi import FitUi
from modules import DataDirectory
from modules import enum
from modules import stringutilit
from trace.PlottedTrace import PlottedTrace
from trace.TraceCollection import TraceCollection
from uiModules.CoordinatePlotWidget import CoordinatePlotWidget
from modules import WeakMethod
from modules.SceneToPrint import SceneToPrint
from collections import defaultdict
from gui.ScanMethods import ScanMethodsDict, ScanException, ExternalScanMethod
from gui.ScanGenerators import GeneratorList
from modules.quantity import is_Q, Q
from persist.MeasurementLog import  Measurement, Parameter, Result
from scan.AnalysisControl import AnalysisControl   #@UnresolvedImport
from modules.Utility import join
import pytz

from ProjectConfig.Project import getProject
from copy import copy
from modules import InkscapeConversion
from AWG import AWGDevices

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ScanExperiment.ui')
ScanExperimentForm, ScanExperimentBase = PyQt5.uic.loadUiType(uipath)

ExpectedLoopkup = { 'd': 0, 'u' : 1, '1':0.5, '-1':0.5, 'i':0.5, '-i':0.5 }

FifoDepth = 1020


class ScanExperimentContext(object):
    """This class encapsulates all variables, settings and data of the scan.
    It is used in order to implement the ability to stash and resumea ScanExperiment"""
    def __init__(self):
        self.plottedTraceList = list()
        self.currentIndex = 0
        self.histogramCurveList = list()
        self.currentTimestampTrace = None
        self.histogramList = list()
        self.histogramTrace = None
        self.histogramBuffer = defaultdict( list )
        self.scan = None
        self.otherDataFile = None
        self.evaluation = None
        self.scanMethod = None
        self.startTime = None
        self.rawDataFile = None
        self.globalOverrides = list()
        self.revertGlobalsValues = list()
        self.analysisName = None
        self.qubitData = QubitDataSet()

    def overrideGlobals(self, globalDict):
        self.revertGlobals(globalDict)  # make sure old values were reverted e.g. when calling start on a running scan
        for key, value in self.globalOverrides:
            self.revertGlobalsValues.append((key, globalDict[key]))
            globalDict[key] = value

    def revertGlobals(self, globalDict):
        for key, value in self.revertGlobalsValues:
            globalDict[key] = value
        self.revertGlobalsValues[:] = list()

    @property
    def key(self):
        return hash((self.scan.settingsName, self.currentIndex, len(self.scan.list), self.startTime))

    def __str__(self):
        return "{0} ({1}/{2}) started {3}".format(self.scan.settingsName, self.currentIndex, len(self.scan.list), datetime.fromtimestamp(self.startTime))

class ScanExperiment(ScanExperimentForm, MainWindowWidget.MainWindowWidget):
    StatusMessage = QtCore.pyqtSignal( str )
    ClearStatusMessage = QtCore.pyqtSignal()
    NeedsDDSRewrite = QtCore.pyqtSignal()
    plotsChanged = QtCore.pyqtSignal()
    ppStartSignal = QtCore.pyqtSignal()
    ppStopSignal = QtCore.pyqtSignal()
    OpStates = enum.enum('idle', 'running', 'paused', 'starting', 'stopping', 'interrupted', 'stashing', 'resuming')
    experimentName = 'Scan Sequence'
    statusChanged = QtCore.pyqtSignal( object )
    scanConfigurationListChanged = None
    evaluationConfigurationChanged = None
    analysisConfigurationChanged = None
    evaluatedDataSignal = QtCore.pyqtSignal( dict ) #key is the eval name, val is (x, y)
    allDataSignal = QtCore.pyqtSignal( dict ) #key is the eval name, val is (xlist, ylist)
    stashChanged = QtCore.pyqtSignal(object) # indicates that the size of the stash has changed
    def __init__(self, settings, pulserHardware, globalVariablesUi, experimentName, toolBar=None, parent=None, measurementLog=None, callWhenDoneAdjusting=None,
                 dbConnection=None, preferences=None, interlock=None):
        MainWindowWidget.MainWindowWidget.__init__(self, toolBar=toolBar, parent=parent)
        ScanExperimentForm.__init__(self)
        self.interlock = interlock
        self.deviceSettings = settings
        self.pulserHardware = pulserHardware
        self.context = ScanExperimentContext()
        self.activated = False
        self.experimentName = experimentName
        self.interruptReason = ""
        self.enableParameter = True
        self.enableExternalParameter = False
        self.globalVariables = globalVariablesUi.globalDict
        self.globalVariablesChanged = globalVariablesUi.valueChanged
        self.globalVariablesUi = globalVariablesUi  
        self.scanTargetDict = dict()     
        self.measurementLog = measurementLog 
        self.callWhenDoneAdjusting = callWhenDoneAdjusting
        self.accumulatedTimingViolations = set()
        self.project = getProject()
        self.preferences = preferences #this is really print preferences being handed down to TraceUi to find gnuplot
        self.timestampsEnabled = self.project.isEnabled('software', 'Timestamps')
        self.unsavedTraceCount = 0
        self.stash = list()
        self.dbConnection = dbConnection
        if self.dbConnection:
            self.dataStore = DataStore(self.dbConnection)
            self.dataStore.open_session()
        else:
            self.dataStore = None
        self.pulseProgramIdentifier = None     # will save the hash of the Pulse Program
        self.last_plot_time = time.time()
        if self.interlock:
            self.interlock.subscribe(self.onInterlock, "Scan")
        self.interlockPaused = False

    def onInterlock(self, context, status):
        if status == LockStatus.Locked:
            if self.interlockPaused and self.progressUi.state in [self.OpStates.paused, self.OpStates.interrupted]:
                self.onContinue()
                self.interlockPaused = False
        elif status == LockStatus.Unlocked:
            if self.progressUi.state in [self.OpStates.running]:
                self.interlockPaused = True
                self.onPause()

    def setupUi(self, MainWindow, config):
        logger = logging.getLogger(__name__)
        ScanExperimentForm.setupUi(self, MainWindow)
        self.config = config
        self.area = DockArea()
        self.setCentralWidget(self.area)
        self.plotDict = dict()
        axesType = self.config.get( self.experimentName+'.axesType', defaultdict( lambda: False ))

        self.requiredPlotNames = ["Scan Data", "Histogram", "Timestamps"] if self.timestampsEnabled else ["Scan Data", "Histogram"]
        if self.experimentName+'.plotNames' in self.config:
            plotNames = self.config[self.experimentName+'.plotNames']
            for name in self.requiredPlotNames: #make sure required plots are present
                if name not in plotNames:
                    plotNames.append(name)
        else:
            plotNames = copy(self.requiredPlotNames)
        # initialize all the plot windows we want
        self.createPlotWindows(plotNames, axesType)
        try:
            if self.experimentName+'.pyqtgraph-dockareastate' in self.config:
                self.area.restoreState(self.config[self.experimentName+'.pyqtgraph-dockareastate'])
        except Exception as e: #If an except occurs, we have to completely rebuild the DockArea
            logger.warning("Cannot restore dock state in experiment {0}. Exception occurred: ".format(self.experimentName) + str(e))
            self.area.deleteLater()
            self.area = DockArea()
            self.setCentralWidget(self.area)
            self.plotDict=dict()
            self.createPlotWindows(plotNames, axesType)
        del plotNames #I don't want to leave this list around, as it is not updated and may cause confusion.

        # Traceui
        self.penicons = pens.penicons().penicons()
        self.traceui = Traceui.Traceui(self.penicons, self.config, self.experimentName, self.plotDict, hasMeasurementLog=True, highlightUnsaved=True, preferences=self.preferences)
        self.traceui.setupUi(self.traceui)
        self.measurementLog.addTraceui( 'Scan', self.traceui )
        self.measurementLog.traceuiLookup['Script'] = self.traceui
        self.traceui.model.traceModelDataChanged.connect(self.measurementLog.measurementModel.onTraceModelDataChanged)
        self.measurementLog.measurementModel.measurementModelDataChanged.connect(self.traceui.model.onMeasurementModelDataChanged)
        self.traceui.model.traceRemoved.connect(self.measurementLog.measurementModel.onTraceRemoved)
        self.traceui.openMeasurementLog.connect(self.measurementLog.onOpenMeasurementLog)
        # traceui for timestamps
        if self.timestampsEnabled:
            self.timestampTraceui = Traceui.Traceui(self.penicons, self.config, self.experimentName+"-timestamps", self.plotDict)
            self.timestampTraceui.setupUi(self.timestampTraceui)
            self.timestampTraceuiDock = self.setupAsDockWidget(self.timestampTraceui, "Timestamp traces", QtCore.Qt.LeftDockWidgetArea)

        self.namedTraceui = NamedTraceui.NamedTraceui(self.penicons, self.config, self.experimentName, self.plotDict, hasMeasurementLog=True, highlightUnsaved=True, preferences=self.preferences, plotsChangedSignal=self.plotsChanged)
        self.namedTraceui.setupUi(self.namedTraceui)
        self.measurementLog.addTraceui( 'Scan', self.namedTraceui )
        self.measurementLog.traceuiLookup['Script'] = self.namedTraceui
        self.namedTraceui.model.traceModelDataChanged.connect(self.measurementLog.measurementModel.onTraceModelDataChanged)
        self.measurementLog.measurementModel.measurementModelDataChanged.connect(self.namedTraceui.model.onMeasurementModelDataChanged)
        self.namedTraceui.model.traceRemoved.connect(self.measurementLog.measurementModel.onTraceRemoved)
        self.namedTraceui.openMeasurementLog.connect(self.measurementLog.onOpenMeasurementLog)

        # new fit widget
        self.fitWidget = FitUi(self.traceui, self.config, self.experimentName, globalDict=self.globalVariablesUi.globalDict, namedtraceui=self.namedTraceui)
        self.fitWidget.setupUi(self.fitWidget)
        self.globalVariablesUi.valueChanged.connect( self.fitWidget.evaluate )
        self.fitWidgetDock = self.setupAsDockWidget(self.fitWidget, "Fit", QtCore.Qt.LeftDockWidgetArea,
                                                    stackAbove=self.timestampTraceuiDock if self.timestampsEnabled else None)
        # TraceuiDock
        self.traceuiDock = self.setupAsDockWidget(self.traceui, "Traces", QtCore.Qt.LeftDockWidgetArea, stackAbove=self.fitWidgetDock )
        self.namedTraceuiDock = self.setupAsDockWidget(self.namedTraceui, "Named Traces", QtCore.Qt.LeftDockWidgetArea, stackAbove=self.fitWidgetDock )
        # ScanProgress
        self.progressUi = ScanProgress()
        self.progressUi.setupUi()
        self.stateChanged = self.progressUi.stateChanged
        self.setupAsDockWidget(self.progressUi, "Progress", QtCore.Qt.RightDockWidgetArea)
        # Average View
        self.displayUi = AverageViewTable(self.config)
        self.displayUi.setupUi()
        self.setupAsDockWidget(self.displayUi, "Average", QtCore.Qt.RightDockWidgetArea)
        # Scan Control
        self.scanControlWidget = ScanControl(config, self.globalVariablesUi, self.experimentName)
        self.scanControlWidget.currentScanChanged.connect( self.progressUi.setScanLabel )
        self.scanControlWidget.setupUi(self.scanControlWidget)
        self.scanControlDock = self.setupAsDockWidget(self.scanControlWidget, "Scan Control", QtCore.Qt.RightDockWidgetArea)
        self.scanConfigurationListChanged = self.scanControlWidget.scanConfigurationListChanged
        # EvaluationControl
        self.evaluationControlWidget = EvaluationControl(config, self.globalVariablesUi.globalDict, self.experimentName, list(self.plotDict.keys()),
                                                         analysisNames=self.fitWidget.analysisNames(),
                                                         counterNames=self.pulserHardware.pulserConfiguration().counterBits if self.pulserHardware.pulserConfiguration() else None )
        self.evaluationControlWidget.currentEvaluationChanged.connect( self.progressUi.setEvaluationLabel )
        self.evaluationControlWidget.setupUi(self.evaluationControlWidget)
        self.globalVariablesChanged.connect(self.evaluationControlWidget.evaluate)
        self.fitWidget.analysisNamesChanged.connect( self.evaluationControlWidget.setAnalysisNames )
        self.evaluationControlDock = self.setupAsDockWidget( self.evaluationControlWidget, "Evaluation Control", QtCore.Qt.RightDockWidgetArea, stackAbove=self.scanControlDock)
        self.evaluationConfigurationChanged = self.evaluationControlWidget.evaluationConfigurationChanged
        # Analysis Control
        self.analysisControlWidget = AnalysisControl(config, self.globalVariablesUi.globalDict, self.experimentName, self.evaluationControlWidget.evaluationNames )
        self.analysisControlWidget.currentAnalysisChanged.connect( self.progressUi.setAnalysisLabel )
        self.analysisControlWidget.setupUi(self.analysisControlWidget)
        self.analysisControlDock = self.setupAsDockWidget( self.analysisControlWidget, "Analysis Control", QtCore.Qt.RightDockWidgetArea, stackAbove=self.evaluationControlDock)
        self.globalVariablesUi.valueChanged.connect( self.analysisControlWidget.evaluate )
        self.analysisConfigurationChanged = self.analysisControlWidget.analysisConfigurationChanged

        #toolBar actions
        self.copyHistogram = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/office-chart-bar.png"), "Copy histogram to traces", self )
        self.copyHistogram.setToolTip("Copy histogram to traces")
        self.copyHistogram.triggered.connect( self.onCopyHistogram )
        self.actionList.append( self.copyHistogram )
        
        self.saveHistogram = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/office-chart-bar-save.png"), "Save histograms", self )
        self.saveHistogram.setToolTip("Save histograms for last run to file")
        self.saveHistogram.triggered.connect( self.onSaveHistogram )
        self.actionList.append( self.saveHistogram )

        self.actionAddPlot = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/add-plot.png"), "Add new plot", self)
        self.actionAddPlot.setToolTip("Add new plot")
        self.actionAddPlot.triggered.connect(self.onAddPlot)
        self.actionList.append(self.actionAddPlot)
        
        self.removePlot = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/remove-plot.png"), "Remove a plot", self)
        self.removePlot.setToolTip("Remove a plot")
        self.removePlot.triggered.connect(self.onRemovePlot)
        self.actionList.append(self.removePlot)

        self.renamePlot = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/rename-plot.png"), "Rename a plot", self)
        self.renamePlot.setToolTip("Rename a plot")
        self.renamePlot.triggered.connect(self.onRenamePlot)
        self.actionList.append(self.renamePlot)
        
        self.analysisControlWidget.addPushDestination('Global', self.globalVariablesUi )

    def createPlotWindows(self, plotNames, axesType):
        for name in plotNames:
            dock = Dock(name)
            widget = CoordinatePlotWidget(self, name=name)
            if hasattr(axesType, name):
                widget.setTimeAxis(axesType[name])
            view = widget._graphicsView
            self.area.addDock(dock, "bottom")
            dock.addWidget(widget)
            self.plotDict[name] = {"dock":dock, "widget":widget, "view":view}
            del dock, widget, view #This is probably unnecessary, but can't hurt
        self.plotDict["Histogram"]["widget"].autoRange()
        if self.timestampsEnabled: self.plotDict["Timestamps"]["widget"].autoRange()

    def reAnalyze(self, plottedTrace):
        self.analysisControlWidget.analyze( dict( ( (evaluation.name, plottedTrace) for evaluation, plottedTrace in zip(self.context.evaluation.evalList, self.context.plottedTraceList) ) ) )
        
    def printTargets(self):
        return list(self.plotDict.keys())

    def addPushDestination(self, name, destination):
        self.analysisControlWidget.addPushDestination(name, destination)
        
    def setupAsDockWidget(self, widget, name, area=QtCore.Qt.RightDockWidgetArea, stackAbove=None, stackBelow=None ):
        dock = QtWidgets.QDockWidget(name)
        dock.setObjectName(name)
        dock.setWidget( widget )
        self.addDockWidget(area, dock )
        self.dockWidgetList.append( dock )
        if stackAbove is not None:
            self.tabifyDockWidget( stackAbove, dock )
        elif stackBelow is not None:
            self.tabifyDockWidget( dock, stackBelow )
        return dock           

    def setPulseProgramUi(self, pulseProgramUi):
        self.pulseProgramUi = pulseProgramUi.addExperiment(self.experimentName, self.globalVariables, self.globalVariablesChanged )
        self.scanControlWidget.setVariables( self.pulseProgramUi.pulseProgram.variabledict )
        self.pulseProgramUi.pulseProgramChanged.connect( self.updatePulseProgram )
        self.scanControlWidget.setPulseProgramUi( self.pulseProgramUi )
        
    def updatePulseProgram(self):
        self.scanControlWidget.setVariables( self.pulseProgramUi.pulseProgram.variabledict )
        self.scanControlWidget.setPulseProgramUi( self.pulseProgramUi )

    def onClear(self):
        self.dockWidget.setShown(True)
        self.StatusMessage.emit("test Clear not implemented")
    
    def onSave(self):
        pass
    
    def setTimeLabel(self):
        elapsed = time.time()-self.context.startTime
        expected = elapsed / ((self.context.currentIndex)/float(max(len(self.scan.list), 1))) if self.context.currentIndex>0 else 0
        self.scanControlWidget.timeLabel.setText( "{0} / {1}".format(timedelta(seconds=round(elapsed)),
                                                 timedelta(seconds=round(expected)))) 
 
    def onStart(self, globalOverrides=list()):
        logging.getLogger(__name__).debug("globalOverrides: {0}".format(globalOverrides))
        self.interlockPaused = False
        self.context.globalOverrides = globalOverrides
        self.context.analysisName = self.analysisControlWidget.currentAnalysisName
        self.context.overrideGlobals(self.globalVariables)
        self.accumulatedTimingViolations = set()
        self.pulseProgramUi.setTimingViolations( [] )
        self.context.scan = self.scanControlWidget.getScan()
        self.context.evaluation = self.evaluationControlWidget.getEvaluation()
        self.displayUi.setNames( [evaluation.name for evaluation in self.context.evaluation.evalList ])
        if self.context.scan.scanTarget in ScanMethodsDict:
            self.context.scanMethod = ScanMethodsDict[self.context.scan.scanTarget](self)
        else:
            self.context.scanMethod = ExternalScanMethod(self)
            self.context.scanMethod.name = self.context.scan.scanTarget
        self.progressUi.setStarting()
        self.ppStartSignal.emit()
        if self.callWhenDoneAdjusting is None:
            self.startScan()
        else:
            self.callWhenDoneAdjusting(self.startScan)
        if self.context.scan.saveRawData and self.context.scan.rawFilename:
            self.context.rawDataFile = open(DataDirectory.DataDirectory().sequencefile(self.context.scan.rawFilename)[0], 'w')
        self.context.dataFinalized = False

    def startScan(self):
        logger = logging.getLogger(__name__)
        if self.progressUi.state in [self.OpStates.idle, self.OpStates.starting, self.OpStates.stopping, self.OpStates.running, self.OpStates.paused, self.OpStates.interrupted]:
            self.context.startTime = time.time()
            self.pulserHardware.ppStop()

            for awgName in list(AWGDevices.AWGDeviceDict.keys()): #program any AWG (if necessary)
                if self.project.isEnabled('hardware', awgName):
                    awgDevice = list(self.scanTargetDict[awgName].values())[0].device
                    if awgDevice.settings.deviceSettings['programOnScanStart']:
                        logging.getLogger(__name__).info("Programming {0}".format(awgName))
                        awgDevice.program()

            self.context.PulseProgramBinary = self.pulseProgramUi.getPulseProgramBinary()
            self.context.generator = GeneratorList[self.context.scan.scanMode](self.context.scan)

            if self.dataStore:
                self.pulseProgramIdentifier = self.dataStore.addData(self.pulseProgramUi.pppSource)
            (mycode, data) = self.context.generator.prepare(self.pulseProgramUi, self.context.scanMethod.maxUpdatesToWrite )
            self.context.qubitData = QubitDataSet(**self.context.generator.gateSequenceInfo)
            if self.pulseProgramUi.writeRam and self.pulseProgramUi.ramData:
                data = self.pulseProgramUi.ramData #Overwrites anything set above by the gate sequence ui
            if data:
                logging.getLogger(__name__).info("Writing {0} bytes to RAM ({1}%)".format(len(data)*8, 100*len(data)/(2**24) ))
                self.pulserHardware.ppWriteRamWordList(data, 0, check=True)
                datacopy = [0]*len(data)
                datacopy = [v & 0xffffffffffffffff for v in self.pulserHardware.ppReadRamWordList(datacopy, 0)]
                if data!=datacopy:
                    logger.info("original: {0}".format(data) if len(data)<202 else "original {0} ... {1}".format(data[0:100], data[-100:]) )
                    logger.info("received: {0}".format(datacopy) if len(datacopy)<202 else "received {0} ... {1}".format(datacopy[0:100], datacopy[-100:]) )
                    raise ScanException("Ram write unsuccessful datalength {0} checked length {1}".format(len(data), len(datacopy)))
                if self.context.scan.gateSequenceSettings.debug:
                    with open("debug.bin", 'w') as f:
                        f.write( ' '.join(map(str, data)) )
            self.pulserHardware.ppFlushData()
            self.pulserHardware.ppClearWriteFifo()
            self.pulserHardware.ppUpload(self.context.PulseProgramBinary)
            self.pulserHardware.ppWriteDataBuffered(mycode)
            self.displayUi.onClear()
            self.timestampsNewRun = True
            if self.context.plottedTraceList and self.traceui.unplotLastTrace:
                for plottedTrace in self.context.plottedTraceList:
                    plottedTrace.plot(0) #unplot previous trace
            if self.context.plottedTraceList and self.traceui.collapseLastTrace:
                self.traceui.collapse(self.context.plottedTraceList[0])
            self.context.plottedTraceList = list() #reset plotted trace list
            self.context.otherDataFile = None
            self.context.histogramBuffer = defaultdict( list )
            self.context.scanMethod.startScan()

    def onContinue(self):
        if self.progressUi.is_interrupted:
            logging.getLogger(__name__).info("Received ion reappeared signal, will continue.")
            self.onPause()
    
    def onPause(self):
        logger = logging.getLogger(__name__)
        if self.progressUi.state in [self.OpStates.paused, self.OpStates.interrupted]:
            self.pulserHardware.ppFlushData()
            self.pulserHardware.ppClearWriteFifo()
            self.pulserHardware.ppWriteDataBuffered(self.context.generator.restartCode(self.context.currentIndex))
            logger.info( "Starting" )
            self.pulserHardware.ppStart()
            self.progressUi.resumeRunning(self.context.currentIndex)
            self.timestampsNewRun = False
            logger.info( "continued" )
        elif self.progressUi.is_running:
            self.pulserHardware.ppStop()
            self.progressUi.setPaused()

    def onStash(self):
        """Pause the current run and stash all the variables.
        A stashed run can be interrupted by anythin and resumed"""
        if self.progressUi.is_running:
            self.progressUi.setStashing()
            self.context.scanMethod.onStash()

    def stashSize(self):
        return len(self.stash)

    def onStashBottomHalf(self):
        self.context.progressData = self.progressUi.getData()
        self.stash.append(self.context)
        self.progressUi.setIdle()
        self.stashChanged.emit(self.stash)
        self.context.revertGlobals(self.globalVariables)
        logging.getLogger(__name__).info("Stashed {0}".format(self.context))
        self.context = ScanExperimentContext()

    def onResume(self, index=-1):
        """Resume the stashed run given by index"""
        if self.progressUi.is_idle:
            self.context = self.stash.pop(index)
            self.context.overrideGlobals(self.globalVariables)
            if self.callWhenDoneAdjusting is None:
                self.resumeMiddlePart()
            else:
                self.callWhenDoneAdjusting(self.resumeMiddlePart)

    def resumeMiddlePart(self):
        self.context.scanMethod.resume()

    def resumeBottomHalf(self):
        logger = logging.getLogger(__name__)
        self.pulserHardware.ppFlushData()
        self.pulserHardware.ppClearWriteFifo()
        self.pulserHardware.ppWriteDataBuffered(self.context.generator.restartCode(self.context.currentIndex))
        logger.info( "Resuming" )
        self.pulserHardware.ppStart()
        self.progressUi.setData(self.context.progressData)
        self.progressUi.resumeRunning(self.context.currentIndex)
        self.timestampsNewRun = False
        logger.info("continued")
        self.stashChanged.emit(self.stash)

    def onInterrupt(self, reason):
        self.pulserHardware.ppStop()
        self.progressUi.setInterrupted(reason)       

    def onStop(self, reason='stopped'):
        if self.progressUi.state in [self.OpStates.starting, self.OpStates.running, self.OpStates.paused, self.OpStates.interrupted, self.OpStates.stopping ]:
            try:
                if self.context.scan:
                    self.finalizeData(reason=reason)
            except Exception as e:
                logging.getLogger(__name__).warning("Analysis failed: {0}".format(str(e)))
            self.context.scanMethod.onStop()
            self.pulserHardware.ppStop()
            self.pulserHardware.ppClearWriteFifo()
            self.pulserHardware.ppFlushData()
            self.NeedsDDSRewrite.emit()

    def finalizeStop(self):
        self.context.revertGlobals(self.globalVariables)
        self.ppStopSignal.emit()
        self.progressUi.setIdle()

    def traceFilename(self, pattern):
        directory = DataDirectory.DataDirectory()
        if pattern and pattern!='':
            filename, _ = directory.sequencefile(pattern)
            return filename
        else:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', directory.path())
            return path

    def onData(self, data, queue_size):
        """ Called by worker with new data
        queuesize is the size of waiting messages, dont't do expensive unnecessary stuff if queue is deep
        """
        logger = logging.getLogger(__name__)
        if self.progressUi.is_running or self.progressUi.is_stashing:
            if data.other and self.context.scan.gateSequenceSettings.debug:
                if self.context.otherDataFile is None:
                    dumpFilename, _ = DataDirectory.DataDirectory().sequencefile("other_data.bin")
                    self.context.otherDataFile = open( dumpFilename, "wb" )
                self.context.otherDataFile.write( self.pulserHardware.wordListToBytearray(data.other))
            if data.overrun:
                logger.warning( "Read Pipe Overrun" )
                self.onInterrupt("Read Pipe Overrun")
            if data.timingViolations:
                oldlength = len(self.accumulatedTimingViolations)
                self.accumulatedTimingViolations.update(data.timingViolations)
                if len(self.accumulatedTimingViolations)>oldlength:
                    self.pulseProgramUi.setTimingViolations( [self.pulseProgramUi.lineOfInstruction(l) for l in self.accumulatedTimingViolations])
                    lineInPP = self.pulseProgramUi.lineOfInstruction(data.timingViolations[0])
                    logger.warning( "PP Timing violation at address {0}".format(lineInPP))
            if data.final:
                if data.exitcode == 0x100000000000:  # interrupt
                    self.processData(data, 0)
                    self.onStashBottomHalf()
                elif data.exitcode not in [0, 0xffff]:
                    self.onInterrupt(self.pulseProgramUi.exitcode(data.exitcode))
                else:
                    self.processData(data, 0)
            else:
                self.processData(data, queue_size)
        else:
            logger.info( "pp not running ignoring onData {0} {1} {2}".format( self.context.currentIndex, dict((i, len(data.count[i])) for i in sorted(data.count.keys())), data.scanvalue ) )

    def processData(self, data, queue_size):
        logger = logging.getLogger(__name__)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("onData {0} {1} {2} {3}".format(self.context.currentIndex,
                                                        dict((i, len(data.count[i])) for i in sorted(data.count.keys())),
                                                        data.scanvalue, queue_size))
        x = self.context.generator.xValue(self.context.currentIndex, data)
        if self.context.rawDataFile is not None:
            self.context.rawDataFile.write(data.dataString())
            self.context.rawDataFile.write('\n')
            self.context.rawDataFile.flush()
        self.context.scanMethod.onData(data, queue_size, x)

    def dataMiddlePart(self, data, queue_size, x):
        if is_Q(x):
            x = x.m_as(self.context.scan.xUnit)
        logger = logging.getLogger(__name__)
        evaluated = list()
        replacementDict = dict(iter(list(self.pulseProgramUi.currentContext.parameters.valueView.items())))
        for evaluation, algo in zip(self.context.evaluation.evalList, self.context.evaluation.evalAlgorithmList):
            evaluated.append(algo.evaluate(data, evaluation, ppDict=replacementDict,
                                           globalDict=self.globalVariables))  # returns mean, error, raw
        # qubit evaluation
        gateSequence = self.context.generator.xKey(self.context.currentIndex)
        for evaluation, algo in zip(self.context.evaluation.evalList, self.context.evaluation.evalAlgorithmList):
            if hasattr(algo, 'qubitEvaluate'):
                self.context.qubitData.extend(gateSequence,
                                              evaluation.name, evaluation.settings['color_box_plot'],
                                              *algo.qubitEvaluate(data, evaluation, ppDict=replacementDict,
                                                                  globalDict=self.globalVariables))
            if hasattr(algo, 'detailEvaluate'):
                self.context.qubitData.extendEnv(gateSequence, evaluation.name,
                                                 *algo.detailEvaluate(data, evaluation, ppDict=replacementDict,
                                                                      globalDict=self.globalVariables))
        if len(evaluated) > 0:
            self.displayUi.add([e.value for e in evaluated])
            self.updateMainGraph(x, evaluated, data.timeinterval, queue_size)
            self.showHistogram(data, self.context.evaluation.evalList, self.context.evaluation.evalAlgorithmList)
        if data.other:
            logger.info("Other: {0}".format(data.other))
        self.context.currentIndex += 1
        if self.context.evaluation.enableTimestamps and self.timestampsEnabled:
            self.showTimestamps(data)
        self.context.scanMethod.prepareNextPoint(data)
        names = [self.context.evaluation.ev.name for self.context.evaluation.ev in self.context.evaluation.evalList]
        results = [(x, res.value) for res in evaluated]
        self.evaluatedDataSignal.emit(dict(list(zip(names, results))))

    def preparePlotting(self, x, evaluated, timeinterval):
        traceCollection = TraceCollection(record_timestamps=True)
        traceCollection.recordTimeinterval()
        self.plottedTraceList = list()
        for (index, result), evaluation in zip(enumerate(evaluated), self.context.evaluation.evalList):
            if result is not None:  # result is None if there were no counter results
                error = result.interval
                showerror = error is not None
                yColumnName = evaluation.name
                rawColumnName = '{0}_raw'.format(evaluation.name)
                if showerror:
                    topColumnName = '{0}_top'.format(evaluation.name)
                    bottomColumnName = '{0}_bottom'.format(evaluation.name)
                    plottedTrace = PlottedTrace(traceCollection,
                                                self.plotDict[self.context.evaluation.evalList[index].plotname] if
                                                self.context.evaluation.evalList[index].plotname != 'None' else None,
                                                pens.penList,
                                                xColumn=self.context.evaluation.evalList[index].abszisse.columnName,
                                                yColumn=yColumnName, topColumn=topColumnName,
                                                bottomColumn=bottomColumnName,
                                                rawColumn=rawColumnName,
                                                name=self.context.evaluation.evalList[index].name,
                                                xAxisUnit=self.context.scan.xUnit,
                                                xAxisLabel=self.context.scan.scanParameter,
                                                windowName=self.context.evaluation.evalList[index].plotname,
                                                combinePoints=evaluation.settings['combinePoints'],
                                                averageSameX=evaluation.settings['averageSameX'],
                                                averageType=evaluation.settings['averageType'])
                else:
                    plottedTrace = PlottedTrace(traceCollection,
                                                self.plotDict[self.context.evaluation.evalList[index].plotname] if
                                                self.context.evaluation.evalList[index].plotname != 'None' else None,
                                                pens.penList,
                                                xColumn=self.context.evaluation.evalList[index].abszisse.columnName,
                                                yColumn=yColumnName, rawColumn=rawColumnName,
                                                name=self.context.evaluation.evalList[index].name,
                                                xAxisUnit=self.context.scan.xUnit,
                                                xAxisLabel=self.context.scan.scanParameter,
                                                windowName=self.context.evaluation.evalList[index].plotname,
                                                combinePoints=evaluation.settings['combinePoints'],
                                                averageSameX=evaluation.settings['averageSameX'],
                                                averageType=evaluation.settings['averageType'])
                xRange = self.context.generator.xRange() if is_Q(self.context.scan.start) and Q(1,
                                                                                                self.context.scan.xUnit).dimensionality == self.context.scan.start.dimensionality else None
                if xRange:
                    self.plotDict["Scan Data"]["view"].setXRange(*xRange)
                else:
                    self.plotDict["Scan Data"]["view"].enableAutoRange(axis=ViewBox.XAxis)
                self.context.plottedTraceList.append(plottedTrace)
        if self.context.qubitData:
            traceCollection.structuredData['qubitData'] = self.context.qubitData
            traceCollection.structuredDataFormat['qubitData'] = self.context.scan.qubitDataFormat
            if self.context.qubitData.is_gst:
                plottedStructure = PlottedStructure(traceCollection, 'qubitData', self.plotDict['Qubit'], 'Qubit',
                                                    properties=self.context.scan.gateSequenceSettings.plotProperties.copy())
                self.context.plottedTraceList.append(plottedStructure)
        self.context.plottedTraceList[0].traceCollection.name = self.context.scan.settingsName
        self.context.plottedTraceList[0].traceCollection.description["comment"] = ""
        self.context.plottedTraceList[0].traceCollection.description["PulseProgram"] = self.pulseProgramUi.description()
        self.context.plottedTraceList[0].traceCollection.description["Scan"] = self.context.scan.description()
        self.context.plottedTraceList[0].traceCollection.autoSave = self.context.scan.autoSave
        self.context.plottedTraceList[0].traceCollection.filenamePattern = self.context.scan.filename
        if len(self.context.plottedTraceList) == 1:
            category = None
        elif self.context.scan.autoSave:
            category = self.traceui.getUniqueCategory(self.context.plottedTraceList[0].traceCollection.filename)
        else:
            category = "UNSAVED_" + self.context.plottedTraceList[0].traceCollection.filenamePattern + "_{0}".format(
                self.unsavedTraceCount)
        for plottedTrace in self.context.plottedTraceList:
            plottedTrace.category = category
        if not self.context.scan.autoSave: self.unsavedTraceCount += 1
        self.context.generator.appendData(self.context.plottedTraceList, x, evaluated, timeinterval)
        for index, plottedTrace in reversed(list(enumerate(self.context.plottedTraceList))):
            self.traceui.addTrace(plottedTrace, pen=-1)
        if self.traceui.expandNew:
            self.traceui.expand(self.context.plottedTraceList[0])
        self.traceui.resizeColumnsToContents()

    def updateMainGraph(self, x, evaluated, timeinterval, queue_size): # evaluated is list of mean, error, raw
        if not self.context.plottedTraceList:
            self.preparePlotting(x, evaluated, timeinterval)
        else:
            self.context.generator.appendData(self.context.plottedTraceList, x, evaluated, timeinterval )
            if queue_size < 2 or time.time() - self.last_plot_time > 5:
                for plottedTrace in self.context.plottedTraceList:
                    plottedTrace.replot()
                self.last_plot_time = time.time()

    def finalizeData(self, reason='end of scan'):
        if not self.context.dataFinalized:  # is not yet finalized
            logger = logging.getLogger(__name__)
            logger.info( "finalize Data reason: {0}".format(reason) )
            saveData = reason != 'aborted'
            if self.context.otherDataFile is not None:
                self.context.otherDataFile.close()
                self.context.otherDataFile = None
            if self.context.rawDataFile is not None:
                self.context.rawDataFile.close()
                self.context.rawDataFile = None
                logging.getLogger(__name__).info("Closed raw data file")
            for trace in ([self.context.currentTimestampTrace]+[self.context.plottedTraceList[0].traceCollection] if self.context.plottedTraceList else[]):
                if trace:
                    trace.description["traceFinalized"] = datetime.now(pytz.utc)
                    if trace.autoSave:
                        trace.save()
            if saveData:
                failedList = self.dataAnalysis()
                self.registerMeasurement(failedList)
            if self.context.scan.histogramSave:
                self.onSaveHistogram(self.context.scan.histogramFilename if self.context.scan.histogramFilename else None)
            self.context.dataFinalized = reason
            allData = {self.p.name:(self.p.x, self.p.y) for self.p in self.context.plottedTraceList}
            self.allDataSignal.emit(allData)
        
    def dataAnalysis(self):
        if self.context.analysisName != self.analysisControlWidget.currentAnalysisName:
            self.analysisControlWidget.onLoadAnalysisConfiguration( self.context.analysisName )
        return self.analysisControlWidget.analyze(dict(((evaluation.name, plottedTrace) for evaluation, plottedTrace in zip(self.context.evaluation.evalList, self.context.plottedTraceList))))
                
            
    def showTimestamps(self, data):
        bins = int(self.context.evaluation.roiWidth / self.context.evaluation.binwidth)
        multiplier = self.pulserHardware.timestep.m_as('ms')
        myrange = (self.context.evaluation.roiStart.m_as('ms')/multiplier, (self.context.evaluation.roiStart+self.context.evaluation.roiWidth).m_as('ms')/multiplier)
        y, x = numpy.histogram(list(itertools.chain(*data.timestamp[self.context.evaluation.timestampsKey])),
                               range=myrange,
                               bins=bins)
        x = x[0:-1] * multiplier
                                
        if self.context.currentTimestampTrace and numpy.array_equal(self.context.currentTimestampTrace.x, x) and (
            self.context.evaluation.integrateTimestamps == self.evaluationControlWidget.integrationMode.IntegrateAll or
                (self.context.evaluation.integrateTimestamps == self.evaluationControlWidget.integrationMode.IntegrateRun and not self.timestampsNewRun) ) :
            self.context.currentTimestampTrace.y += y
            self.plottedTimestampTrace.replot()
            if self.context.currentTimestampTrace.rawdata:
                self.context.currentTimestampTrace.rawdata.addInt(itertools.chain(*data.timestamp[self.context.evaluation.timestampsKey]))
        else:    
            self.context.currentTimestampTrace = TraceCollection()
            if self.context.evaluation.saveRawData:
                self.context.currentTimestampTrace.rawdata = RawData()
                self.context.currentTimestampTrace.rawdata.addInt(itertools.chain(data.timestamp[self.context.evaluation.timestampsKey]))
            self.context.currentTimestampTrace.x = x
            self.context.currentTimestampTrace.y = y
            self.context.currentTimestampTrace.name = self.context.scan.settingsName
            self.context.currentTimestampTrace.description["comment"] = ""
            self.context.currentTimestampTrace.filenameCallback = functools.partial( self.traceFilename, "Timestamp_"+self.context.scan.filename )
            self.plottedTimestampTrace = PlottedTrace(self.context.currentTimestampTrace, self.plotDict["Timestamps"], pens.penList, windowName="Timestamps")
            self.timestampTraceui.addTrace(self.plottedTimestampTrace, pen=-1)              
            # pulseProgramHeader = stringutilit.commentarize( self.pulseProgramUi.documentationString() )
            # scanHeader = stringutilit.commentarize( repr(self.context.scan) )
            # self.plottedTimestampTrace.trace.header = '\n'.join((pulseProgramHeader, scanHeader))
        self.timestampsNewRun = False                       
        
    def showHistogram(self, data, evalList, evalAlgoList ):
        index = 0
        for evaluation, algo in zip(evalList, evalAlgoList):
            if evaluation.showHistogram:
                y, x, function = algo.histogram( data, evaluation, self.context.evaluation.histogramBins )
                if self.context.evaluation.integrateHistogram and len(self.context.histogramList)>index:
                    self.context.histogramList[index] = (self.context.histogramList[index][0] + y, self.context.histogramList[index][1], evaluation.name, None )
                elif len(self.context.histogramList)>index:
                    self.context.histogramList[index] = (y, x, evaluation.name, function )
                else:
                    self.context.histogramList.append( (y, x, evaluation.name, function) )
                self.context.histogramBuffer[evaluation.name].append(y)
                index += 1
        numberTraces = index
        del self.context.histogramList[numberTraces:]   # remove elements that are not needed any more
        if not self.context.histogramTrace:
            self.context.histogramTrace = TraceCollection()
        for index, histogram in enumerate(self.context.histogramList):
            if index<len(self.context.histogramCurveList):
                self.context.histogramCurveList[index].x = histogram[1]
                self.context.histogramCurveList[index].y = histogram[0]
                self.context.histogramCurveList[index].fitFunction = histogram[3]
                self.context.histogramCurveList[index].replot()
            else:
                yColumnName = 'y{0}'.format(index) 
                plottedHistogramTrace = PlottedTrace(self.context.histogramTrace, self.plotDict["Histogram"], pens.penList, plotType=PlottedTrace.Types.steps, #@UndefinedVariable
                                                     yColumn=yColumnName, name="Histogram "+(histogram[2] if histogram[2] else ""), windowName="Histogram" )
                self.context.histogramTrace.filenamePattern = "Hist_"+self.context.scan.filename
                plottedHistogramTrace.x = histogram[1]
                plottedHistogramTrace.y = histogram[0]
                plottedHistogramTrace.trace.name = self.context.scan.settingsName
                plottedHistogramTrace.fitFunction = histogram[3]
                self.context.histogramCurveList.append(plottedHistogramTrace)
                plottedHistogramTrace.plot()
        for i in range(numberTraces, len(self.context.histogramCurveList)):
            self.context.histogramCurveList[i].removePlots()
        del self.context.histogramCurveList[numberTraces:]

    def onCopyHistogram(self):
        for plottedtrace in self.context.histogramCurveList:
            self.traceui.addTrace(plottedtrace, pen=-1)   
        self.context.histogramTrace = TraceCollection()
        self.context.histogramCurveList = []
             
    
    def onSaveHistogram(self, filenameTemplate="Histogram.txt"):
        tName, tExtension = os.path.splitext(filenameTemplate) if filenameTemplate else ("Histogram", ".txt")
        for name, histogramlist in list(self.context.histogramBuffer.items()):
            filename = DataDirectory.DataDirectory().sequencefile(tName+"_"+name+tExtension)[0]
            with open(filename, 'w') as f:
                for histogram in histogramlist:
                    f.write( "\t".join(map(str, histogram)))
                    f.write("\n")
    
    def onAddPlot(self):
        name, ok = QtWidgets.QInputDialog.getText(self, 'Plot Name', 'Please enter a plot name: ')
        if ok:
            self.addPlot(name)
            
    def addPlot(self, name):
        if name not in self.plotDict:
            dock = Dock(name)
            widget = CoordinatePlotWidget(self)
            view = widget._graphicsView
            self.area.addDock(dock, "bottom")
            dock.addWidget(widget)
            self.plotDict[name] = {"dock":dock, "widget":widget, "view":view}
            self.evaluationControlWidget.plotnames.append(name)
            self.saveConfig() #In case the program suddenly shuts down
            self.plotsChanged.emit()
        else:
            logging.getLogger(__name__).warning("Plot '{}' already exists.".format(name))

    def onRemovePlot(self):
        names = [name for name in list(self.plotDict.keys()) if name not in self.requiredPlotNames]
        if len(names) > 0:
            name, ok = QtWidgets.QInputDialog.getItem(self, "Select Plot", "Please select which plot to remove: ", names, editable=False)
            if ok:
                self.plotDict[name]["dock"].close()
                self.evaluationControlWidget.plotnames.remove(name)
                del self.plotDict[name]
                for evaluation in self.evaluationControlWidget.settings.evalList: #Change any instance of the removed plot in the current scan evaluation to the default scan ("Scan Data")
                    if evaluation.plotname == name:
                        evaluation.plotname = "Scan Data"
                self.saveConfig() #In case the program suddenly shuts down
        else:
            logging.getLogger(__name__).info("There are no plots which can be removed")
        self.saveConfig()
        self.plotsChanged.emit()

                
    def onRenamePlot(self):
        names = [name for name in list(self.plotDict.keys()) if name not in self.requiredPlotNames]
        if len(names) == 0:
            logging.getLogger(__name__).info("There are no plots which can be renamed")
            return
        name, ok = QtWidgets.QInputDialog.getItem(self, "Select Plot", "Please select which plot to rename: ", names, editable=False)
        if not ok:
            return
        newName, ok = QtWidgets.QInputDialog.getText(self, 'New Plot Name', 'Please enter a new plot name: ')
        if not ok:
            return
        if newName in self.plotDict:
            logging.getLogger(__name__).warning("Plot with name '{}' already exists.")
            return

        self.plotDict[name]["dock"].label.setText(newName)
        self.plotDict[newName] = self.plotDict.pop(name)
        self.evaluationControlWidget.plotnames.append(newName)
        self.evaluationControlWidget.plotnames.remove(name)
        for evaluation in self.evaluationControlWidget.settings.evalList: #Update the current evaluation plot names, whether or not it has been saved
            if evaluation.plotname == name:
                evaluation.plotname = newName
        for settingsName in list(self.evaluationControlWidget.settingsDict.keys()): #Update all the saved evaluation plot names
            for evaluation in self.evaluationControlWidget.settingsDict[settingsName].evalList:
                if evaluation.plotname == name:
                    evaluation.plotname = newName
        self.saveConfig() #In case the program suddenly shuts down
        self.plotsChanged.emit()


    def activate(self):
        logger = logging.getLogger(__name__)
        MainWindowWidget.MainWindowWidget.activate(self)
        if (self.deviceSettings is not None) and (not self.activated):
            try:
                logger.info( "Scan activated" )
                self.pulserHardware.ppFlushData()
                self.pulserHardware.dataAvailable.connect(self.onData)
                self.activated = True
            except Exception as ex:
                logger.exception("activate")
                self.StatusMessage.emit(str(ex))
    
    def deactivate(self):
        logger = logging.getLogger(__name__)
        MainWindowWidget.MainWindowWidget.deactivate(self)
        if self.activated :
            logger.info( "Scan deactivated" )
            self.pulserHardware.dataAvailable.disconnect(self.onData)
            self.activated = False
            self.progressUi.setIdle()
                
    def saveConfig(self):
        self.config[self.experimentName+'.MainWindow.State'] = QtWidgets.QMainWindow.saveState(self)
        self.config[self.experimentName+'.pyqtgraph-dockareastate'] = self.area.saveState()
        self.config[self.experimentName+'.plotNames'] = list(self.plotDict.keys())
        self.config[self.experimentName+".axesType"] = dict( ((key, value["widget"].timeAxis) for key, value in list(self.plotDict.items())) )
        self.scanControlWidget.saveConfig()
        self.evaluationControlWidget.saveConfig()
        self.traceui.saveConfig()
        self.namedTraceui.saveConfig()
        self.displayUi.saveConfig()
        self.fitWidget.saveConfig()
        self.analysisControlWidget.saveConfig()
        
    def onClose(self):
        self.traceui.exitSignal.emit()
        self.namedTraceui.exitSignal.emit()
        self.namedTraceui.onClose()
        if self.dataStore:
            self.dataStore.close_session()

    def state(self):
        return self.progressUi.state
        
    def onPrint(self, target, printer, pdfPrinter, preferences):
        widget = self.plotDict[target]['widget']
        if preferences.savePdf:
            with SceneToPrint(widget):
                painter = QtGui.QPainter(pdfPrinter)
                widget.render( painter )
                del painter
        filenames = set()
        for nodeDict in [self.namedTraceui.model.nodeDict, self.traceui.model.nodeDict]:
            for nname, node in nodeDict.items():
                if isinstance(node.content, PlottedTrace):
                    if node.content.windowName == target:
                        if node.content.isPlotted:
                            if node.content.traceCollection.saved:
                                filenames.add(str(Path(node.content.traceCollection.filename)))
        with SceneToPrint(widget, 1, 1):
            exporter = SVGExporter(widget._graphicsView.scene())
            emfFilename = DataDirectory.DataDirectory().sequencefile(target+".svg")[0]
            exporter.export(fileName=emfFilename)
            InkscapeConversion.addSvgMetaData(emfFilename, filenames)
            if preferences.exportEmf:
                if os.path.exists(preferences.inkscapeExecutable):
                    InkscapeConversion.convertSvgEmf(preferences.inkscapeExecutable, emfFilename)
                else:
                    logging.getLogger(__name__).error("Inkscape executable not found at '{0}'".format(preferences.inkscapeExecutable))
            if preferences.exportWmf:
                if os.path.exists(preferences.inkscapeExecutable):
                    InkscapeConversion.convertSvgWmf(preferences.inkscapeExecutable, emfFilename)
                else:
                    logging.getLogger(__name__).error("Inkscape executable not found at '{0}'".format(preferences.inkscapeExecutable))
            if preferences.exportPdf:
                if os.path.exists(preferences.inkscapeExecutable):
                    InkscapeConversion.convertSvgPdf(preferences.inkscapeExecutable, emfFilename, filenames)
                else:
                    logging.getLogger(__name__).error("Inkscape executable not found at '{0}'".format(preferences.inkscapeExecutable))
        # create an exporter instance, as an argument give it
        # the item you wish to export
        with SceneToPrint(widget, preferences.gridLinewidth, preferences.curveLinewidth):
            exporter = ImageExporter(widget._graphicsView.scene()) 
      
            # set export parameters if needed
            pageWidth = printer.pageRect().width()
            pageHeight = printer.pageRect().height()
            exporter.parameters()['width'] = pageWidth*preferences.printWidth   # (note this also affects height parameter)
            exporter.widthChanged()
              
            # save to file
            png = exporter.export(toBytes=True)
            if preferences.savePng:
                png.save(DataDirectory.DataDirectory().sequencefile(target+".png")[0])
            
            if preferences.doPrint:
                painter = QtGui.QPainter( printer )
                painter.drawImage(QtCore.QPoint(pageWidth*preferences.printX, pageHeight*preferences.printY), png)

    def updateScanTarget(self, target, parameterdict ):
        self.scanTargetDict[target] = parameterdict
        self.scanControlWidget.updateScanTarget(target, list(parameterdict.keys()) )

    def registerMeasurement(self, failedList):
        failedEntry = ", ".join((name for target, name in failedList)) if failedList else None
        startDate = self.context.plottedTraceList[0].traceCollection.description['traceCreation'] if self.context.plottedTraceList else datetime.now(pytz.utc)
        comment = self.context.plottedTraceList[0].trace.comment if self.context.plottedTraceList else None
        filename = self.context.plottedTraceList[0].traceCollection.filename if self.context.plottedTraceList else "none"
        measurement = Measurement(scanType= 'Scan', scanName=self.context.scan.settingsName, scanParameter=self.context.scan.scanParameter, scanTarget=self.context.scan.scanTarget,
                                  scanPP = self.context.scan.loadPPName,
                                  evaluation=self.context.evaluation.settingsName,
                                  startDate=startDate,
                                  duration=None, filename=filename,
                                  comment=comment, longComment=None, failedAnalysis=failedEntry)
        # add parameters
        space = self.measurementLog.container.getSpace('PulseProgram')
        if self.pulseProgramIdentifier:
            measurement.parameters.append(Parameter(name='identifier', value=0, definition=self.pulseProgramIdentifier, space=space))
        for var in list(self.pulseProgramUi.variableTableModel.variabledict.values()):
            measurement.parameters.append(Parameter(name=var.name, value=var.outValue(), definition=var.strvalue, space=space))
        space = self.measurementLog.container.getSpace('GlobalVariables')
        for name, value in list(self.globalVariables.items()):
            measurement.parameters.append( Parameter(name=name, value=value, space=space) )
        
        for targetname, target in list(self.scanTargetDict.items()):
            space = self.measurementLog.container.getSpace(targetname)
            for obj in list(target.values()):
                measurement.parameters.append( Parameter(name=obj.name, value=obj.value, definition=obj.strValue if hasattr(obj, 'strValue') else None, space=space) )
        # add results
        for evaluationElement in self.analysisControlWidget.analysisDefinition:
            fit = evaluationElement.fitfunction.fitfunction()
            for name, value, confidence in zip( fit.parameterNames, fit.parameters, fit.parametersConfidence ):
                fullName = join( '_', [evaluationElement.name, name] )
                measurement.results.append( Result(name=fullName, value=value, bottom=confidence, top=confidence))
            for result in list(fit.results.values()):
                fullName = join( '_', [evaluationElement.name, result.name] )
                measurement.results.append( Result(name=fullName, value=result.value))
            for pushvar in list(evaluationElement.pushVariables.values()):
                fullName = join( '_', [evaluationElement.name, pushvar.variableName] )
                measurement.results.append( Result(name=fullName, value=pushvar.value, bottom=pushvar.minimum if pushvar.minimum else None,
                                                                                       top=pushvar.maximum if pushvar.maximum else None))   
        # add Plots
        measurement.plottedTraceList = self.context.plottedTraceList
        self.measurementLog.container.addMeasurement( measurement )
            
                