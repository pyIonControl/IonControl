# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging

from PyQt5 import QtWidgets, QtCore
import PyQt5.uic

from .VoltageAdjust import VoltageAdjust
from . import VoltageBlender
from .VoltageFiles import VoltageFiles
from .VoltageGlobalAdjust import VoltageGlobalAdjust
from . import VoltageTableModel
from voltageControl.VoltageLocalAdjust import VoltageLocalAdjust
from reportlab.pdfbase.pdfdoc import Destination
import functools
from ProjectConfig.Project import getProject

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/VoltageControl.ui')
VoltageControlForm, VoltageControlBase = PyQt5.uic.loadUiType(uipath)


class Settings:
    pass

class VoltageControl(VoltageControlForm, VoltageControlBase ):    
    def __init__(self, config, globalDict=None, dacController=None, parent=None):
        VoltageControlForm.__init__(self)
        VoltageControlBase.__init__(self, parent)
        self.config = config
        self.configname = 'VoltageControl.Settings'
        self.settings = self.config.get(self.configname, Settings())
        self.dacController = dacController
        self.voltageBlender = VoltageBlender.VoltageBlender(globalDict, dacController)
        self.globalDict = globalDict
        self.project = getProject()

    def setupUi(self, parent):
        logger = logging.getLogger(__name__)
        VoltageControlForm.setupUi(self, parent)
        self.voltageFilesUi = VoltageFiles(self.config)
        self.voltageFilesUi.setupUi( self.voltageFilesUi )
        self.voltageFilesDock.setWidget( self.voltageFilesUi )
        self.adjustUi = VoltageAdjust(self.config, self.voltageBlender, self.globalDict)
        self.adjustUi.updateOutput.connect( self.onUpdate )
        self.adjustUi.setupUi( self.adjustUi )
        self.adjustDock.setWidget( self.adjustUi )
        self.globalAdjustUi = VoltageGlobalAdjust(self.config, self.globalDict)
        self.globalAdjustUi.setupUi( self.globalAdjustUi )
        self.globalAdjustUi.updateOutput.connect( self.voltageBlender.setAdjust )
        self.globalAdjustDock.setWidget( self.globalAdjustUi )
        self.localAdjustUi = VoltageLocalAdjust(self.config, self.globalDict)
        self.localAdjustUi.setupUi( self.localAdjustUi )
        self.localAdjustUi.updateOutput.connect( self.voltageBlender.setLocalAdjust )
        self.localAdjustDock = QtWidgets.QDockWidget("Local Adjust")
        self.localAdjustDock.setObjectName("_LocalAdjustDock")
        self.localAdjustDock.setWidget( self.localAdjustUi )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.localAdjustDock)
        if hasattr(self.settings, 'state'):
            self.restoreState( self.settings.state )
        self.voltageFilesUi.loadMapping.connect( self.voltageBlender.loadMapping )
        self.voltageFilesUi.loadDefinition.connect( self.onLoadVoltage )
        self.voltageFilesUi.loadGlobalAdjust.connect( self.onLoadGlobalAdjust )
        self.voltageTableModel = VoltageTableModel.VoltageTableModel(self.voltageBlender)
        self.tableView.setModel( self.voltageTableModel )
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        self.localAdjustUi.filesChanged.connect( self.voltageBlender.loadLocalAdjust )
        self.voltageBlender.dataChanged.connect( self.voltageTableModel.onDataChanged )
        self.voltageBlender.dataError.connect( self.voltageTableModel.onDataError )
        self.tableView.setSortingEnabled(True)
        self.voltageFilesUi.reloadAll()
        adjust = self.adjustUi.adjust
        self.voltageBlender.loadLocalAdjust( self.localAdjustUi.localAdjustList, list() )
        try:
            self.voltageBlender.applyLine(adjust.line, adjust.lineGain, adjust.globalGain )
            self.adjustUi.setLine(adjust.line)
        except Exception as e:
            logger.error("cannot apply voltages. Ignored for now. Exception:{0}".format(e))
        self.adjustUi.shuttleOutput.connect( self.voltageBlender.shuttle )
        self.voltageBlender.shuttlingOnLine.connect( self.adjustUi.setPosition )

    def onLoadVoltage(self, path, shuttledefpath ):
        path = self.project.findFile(path)
        shuttledefpath = self.project.findFile(shuttledefpath)
        self.voltageBlender.loadVoltage(path)
        self.adjustUi.loadShuttleDef( shuttledefpath )

    def shuttleTo(self, destination, onestep=False):
        return self.adjustUi.onShuttleSequence(destination, instant=onestep)
    
    def shuttlingNodesObservable(self):
        return self.adjustUi.shuttlingGraph.graphChangedObservable
        
    def currentShuttlingPosition(self):
        return self.adjustUi.currentShuttlingPosition()
        
    def shuttlingNodes(self):
        return self.adjustUi.shuttlingNodes()
    
    def synchronize(self):
        self.adjustUi.synchronize()
    
    def onUpdate(self, adjust, updateHardware=True ):
        try:
            self.voltageBlender.applyLine(float(adjust.line), float(adjust.lineGain), float(adjust.globalGain), updateHardware)
        except ValueError as e:
            logging.getLogger(__name__).warning( str(e) )
        self.adjustUi.setLine(float(adjust.line))
                     
    def onLoadGlobalAdjust(self, path):
        path = self.project.findFile(path)
        self.voltageBlender.loadGlobalAdjust(path)
        self.globalAdjustUi.setupGlobalAdjust(path, self.voltageBlender.adjustDict)
    
    def saveConfig(self):
        self.settings.state = self.saveState()
        self.settings.isVisible = self.isVisible()
        self.config[self.configname] = self.settings
        self.adjustUi.saveConfig()
        self.globalAdjustUi.saveConfig()
        self.voltageFilesUi.saveConfig()
        self.localAdjustUi.saveConfig()
    
    def onClose(self):
        pass
        
    def closeEvent(self, e):
        self.onClose()
        
    def onShuttleSequence(self, cont=False):
        self.adjustUi.onShuttleEdge(0)
  
if __name__ == "__main__":
    class MyMainWindow(QtWidgets.QMainWindow):
        def setCentralWidget(self, widget):
            self.myCentralWidget = widget
            super(MyMainWindow, self).setCentralWidget(widget)  
            
        def closeEvent(self, e):
            self.myCentralWidget.onClose()
            super(MyMainWindow, self).closeEvent(e)   
    
    import sys
    from persist import configshelve
    with configshelve.configshelve("VoltageControl-test") as config:
        app = QtWidgets.QApplication(sys.argv)
        MainWindow = MyMainWindow()
        ui = VoltageControl(config)
        ui.setupUi(ui)
        MainWindow.setCentralWidget(ui)
        MainWindow.show()
        sys.exit(app.exec_())


        
