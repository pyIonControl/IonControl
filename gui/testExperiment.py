# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import functools
import random
from trace import pens

from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic
import numpy

from .AverageViewTable import AverageViewTable
from . import MainWindowWidget
from scan.ScanControl import ScanControl
from fit.FitUi import FitUi
from modules import DataDirectory
from trace.PlottedTrace import PlottedTrace
from trace.TraceCollection import TraceCollection
from trace.Traceui import Traceui

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/testExperiment.ui')
testForm, testBase = PyQt5.uic.loadUiType(uipath)

class test(testForm, MainWindowWidget.MainWindowWidget):
    StatusMessage = QtCore.pyqtSignal( str )
    ClearStatusMessage = QtCore.pyqtSignal()
    experimentName = 'Test Scan'

    def __init__(self,globalVariablesUi, parent=None, measurementLog=None):
        MainWindowWidget.MainWindowWidget.__init__(self, parent)
        testForm.__init__(self)
        self.globalVariablesUi = globalVariablesUi
        self.measurementLog = measurementLog 
#        pyqtgraph.setConfigOption('background', 'w')
#        pyqtgraph.setConfigOption('foreground', 'k')

    def setupUi(self, MainWindow, config):
        testForm.setupUi(self, MainWindow)
        self.config = config
        self.plottedTrace = None
        self._graphicsView = self.graphicsLayout._graphicsView
        self.penicons = pens.penicons().penicons()
        self.traceui = Traceui(self.penicons, self.config, "testExperiment", { "Plot Window": {'view': self._graphicsView}})
        self.traceui.setupUi(self.traceui)
        self.dockWidget.setWidget( self.traceui )
        self.dockWidgetList.append(self.dockWidget)
        self.fitWidget = FitUi(self.traceui, self.config, "testExperiment", globalDict = self.globalVariablesUi.variables )
        self.fitWidget.setupUi(self.fitWidget)
        self.dockWidgetFitUi.setWidget( self.fitWidget )
        self.dockWidgetList.append(self.dockWidgetFitUi )
        self.displayUi = AverageViewTable(self.config)
        self.displayUi.setupUi()
        self.displayDock = QtWidgets.QDockWidget("Average")
        self.displayDock.setObjectName("Average")
        self.displayDock.setWidget( self.displayUi )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.displayDock)
        self.dockWidgetList.append(self.displayDock )
        if 'testWidget.MainWindow.State' in self.config:
            QtWidgets.QMainWindow.restoreState(self, self.config['testWidget.MainWindow.State'])
#start added
        self.scanControlWidget = ScanControl(config, self.globalVariablesUi, self.experimentName)
        self.scanControlWidget.setupUi(self.scanControlWidget)
        self.scanControlUi.setWidget(self.scanControlWidget )
        self.dockWidgetList.append(self.scanControlUi)
#end added
        self.tabifyDockWidget( self.dockWidgetFitUi, self.scanControlUi )

    def addPushDestination(self, name, destination):
#        self.fitWidget.addPushDestination(name, destination)
        pass
        
    def setPulseProgramUi(self, pulseProgramUi):
        self.pulseProgramUi = pulseProgramUi
        self.pulseProgramUi.addExperiment('Sequence')

    def onClear(self):
        self.dockWidget.setShown(True)
        self.StatusMessage.emit("test Clear not implemented")
    
    def onSave(self):
        self.StatusMessage.emit("test Save not implemented")

    def onStart(self):
        self.scanType = self.scanControlWidget.scanRepeatComboBox.currentIndex()
#start added
        if self.scanType == 0:
            self.startScan()
        elif self.scanType == 1:
            self.createAverageScan()
            self.startScan()
#end added
        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect( self.onData )
        self.timer.start(10)
        self.displayUi.onClear()

#start added
    def createAverageScan(self):
        self.averagePlottedTrace = PlottedTrace(TraceCollection(), self._graphicsView, pens.penList)
        self.averagePlottedTrace.trace.name = "test average trace"
        self.averagePlottedTrace.trace.description["comment"] = "average trace comment"
        self.averagePlottedTrace.trace.filenameCallback = functools.partial(self.traceFilename, '')
        self.traceui.addTrace(self.averagePlottedTrace, pen=0)
#end added

    def startScan(self):
        if self.plottedTrace is not None and self.traceui.unplotLastTrace():
            self.plottedTrace.plot(0)
        self.plottedTrace = PlottedTrace(TraceCollection(), self._graphicsView, pens.penList)
        self.xvalue = 0
        self.phase = 0 #random.uniform(0,2*numpy.pi)
        self.plottedTrace.trace.x = numpy.array([self.xvalue])
        c = numpy.sin( self.xvalue + self.phase)**2
        self.plottedTrace.trace.y = numpy.array([random.gauss(c, 0.1)])#c*(1-c))])
        self.plottedTrace.trace.top = numpy.array([0.05])
        self.plottedTrace.trace.bottom = numpy.array([0.05])
        self.plottedTrace.trace.filenameCallback = functools.partial( self.traceFilename, '' )
        if self.scanType == 0:
            self.plottedTrace.trace.name = "test trace"
            self.plottedTrace.trace.description["comment"] = "My Comment"
            self.traceui.addTrace(self.plottedTrace, pen=-1)
#start added
        elif self.scanType == 1:
            self.traceui.addTrace(self.plottedTrace, pen=-1, parentTrace=self.averagePlottedTrace)
            self.plottedTrace.trace.name = "test trace {0}".format(self.averagePlottedTrace.childCount())
            self.plottedTrace.trace.description["comment"] = "My Comment {0}".format(self.averagePlottedTrace.childCount())
#end added

    def onData(self):
        self.xvalue += 0.05
        self.plottedTrace.trace.x = numpy.append( self.plottedTrace.trace.x, self.xvalue )
        c = numpy.sin( self.xvalue + self.phase)**2
        value = random.gauss(c, 0.1)#c*(1-c))
        self.plottedTrace.trace.y = numpy.append( self.plottedTrace.trace.y, value )
        self.plottedTrace.trace.top = numpy.append( self.plottedTrace.trace.top, 0.05)
        self.plottedTrace.trace.bottom = numpy.append( self.plottedTrace.trace.bottom, 0.05)
        self.displayUi.add( [value] )
        self.plottedTrace.replot()
        if self.xvalue > 500:
            if self.scanType == 0:
                self.onStop()
#start added
            elif self.scanType == 1:
                self.averagePlottedTrace.averageChildren()
                self.averagePlottedTrace.plot(7) #average plot is in black
                self.startScan()
#end added
                
    def onStop(self):
        if hasattr(self, 'timer'):
            self.timer.stop()
    
    def onPause(self):
        self.StatusMessage.emit("test Pause not implemented")
     
    def activate(self):
        self.StatusMessage.emit("test active")
        MainWindowWidget.MainWindowWidget.activate(self)
        
    def deactivate(self):
        self.StatusMessage.emit("test not active")
        MainWindowWidget.MainWindowWidget.deactivate(self)
        
    def saveConfig(self):
        self.config['testWidget.MainWindow.State'] = QtWidgets.QMainWindow.saveState(self)
        self.traceui.saveConfig()
        self.fitWidget.saveConfig()
        
    def traceFilename(self, pattern):
        directory = DataDirectory.DataDirectory()
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save file', directory.path())
        return path

    def setGlobalVariablesUi(self, globalVariablesUi ):
        self.globalVariables = globalVariablesUi.variables
        self.globalVariablesChanged = globalVariablesUi.valueChanged
        self.globalVariablesUi = globalVariablesUi
        #self.fitWidget.addPushDestination('Global', globalVariablesUi )
