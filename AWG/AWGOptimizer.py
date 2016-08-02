"""
Created on 11 Dec 2015 at 10:34 AM

author: jmizrahi
"""

import PyQt5.uic
from PyQt5 import QtCore, QtGui
from .AWGDevices import DummyAWG
from .AWGUi import AWGUi
import sys
import os
from ProjectConfig.Project import Project
from persist import configshelve
from trace import Traceui, pens
from pyqtgraph.dockarea import DockArea, Dock
from uiModules.CoordinatePlotWidget import CoordinatePlotWidget
from modules.GuiAppearance import saveGuiState, restoreGuiState

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/AWGOptimizer.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class AWGOptimizer(Form, Base):
    def __init__(self, deviceClass, config, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        Form.setupUi(self, self)
        self.config = config
        self.configname = "AWGOptimizer"
        self.setWindowTitle("AWG Optimizer")
        guiState = self.config.get(self.configname+".guiState")
        state = self.config.get(self.configname+'.state')
        pos = self.config.get(self.configname+'.pos')
        size = self.config.get(self.configname+'.size')
        isMaximized = self.config.get(self.configname+'.isMaximized')
        restoreGuiState(self, self.config.get(self.configname+".guiState"))
        if state: self.restoreState(state)
        if pos: self.move(pos)
        if size: self.resize(size)
        if isMaximized: self.showMaximized()

        self.show()
        self.awgUi = AWGUi(deviceClass, config, dict())
        self.awgUi.setupUi(self.awgUi)
        self.splitter.insertWidget(1, self.awgUi)

        #oscilloscope plot window
        name = "Oscilloscope Trace"
        self.scopeDock = Dock(name)
        self.scopePlot = CoordinatePlotWidget(self, name=name)
        self.scopeView = self.scopePlot._graphicsView
        self.scopeDock.addWidget(self.scopePlot)
        self.area = DockArea()
        self.area.addDock(self.scopeDock)
        self.plotDict ={name: {"dock":self.scopeDock, "widget":self.scopePlot, "view":self.scopeView}}
        self.verticalLayout.insertWidget(0, self.area)

        #trace ui
        self.penicons = pens.penicons().penicons()
        self.traceui = Traceui.Traceui(self.penicons, self.config, self.configname, self.plotDict, hasMeasurementLog=False, highlightUnsaved=False)
        self.traceui.setupUi(self.traceui)
        traceDock = Dock("Traces")
        traceDock.addWidget(self.traceui)
        self.area.addDock(traceDock, 'left')
        self.device = self.awgUi.device

        self.measureWaveformButton.clicked.connect(self.onMeasureWaveform)
        self.optimizeButton.clicked.connect(self.onOptimize)

        dockAreaState = self.config.get(self.configname+'.dockAreaState')
        try:
            if dockAreaState: self.area.restoreState(dockAreaState)
        except Exception as e:
            print(e)

    def saveConfig(self):
        self.config[self.configname+".guiState"] = saveGuiState(self)
        self.config[self.configname+'.state'] = self.saveState()
        self.config[self.configname+'.pos'] = self.pos()
        self.config[self.configname+'.size'] = self.size()
        self.config[self.configname+'.isMaximized'] = self.isMaximized()
        self.config[self.configname+'.dockAreaState'] = self.area.saveState()
        self.awgUi.saveConfig()

    def closeEvent(self, e):
        self.saveConfig()

    def onMeasureWaveform(self):
        pass

    def onOptimize(self):
        pass

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    project = Project()
    with configshelve.configshelve(project.guiConfigFile) as config:
        ui = AWGOptimizer(DummyAWG, config)
        ui.show()
        sys.exit(app.exec_())