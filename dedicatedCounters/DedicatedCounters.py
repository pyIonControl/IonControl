# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
DedicatedCounters reads and displays the counts from the simple counters and ADCs.
"""
import logging
import os
from time import time

import PyQt5
import numpy
from PyQt5 import QtCore, QtWidgets, QtGui
from pyqtgraph.dockarea import Dock, DockArea

from dedicatedCounters import AutoLoad
from dedicatedCounters import DedicatedCountersSettings
from dedicatedCounters import DedicatedDisplay
from dedicatedCounters import InputCalibrationUi
from dedicatedCounters.StatusDisplay import StatusDisplay
from modules import enum
from modules.DataDirectory import DataDirectory
from modules.RollingUpdate import rollingUpdate
from modules.SequenceDict import SequenceDict
from modules.quantity import is_Q
from trace.PlottedTrace import PlottedTrace
from trace.TraceCollection import TraceCollection
from trace.pens import penList, penArgList
from uiModules.BlockAutoRange import BlockAutoRange
from uiModules.DateTimePlotWidget import DateTimePlotWidget
from uiModules.RemoteCustomPlot import RemoteCustomView
from persist.Timeseries import TimeseriesPersist

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/DedicatedCounters.ui')
DedicatedCountersForm, DedicatedCountersBase = PyQt5.uic.loadUiType(uipath)

#curvecolors = [ 'b', 'g', 'r', 'b', 'c', 'm', 'y', 'g' ]

class Settings:
    pass

class DedicatedCounters(DedicatedCountersForm, DedicatedCountersBase ):
    dataAvailable = QtCore.pyqtSignal( object )
    OpStates = enum.enum('idle', 'running', 'paused')

    def __init__(self, config, dbConnection, pulserHardware, globalVariablesUi, shutterUi, externalInstrumentObservable,
                 interlock, parent=None, remoteRender=False):
        self.interlock = interlock
        self.remoteRender = remoteRender
        DedicatedCountersForm.__init__(self)
        DedicatedCountersBase.__init__(self, parent)
        self.curvesDict = {}
        self.dataSlotConnected = False
        self.config = config
        self.configName = 'DedicatedCounter'
        self.pulserHardware = pulserHardware
        self.state = self.OpStates.idle
        self.xData = [numpy.array([])]*20
        self.yData = [numpy.array([])]*20
        self.refValue = [None] * 20
        self.integrationTime = 0
        self.integrationTimeLookup = dict()
        self.tick = 0
        self.analogCalbrations = None
        self.globalVariablesUi = globalVariablesUi
        self.shutterUi = shutterUi
        self.externalInstrumentObservable = externalInstrumentObservable
        self.dbConnection = dbConnection
        self.plotDict = dict()
        self.lastPlotTime = 0
        self.area = None
        self.enableDataPlotting = False
        self.enableTimeseries = False
        self.enableDataTaking = False
#        [
#            AnalogInputCalibration.PowerDetectorCalibration(),
#            AnalogInputCalibration.PowerDetectorCalibrationTwo(),
#            AnalogInputCalibration.AnalogInputCalibration(),
#            AnalogInputCalibration.AnalogInputCalibration() ]

    @property
    def settings(self):
        return self.settingsUi.settings

    def setupUi(self, parent):
        DedicatedCountersForm.setupUi(self, parent)
        self.setupPlots()
        self.actionSave.triggered.connect( self.onSave )
        self.actionClear.triggered.connect( self.onClear )
        self.actionData_Reporting.triggered.connect(self.onEnableDataTaking)
        self.actionPlot_Data.triggered.connect(self.onEnableDataPlotting)
        self.actionTimeseries.triggered.connect(self.onEnableTimeseries)
        self.settingsUi = DedicatedCountersSettings.DedicatedCountersSettings(self.config,self.plotDict)
        self.settingsUi.setupUi(self.settingsUi)
        self.settingsDock.setWidget( self.settingsUi )
        self.settingsUi.valueChanged.connect( self.onSettingsChanged )

        #Plot buttons
        self.addPlot = QtGui.QAction( QtGui.QIcon(":/openicon/icons/add-plot.png"), "Add new plot", self)
        self.addPlot.setToolTip("Add new plot")
        self.addPlot.triggered.connect(self.onAddPlot)
        self.toolBar.addAction(self.addPlot)

        self.removePlot = QtGui.QAction( QtGui.QIcon(":/openicon/icons/remove-plot.png"), "Remove a plot", self)
        self.removePlot.setToolTip("Remove a plot")
        self.removePlot.triggered.connect(self.onRemovePlot)
        self.toolBar.addAction(self.removePlot)

        self.renamePlot = QtGui.QAction( QtGui.QIcon(":/openicon/icons/rename-plot.png"), "Rename a plot", self)
        self.renamePlot.setToolTip("Rename a plot")
        self.renamePlot.triggered.connect(self.onRenamePlot)
        self.toolBar.addAction(self.renamePlot)

        # Input Calibrations        
        self.calibrationUi = InputCalibrationUi.InputCalibrationUi(self.config, 4)
        self.calibrationUi.setupUi(self.calibrationUi)
        self.calibrationDock = QtWidgets.QDockWidget("Input Calibration")
        self.calibrationDock.setObjectName("Input Calibration")
        self.calibrationDock.setWidget( self.calibrationUi )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.calibrationDock)
        self.analogCalbrations = self.calibrationUi.calibrations

        # Display Channels 0-3
        self.displayUi = DedicatedDisplay.DedicatedDisplay(self.config, "Channel 0-3")
        self.displayUi.setupUi(self.displayUi)
        self.displayDock = QtWidgets.QDockWidget("Channel 0-3")
        self.displayDock.setObjectName("Channel 0-3")
        self.displayDock.setWidget( self.displayUi )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.displayDock)

        # Display Channel 4-7
        self.displayUi2 = DedicatedDisplay.DedicatedDisplay(self.config, "Channel 4-7")
        self.displayUi2.setupUi(self.displayUi2)
        self.displayDock2 = QtWidgets.QDockWidget("Channel 4-7")
        self.displayDock2.setObjectName("Channel 4-7")
        self.displayDock2.setWidget(self.displayUi2)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.displayDock2)

        # Display ADC 0-3
        self.displayUiADC = DedicatedDisplay.DedicatedDisplay(self.config, "Analog Channels")
        self.displayUiADC.setupUi(self.displayUiADC)
        self.displayDockADC = QtWidgets.QDockWidget("Analog Channels")
        self.displayDockADC.setObjectName("Analog Channels")
        self.displayDockADC.setWidget(self.displayUiADC)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.displayDockADC)

        # Arrange the dock widgets
        self.tabifyDockWidget( self.displayDockADC, self.displayDock2)
        self.tabifyDockWidget( self.displayDock2, self.displayDock )
        self.tabifyDockWidget( self.calibrationDock, self.settingsDock )
        self.calibrationDock.hide()        

        # AutoLoad
        self.autoLoad = AutoLoad.AutoLoad(self.config, self.dbConnection, self.pulserHardware, self.dataAvailable,
                                          self.globalVariablesUi,self.shutterUi, self.externalInstrumentObservable,
                                          self.interlock)
        self.autoLoad.setupUi(self.autoLoad)
        self.autoLoadDock = QtWidgets.QDockWidget("Auto Loader")
        self.autoLoadDock.setObjectName("Auto Loader")
        self.autoLoadDock.setWidget( self.autoLoad )
        self.autoLoad.valueChanged.connect( self.onSettingsChanged )
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.autoLoadDock)

        # external Status display
        self.statusDisplay = StatusDisplay(self.config, self.pulserHardware.pulserConfiguration())
        self.statusDisplay.setupUi(self.statusDisplay)
        self.statusDock = QtWidgets.QDockWidget("Status display")
        self.statusDock.setObjectName("Status display")
        self.statusDock.setWidget( self.statusDisplay )
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.statusDock)

        if self.configName+'.MainWindow.State' in self.config:
            QtGui.QMainWindow.restoreState(self,self.config[self.configName+'.MainWindow.State'])
        self.onSettingsChanged()

    def onSettingsChanged(self):
        self.integrationTimeLookup[ self.pulserHardware.getIntegrationTimeBinary(self.settings.integrationTime) & 0xffffff] = self.settings.integrationTime
        self.pulserHardware.integrationTime = self.settings.integrationTime
        self.autoLoadCounterMask = self.autoLoad.settings.counterMask
        self.plotCounterMask = self.settingsUi.settings.counterMask
        self.counterDisplayData = self.autoLoad.settings.counterDisplayData
        self.plotDisplayData = self.settingsUi.settings.plotDisplayData
        self.countDict = self.settingsUi.settings.counterDict
        self.adcDict = self.settingsUi.settings.adcDict
        if self.state == self.OpStates.running:
            mask = 0
            mask += self.autoLoadCounterMask | self.plotCounterMask
            self.pulserHardware.counterMask = mask
            self.pulserHardware.adcMask = self.settings.adcMask
            for windowName, dataSourceNames in self.plotDisplayData.items():
                if windowName in self.plotDict:
                    self.curvesDict.setdefault(windowName, dict())
                    counterIndexList = [self.countDict[n] for n in dataSourceNames if n in self.countDict]
                    adcIndexList = [self.adcDict[n] for n in dataSourceNames if n in self.adcDict]
                    mycurves = self.curvesDict[windowName]
                    for cIdx in counterIndexList:
                        mycurves.setdefault(cIdx, self.plotDict[windowName]['view'].plot(pen=penArgList[cIdx + 1]))
                    for aIdx in adcIndexList:
                        mycurves.setdefault(aIdx + 16, self.plotDict[windowName]['view'].plot(pen=penArgList[aIdx + 1]))
                    for eIdx in set(mycurves) - set(counterIndexList) - set(i + 16 for i in adcIndexList):
                        curve = mycurves.pop(eIdx)
                        self.plotDict[windowName]['view'].removeItem(curve)
                        self.xData[eIdx] = numpy.array([])
                        self.yData[eIdx] = numpy.array([])

    def saveConfig(self):
        self.config[self.configName+'.pos'] = self.pos()
        self.config[self.configName+'.size'] = self.size()
        self.config[self.configName+'.Settings'] = self.settings
        self.config[self.configName+'.MainWindow.State'] = QtWidgets.QMainWindow.saveState(self)
        self.config[self.configName+'.PlotNames'] = list(self.plotDict.keys())
        self.displayUi.saveConfig()
        self.displayUi2.saveConfig()
        self.displayUiADC.saveConfig()
        self.autoLoad.saveConfig()
        self.calibrationUi.saveConfig()
        self.settingsUi.saveConfig()
        self.statusDisplay.saveConfig()

    def onClose(self):
        self.autoLoad.onClose()

    def closeEvent(self, e):
        self.onClose()
        
    def reject(self):
        self.config[self.configName+'.pos'] = self.pos()
        self.config[self.configName+'.size'] = self.size()
        self.pulserHardware.dedicatedDataAvailable.disconnect( self.onData )
        self.hide()
        
    def show(self):
        if self.configName+'.pos' in self.config:
            self.move(self.config[self.configName+'.pos'])
        if self.configName+'.size' in self.config:
            self.resize(self.config[self.configName+'.size'])
        super(DedicatedCounters,self).show()
        if not self.dataSlotConnected:
            self.pulserHardware.dedicatedDataAvailable.connect( self.onData )
            self.dataSlotConnected = True
        
    def onEnableDataTaking(self, checked):
        self.enableDataTaking = checked
        if checked:
            self.pulserHardware.counterMask = self.settings.counterMask
            self.pulserHardware.adcMask = self.settings.adcMask
            self.state = self.OpStates.running
            self.onSettingsChanged()
        else:
            self.pulserHardware.counterMask = 0
            self.pulserHardware.adcMask = 0
            self.state = self.OpStates.idle
            self.onSettingsChanged()
        if self.actionData_Reporting.isChecked() != checked:
            self.actionData_Reporting.setChecked(checked)

    def onEnableDataPlotting(self, checked):
        self.enableDataPlotting = checked
        if self.actionPlot_Data.isChecked() != checked:
            self.actionPlot_Data.setChecked(checked)

    def onEnableTimeseries(self, checked):
        if checked:
            self.timeseries = TimeseriesPersist()
            checked = self.timeseries.initDB()
        else:
            self.timeseries = None
        self.enableTimeseries = checked
        if self.actionTimeseries.isChecked() != checked:
            self.actionTimeseries.setChecked(checked)

    def onSave(self):
        logger = logging.getLogger(__name__)
        self.plotDisplayData = self.settingsUi.settings.plotDisplayData
        for plotName in self.plotDisplayData.keys():
            for n in range(20):
                if len(self.xData[n])>0 and len(self.yData[n])>0:
                    trace = TraceCollection()
                    trace.x = self.xData[n]
                    trace.y = self.yData[n]
                    if n < 16:
                        trace.description["counter"] = str(plotName)
                    else:
                        trace.description["ADC"] = str(plotName)
                    filename, _ = DataDirectory().sequencefile("DedicatedCounter_{0}.txt".format(n))
                    trace.addPlotting(PlottedTrace(Trace=trace, name="Counter {0}".format(n)))
                    trace.save()
        logger.info("saving dedicated counters")
    
    def onClear(self):
        self.xData = [numpy.array([])]*20
        self.yData = [numpy.array([])]*20
        self.tick = 0
        for name, subdict in self.curvesDict.items():
            for n in list(subdict.keys()):
                subdict[n].setData(self.xData[n], self.yData[n])

    def onData(self, data, queueSize):
        if self.enableDataTaking:
            self.tick += 1
            self.dataIntegrationTime = self.settings.integrationTime
            data.integrationTime = self.dataIntegrationTime
            self.displayUiADC.values = self.convertAnalog(data.analog())
            data.analogValues = self.displayUiADC.values
            self.displayUi.values = data.data[0:4]
            self.displayUi2.values = data.data[4:8]
            self.statusDisplay.setData(data)
            if self.enableDataPlotting:
                self.plotData(data, queueSize)
            if self.enableTimeseries:
                self.storeData(data, queueSize)
            self.dataAvailable.emit(data)

    def analogValue(self, myindex, value):
        refValue = self.refValue[myindex]
        if is_Q(value):
            if refValue is not None and refValue.dimensionality == value.dimensionality:
                y = value.m_as(refValue)
            else:
                self.refValue[myindex] = value
                y = value.m
        else:
            y = value
        return y

    def plotData(self, data, queueSize):
        self.plotDisplayData = self.settingsUi.settings.plotDisplayData
        msIntegrationTime = self.dataIntegrationTime.m_as('ms')
        for index, value in enumerate(data.data[:16]):
            if value is not None:
                y = self.settings.displayUnit.convert(value, msIntegrationTime)
                self.yData[index] = rollingUpdate(self.yData[index], y, self.settings.pointsToKeep)
                self.xData[index] = rollingUpdate(self.xData[index], data.timestamp, self.settings.pointsToKeep)
        for index, value in enumerate(data.analogValues):
            if value is not None:
                myindex = 16 + index
                self.yData[myindex] = rollingUpdate(self.yData[myindex], self.analogValue(myindex, value), self.settings.pointsToKeep)
                self.xData[myindex] = rollingUpdate(self.xData[myindex], data.timestamp, self.settings.pointsToKeep)
        lag = time() - self.lastPlotTime
        if queueSize < 2 or (queueSize < 20 and lag > 1) or lag > 2:
            self.replot()

    def storeData(self, data, queueSize):
        if self.timeseries is None or not self.timeseries.active:
            return
        if not self.timeseries.initialized:
            self.timeseries.initDB()
        fields = {'count{}'.format(index): float(value) for index, value in enumerate(data.data[:16]) if value is not None}
        fields.update({'analog{}'.format(index): float(self.analogValue(index+16, value)) for index, value in enumerate(data.analogValues) if value is not None})
        fields['integrationtime'] = float(self.dataIntegrationTime.m_as('ms'))
        TimeseriesPersist.store.write_points([{
            "measurement": "dedicated",
            "tags": {
                "project": self.timeseries.projectName,
            },
            "fields": fields,
            "time": data.timestamp if data.timestamp > 1000000000000000000 else int(data.timestamp * 1000000000)
        }])

    def replot(self):
        for name, plotwin in self.curvesDict.items():
            if plotwin:
                with BlockAutoRange(next(iter(plotwin.values()))):
                    for index, plotdata in plotwin.items():
                        plotdata.setData(self.xData[index], self.yData[index])
        self.lastPlotTime = time()

    def convertAnalog(self, data):
        converted = list()
        for channel, cal in enumerate(self.analogCalbrations):
            converted.append( cal.convertMagnitude(data[channel]) )
        return converted

    def setupPlots(self):
        self.area = DockArea()
        self.setCentralWidget(self.area)
        self.plotDict = SequenceDict()
        # initialize all the plot windows we want
        plotNames = self.config.get(self.configName+'.PlotNames', ['Plot'])
        if len(plotNames) < 1:
            plotNames.append('Plot')
        if 'Autoload' not in plotNames:
            plotNames.append('Autoload')
        for name in plotNames:
            dock = Dock(name)
            if self.remoteRender:
                widget = RemoteCustomView()
                widget.pg.setConfigOptions(antialias=True)  ## prettier plots at no cost to the main process!
                rplt = widget.cp.CustomPlotItem(dateAxis=True, name=name)
                rplt._setProxyOptions(deferGetattr=True)  ## speeds up access to rplt.plot
                widget.setCentralItem(rplt)
                dock.addWidget(widget)
                self.plotDict[name] = {"dock":dock, "widget":widget, "view":rplt}
            else:
                widget = DateTimePlotWidget(self, name=name)
                view = widget._graphicsView
                self.area.addDock(dock, "bottom")
                dock.addWidget(widget)
                self.plotDict[name] = {"dock":dock, "widget":widget, "view":view}

    def onAddPlot(self):
        name, ok = QtGui.QInputDialog.getText(self, 'Plot Name', 'Please enter a plot name: ')
        if ok and name!= 'Autoload':
            name = str(name)
            dock = Dock(name)
            widget = DateTimePlotWidget(self)
            view = widget._graphicsView
            self.area.addDock(dock, "bottom")
            dock.addWidget(widget)
            self.plotDict[name] = {"dock":dock, "widget":widget, "view":view}

    def onRemovePlot(self):
        self.editablePlots = {}
        self.editablePlots.update(self.plotDict)
        if 'Autoload' in self.editablePlots:
            self.editablePlots.pop('Autoload')
        logger = logging.getLogger(__name__)
        if len(self.plotDict) > 0:
            name, ok = QtGui.QInputDialog.getItem(self, "Select Plot", "Please select which plot to remove: ", self.editablePlots.keys(), editable=False)
            if ok and name != 'Autoload':
                if ok:
                    name = str(name)
                    self.plotDict[name]["dock"].close()
                    del self.plotDict[name]
        else:
            logger.info("There are no plots which can be removed")

    def onRenamePlot(self):
        self.plotDisplayData = self.settingsUi.settings.plotDisplayData
        self.editablePlots = {}
        self.editablePlots.update(self.plotDict)
        if 'Autoload' in self.editablePlots:
            self.editablePlots.pop('Autoload')
        logger = logging.getLogger(__name__)
        if len(self.plotDict) > 0:
            name, ok = QtGui.QInputDialog.getItem(self, "Select Plot", "Please select which plot to rename: ", self.editablePlots.keys(), editable=False)
            if ok and name != 'Autoload':
                newName, newOk = QtGui.QInputDialog.getText(self, 'New Plot Name', 'Please enter a new plot name: ')
                if newOk and newName != 'Autoload':
                    name = str(name)
                    newName = str(newName)
                    self.plotDict[name]["dock"].label.setText(QtCore.QString(newName))
                    self.plotDict[newName] = self.plotDict[name]
                    for plotName in list(self.plotDisplayData.keys()):
                        plotString = str(plotName)
                        if name == plotString:
                            plotIndex = self.plotDisplayData.index(plotName)
                            self.plotDisplayData.renameAt(plotIndex, newName)
                    del self.plotDict[name]
                    self.onSettingsChanged()
        else:
            logger.info("There are no plots which can be renamed")
