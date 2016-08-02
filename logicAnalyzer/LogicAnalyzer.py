# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import os
from _functools import partial

import PyQt5.uic
from PyQt5 import QtCore, QtWidgets
from pyqtgraph.graphicsItems.PlotCurveItem import PlotCurveItem
from pyqtgraph.graphicsItems.TextItem import TextItem
from pyqtgraph.graphicsItems.ViewBox import ViewBox

from logicAnalyzer.LogicAnalyzerSignalTableModel import LogicAnalyzerSignalTableModel
from logicAnalyzer.LogicAnalyzerTraceTableModel import LogicAnalyzerTraceTableModel
from modules import dictutil
from modules.AttributeComparisonEquality import AttributeComparisonEquality
from modules.GuiAppearance import restoreGuiState, saveGuiState
from modules.Utility import flatten, unique
from modules.concatenate_iter import concatenate_iter
from modules.enum import enum
from trace.pens import penList
from uiModules.RotatedHeaderView import RotatedHeaderView

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/LogicAnalyzer.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class Settings(AttributeComparisonEquality):
    def __init__(self):
        self.numChannels = 64
        self.numTriggerChannels = 7
        self.numAuxChannels = 10
        self.numGateChannels = 32
        self.height = 0.75
        self.scaling = 0.000020
        self.triggerWidth = 0.0001   # only rising edge counts
        
    def __setstate__(self, state):
        self.__dict__ = state

def bitEvaluate(numChannels, thisval, lastval=None, channelOffset=0, trigger=False):
    offValue = 0 if trigger else -1
    if lastval is None:
        return [(bit+channelOffset, 1 if thisval&(1<<bit) else offValue) for bit in range(numChannels)]
    return [(bit+channelOffset, 0 if thisval&(1<<bit)==lastval&(1<<bit) else 1 if thisval&(1<<bit) else offValue) for bit in range(numChannels)]
   

class LogicAnalyzer(Form, Base ):
    OpStates = enum('stopped', 'running', 'single', 'idle') #added idle in response to exception
    def __init__(self,config,pulserHardware,channelNameData, parent=None):
        Form.__init__(self)
        Base.__init__(self, parent)
        self.state = self.OpStates.idle
        self.config = config
        self.pulserHardware = pulserHardware
        self.settings = Settings() #self.config.get( "LogicAnalyzerSettings", Settings() )
        self.pulserHardware.logicAnalyzerDataAvailable.connect( self.onData )
        self.curveBundle = None
        self.curveTriggerBundle = None
        self.xTrigger = None
        self.yTrigger = None
        self.yTriggerBundle = None
        self.xData = None
        self.yData = None
        self.yDataBundle = None
        self.xAuxData = None
        self.yAuxData = None
        self.yAuxDataBundle = None
        self.curveAuxBundle = None
        self.xGateData = None
        self.yGateData = None
        self.yGateDataBundle = None
        self.curveGateBundle = None
        self.channelNameData = channelNameData
        self.lastEnabledChannels = None
        self.textItems = list()
        self.logicData = None

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.actionRun.triggered.connect( self.onRun )
        self.actionStop.triggered.connect( self.onStop )
        self.actionSingle.triggered.connect( self.onSingle )
        self._graphicsView = self.graphicsLayout._graphicsView
        self.signalTableModel = LogicAnalyzerSignalTableModel(self.config, self.channelNameData)
        self.signalTableView.setModel(self.signalTableModel)
        self.signalTableView.resizeColumnsToContents()
        if 'LogicAnalyzer.State' in self.config:
            self.restoreState(self.config['LogicAnalyzer.State'])
        self.signalTableModel.enableChanged.connect( self.refresh )
        
        self.headerView =  RotatedHeaderView(QtCore.Qt.Horizontal )
        self.traceTableView.setHorizontalHeader( self.headerView )
        self.traceTableModel = LogicAnalyzerTraceTableModel(self.config, self.signalTableModel)
        self.traceTableView.setModel( self.traceTableModel )
        self.traceTableView.resizeColumnsToContents()
        
        self.traceTableView.doubleClicked.connect( self.traceTableModel.setReferenceTimeCell )
        # Context Menu for Table
        self.signalTableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.hideSelectedAction = QtWidgets.QAction( "hide selected", self)
        self.showSelectedAction = QtWidgets.QAction( "show selected", self)
        self.hideSelectedAction.triggered.connect( partial(self.onShow,  False) )
        self.showSelectedAction.triggered.connect( partial(self.onShow,  True) )
        self.signalTableView.addAction( self.hideSelectedAction )
        self.signalTableView.addAction( self.showSelectedAction )
        restoreGuiState( self, self.config.get('LogicAnalyzer.guiState') )
        
    def onShow(self, show, checked):
        rows = sorted(unique([ i.row() for i in self.signalTableView.selectedIndexes() ]))
        if rows:
            for row in rows:
                self.signalTableModel.setData( self.signalTableModel.createIndex(row, 0), QtCore.Qt.Checked if show else QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole )
            self.signalTableModel.dataChanged.emit( self.signalTableModel.createIndex(rows[0], 0), self.signalTableModel.createIndex(rows[-1], 0))
        
    def onData(self, logicData):
        logger = logging.getLogger(__name__)
        logger.debug( str(logicData) )
        logger.debug( "Wordcount: {0}".format(logicData.wordcount))
        self.logicData = logicData
        offset = 0
        if logicData.data:
            self.xData, self.yData = list(zip( *logicData.data ))
            self.xData = [ x * self.settings.scaling for x in self.xData ]  # convert tuple to list
            self.xData.append( logicData.stopMarker * self.settings.scaling )
            self.yDataBundle = [list() for _ in range(self.settings.numChannels)]
            for i in range(self.settings.numChannels):
                if self.signalTableModel.enabledList[i]:
                    for value in self.yData:
                        self.yDataBundle[i].append(offset+self.settings.height if value&(1<<i) else offset )
                    offset += 1
        nextChannel = self.settings.numChannels
        if logicData.auxData:
            self.xAuxData, self.yAuxData = list(zip( *logicData.auxData ))
            self.xAuxData = [ x * self.settings.scaling for x in self.xAuxData ]  # convert tuple to list
            self.xAuxData.append( logicData.stopMarker * self.settings.scaling )
            self.yAuxDataBundle = [list() for _ in range(self.settings.numAuxChannels)]
            for i in range(self.settings.numAuxChannels):
                if self.signalTableModel.enabledList[nextChannel+i]:
                    for value in self.yAuxData:
                        self.yAuxDataBundle[i].append(offset+self.settings.height if value&(1<<i) else offset )
                    offset += 1
        nextChannel += self.settings.numAuxChannels
        if logicData.trigger:
            self.xTrigger, self.yTrigger = list(zip( *logicData.trigger ))
            self.xTrigger = list(flatten([ (x* self.settings.scaling, x* self.settings.scaling+self.settings.triggerWidth)  for x in self.xTrigger ]))  # convert tuple to list
            self.yTrigger = list(flatten([ (y, 0) for y in self.yTrigger ]))
            self.xTrigger.append( logicData.stopMarker * self.settings.scaling )
            self.yTriggerBundle = [list() for _ in range(self.settings.numTriggerChannels)]
            for i in range(self.settings.numTriggerChannels):
                if self.signalTableModel.enabledList[nextChannel+i]:
                    for value in self.yTrigger:
                        self.yTriggerBundle[i].append(offset+self.settings.height if value&(1<<i) else offset )
                    offset += 1
        nextChannel += self.settings.numTriggerChannels
        if logicData.gateData:
            self.xGateData, self.yGateData = list(zip( *logicData.gateData ))
            self.xGateData = [ x * self.settings.scaling for x in self.xGateData ]  # convert tuple to list
            self.xGateData.append( logicData.stopMarker * self.settings.scaling )
            self.yGateDataBundle = [list() for _ in range(self.settings.numGateChannels)]
            for i in range(self.settings.numGateChannels):
                if self.signalTableModel.enabledList[nextChannel+i]:
                    for value in self.yGateData:
                        self.yGateDataBundle[i].append(offset+self.settings.height if value&(1<<i) else offset )
                    offset += 1
        self.plotData()
        if self.state==self.OpStates.single:
            self.setStatusStopped()
        self.evaluateData(logicData)
            
            
    def evaluateData(self, logicData):
        self.pulseData = dict()
        if logicData.data:
            lastval = None
            for clockcycle, value in logicData.data:
                dictutil.getOrInsert(self.pulseData, clockcycle * self.settings.scaling, dict()).update( bitEvaluate(self.settings.numChannels, value, lastval) )
                lastval = value
            self.pulseData[logicData.stopMarker * self.settings.scaling] = dict()
        inext = self.settings.numChannels
        if logicData.auxData:
            lastval = None
            for clockcycle, value in logicData.auxData:
                dictutil.getOrInsert(self.pulseData, clockcycle * self.settings.scaling, dict()).update( bitEvaluate(self.settings.numAuxChannels, value, lastval, inext)  )
                lastval = value
        inext += self.settings.numAuxChannels
        if logicData.trigger:
            lastval = None
            for clockcycle, value in logicData.trigger:
                dictutil.getOrInsert(self.pulseData, clockcycle * self.settings.scaling, dict()).update( bitEvaluate(self.settings.numTriggerChannels, value, lastval, inext, trigger=True) )
                lastval = value
        inext += self.settings.numTriggerChannels
        if logicData.gateData:
            lastval = None
            for clockcycle, value in logicData.gateData:
                dictutil.getOrInsert(self.pulseData, clockcycle * self.settings.scaling, dict()).update( bitEvaluate(self.settings.numGateChannels, value, lastval, inext)  )
                lastval = value
        self.traceTableModel.setPulseData(self.pulseData)
        self.traceTableView.resizeColumnsToContents()
           
    def plotData(self):
        offset = 0
        lastAutoRangeState = self._graphicsView.vb.getState()['autoRange']
        self._graphicsView.disableAutoRange(ViewBox.XYAxes)
        if self.lastEnabledChannels and self.lastEnabledChannels!=self.signalTableModel.enabledList:
            for curve in concatenate_iter(self.curveBundle, self.curveAuxBundle, self.curveTriggerBundle, self.curveGateBundle):
                if curve:
                    self._graphicsView.removeItem(curve)
            self.curveBundle = None
            self.curveAuxBundle = None
            self.curveTriggerBundle = None
            self.curveGateBundle = None
            if self.textItems:
                for item in self.textItems:
                    self._graphicsView.removeItem(item)
        if self.yDataBundle:
            if self.curveBundle is None:
                self.curveBundle = list()
                for i, yData in enumerate(self.yDataBundle):
                    if yData:
                        curve = PlotCurveItem(self.xData, yData, stepMode=True, fillLevel=offset, brush=penList[1][4], pen=penList[1][0]) 
                        self._graphicsView.addItem( curve )
                        self.curveBundle.append( curve )
                        textItem = TextItem( self.signalTableModel.primaryChannelName(i), anchor=(1, 1), color=(0, 0, 0) )
                        textItem.setPos( 0, offset )
                        self._graphicsView.addItem(textItem)
                        self.textItems.append(textItem)
                        offset += 1
                    else:
                        self.curveBundle.append( None )
            else:
                for curve, yData in zip(self.curveBundle, self.yDataBundle):
                    if yData:
                        if curve:
                            curve.setData(x=self.xData, y=yData)
                            
        nextChannel = self.settings.numChannels
        if self.yAuxDataBundle:
            if self.curveAuxBundle is None:
                self.curveAuxBundle = list()
                for i, yAuxData in enumerate(self.yAuxDataBundle):
                    if yAuxData:
                        curve = PlotCurveItem(self.xAuxData, yAuxData, stepMode=True, fillLevel=offset, brush=penList[2][4], pen=penList[2][0])
                        self._graphicsView.addItem( curve )
                        self.curveAuxBundle.append( curve )
                        textItem = TextItem( self.signalTableModel.auxChannelName(i), anchor=(1, 1), color=(0, 0, 0) )
                        textItem.setPos( 0, offset )
                        self._graphicsView.addItem(textItem)
                        self.textItems.append(textItem)
                        offset += 1 
                    else:
                        self.curveAuxBundle.append( None )
                        
            else:
                for curve, yAuxData in zip(self.curveAuxBundle, self.yAuxDataBundle):
                    if yAuxData:
                        if curve:
                            curve.setData(x=self.xAuxData, y=yAuxData)
        nextChannel += self.settings.numAuxChannels
        if self.yTriggerBundle:
            if self.curveTriggerBundle is None:
                self.curveTriggerBundle = list()
                for i, yTrigger in enumerate(self.yTriggerBundle):
                    if yTrigger:
                        curve = PlotCurveItem(self.xTrigger, yTrigger, stepMode=True, fillLevel=offset, brush=penList[3][4], pen=penList[3][0]) 
                        self._graphicsView.addItem( curve )
                        self.curveTriggerBundle.append( curve )
                        textItem = TextItem( self.signalTableModel.triggerChannelName(i), anchor=(1, 1), color=(0, 0, 0) )
                        textItem.setPos( 0, offset )
                        self._graphicsView.addItem(textItem)
                        self.textItems.append(textItem)
                        offset += 1 
                    else:
                        self.curveTriggerBundle.append( None )
                        
            else:
                for curve, yTrigger in zip(self.curveTriggerBundle, self.yTriggerBundle):
                    if yTrigger:
                        if curve:
                            curve.setData(x=self.xTrigger, y=yTrigger)
        nextChannel = self.settings.numTriggerChannels
        if self.yGateDataBundle:
            if self.curveGateBundle is None:
                self.curveGateBundle = list()
                for i, yGateData in enumerate(self.yGateDataBundle):
                    if yGateData:
                        curve = PlotCurveItem(self.xGateData, yGateData, stepMode=True, fillLevel=offset, brush=penList[2][4], pen=penList[2][0])
                        self._graphicsView.addItem( curve )
                        self.curveGateBundle.append( curve )
                        textItem = TextItem( self.signalTableModel.gateChannelName(i), anchor=(1, 1), color=(0, 0, 0) )
                        textItem.setPos( 0, offset )
                        self._graphicsView.addItem(textItem)
                        self.textItems.append(textItem)
                        offset += 1 
                    else:
                        self.curveGateBundle.append( None )
                        
            else:
                for curve, yGateData in zip(self.curveGateBundle, self.yGateDataBundle):
                    if yGateData:
                        if curve:
                            curve.setData(x=self.xGateData, y=yGateData)
        self.lastEnabledChannels = list( self.signalTableModel.enabledList )
        xautorange, yautorange = lastAutoRangeState
        if xautorange:
            self._graphicsView.enableAutoRange(ViewBox.XAxis)
        if yautorange:
            self._graphicsView.enableAutoRange(ViewBox.YAxis)
        self._graphicsView.autoRange()
             
    def refresh(self):
        if self.logicData:
            self.onData(self.logicData)
                
    def onRun(self):
        logger = logging.getLogger(__name__)
        logger.debug("Starting Logic Analyzer")
        self.pulserHardware.enableLogicAnalyzer(True)
        self.setStatusRunning()
        
    def onStop(self):
        logger = logging.getLogger(__name__)
        logger.debug("Stopping Logic Analyzer")
        self.pulserHardware.enableLogicAnalyzer(False)
        self.setStatusStopped()
        
    def onSingle(self):
        logger = logging.getLogger(__name__)
        logger.debug("Logic Analyzer Single Shot")
        self.pulserHardware.enableLogicAnalyzer(False)
        self.pulserHardware.logicAnalyzerTrigger()
        self.setStatusSingle()
        
    def setStatusStopped(self):
        self.state = self.OpStates.idle
        self.statusBar.showMessage("Stopped")
        
    def setStatusRunning(self):
        self.state = self.OpStates.idle
        self.statusBar.showMessage("Running")

    def setStatusSingle(self):
        self.state = self.OpStates.idle
        self.statusBar.showMessage("Single shot")
        
    def saveConfig(self):
        self.config["LogicAnalyzerSettings"] = self.settings
        self.signalTableModel.saveConfig()
        self.config['LogicAnalyzer.State'] = self.saveState()
        self.config['LogicAnalyzer.guiState'] = saveGuiState(self)
    
    def onClose(self):
        pass

    def closeEvent(self, e):
        self.onClose()
        
