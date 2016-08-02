# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import os.path

from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic

from ProjectConfig.Project import getProject
from modules.firstNotNone import firstNotNone
#from modules.PyqtUtility import updateComboBoxItems
from modules.PyqtUtility import BlockSignals

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/VoltageFiles.ui')
VoltageFilesForm, VoltageFilesBase = PyQt5.uic.loadUiType(uipath)


class Scan:
    pass

class Files:
    def __init__(self):
        self.mappingFile = None
        self.definitionFile = None
        self.globalFile = None
        self.localFile = None
        self.mappingHistory = dict()
        self.definitionHistory = dict()
        self.globalHistory = dict()
        self.localHistory = dict()

class VoltageFiles(VoltageFilesForm, VoltageFilesBase ):
    loadMapping = QtCore.pyqtSignal(str)
    loadDefinition = QtCore.pyqtSignal(str, str)
    loadGlobalAdjust = QtCore.pyqtSignal(object)
    loadLocalAdjust = QtCore.pyqtSignal(str)
    
    def __init__(self,config,parent=None):
        VoltageFilesForm.__init__(self)
        VoltageFilesBase.__init__(self, parent)
        self.config = config
        self.configname = 'VoltageFiles.Files'
        self.files = self.config.get(self.configname, Files())
        self.lastDir = getProject().configDir

    def setupUi(self, parent):
        VoltageFilesForm.setupUi(self, parent)
        self.mappingCombo.addItems( list(self.files.mappingHistory.keys()) )
        self.loadMappingButton.clicked.connect( self.onLoadMapping )
        self.loadDefinitionButton.clicked.connect( self.onLoadDefinition )
        self.loadGlobalButton.clicked.connect( self.onLoadGlobal )
        if self.files.mappingFile is not None:
            _, filename = os.path.split(self.files.mappingFile)
            self.mappingCombo.setCurrentIndex( self.mappingCombo.findText(filename))
        self.definitionCombo.addItems( list(self.files.definitionHistory.keys()) )
        if self.files.definitionFile is not None:
            _, filename = os.path.split(self.files.definitionFile)
            self.definitionCombo.setCurrentIndex( self.definitionCombo.findText(filename))
        self.globalCombo.addItems( list(self.files.globalHistory.keys()) )
        if self.files.globalFile is not None:
            _, filename = os.path.split(self.files.globalFile)
            self.globalCombo.setCurrentIndex( self.globalCombo.findText(filename))
        self.mappingCombo.currentIndexChanged['QString'].connect( self.onMappingChanged )
        self.definitionCombo.currentIndexChanged['QString'].connect( self.onDefinitionChanged )
        self.globalCombo.currentIndexChanged['QString'].connect( self.onGlobalChanged )
        self.reloadDefinition.clicked.connect( self.onReloadDefinition)
        self.removeDefinition.clicked.connect( self.onRemoveDefinition)
        self.reloadMapping.clicked.connect( self.onReloadMapping)
        self.removeMapping.clicked.connect( self.onRemoveMapping)
        self.reloadGlobal.clicked.connect( self.onReloadGlobal)
        self.removeGlobal.clicked.connect( self.onRemoveGlobal)


    def onReloadDefinition(self):
        if self.files.definitionFile:
            self.loadDefinition.emit(self.files.definitionFile, self.shuttlingDefinitionPath() )
            logger = logging.getLogger(__name__)
            logger.info( "onReloadDefinition {0}".format(self.files.definitionFile) )

    def onRemoveDefinition(self):
        self.removeComboUtility(self.files.definitionHistory,self.files.definitionFile,self.definitionCombo)
        logger = logging.getLogger(__name__)
        logger.info( "onRemoveMapping {0}".format(self.files.globalFile) )

    def onReloadMapping(self):
        if self.files.mappingFile:
            self.loadMapping.emit(self.files.mappingFile)
            logger = logging.getLogger(__name__)
            logger.info( "onReloadMapping {0}".format(self.files.mappingFile) )

    def onRemoveMapping(self):
        self.removeComboUtility(self.files.mappingHistory,self.files.mappingFile,self.mappingCombo)
        logger = logging.getLogger(__name__)
        logger.info( "onRemoveMapping {0}".format(self.files.mappingFile) )

    def onReloadGlobal(self):
        if self.files.globalFile:
            self.loadGlobalAdjust.emit(self.files.globalFile)
            logger = logging.getLogger(__name__)
            logger.info( "onReloadGlobal {0}".format(self.files.globalFile) )

    def onRemoveGlobal(self):
        self.removeComboUtility(self.files.globalHistory,self.files.globalFile,self.globalCombo)
        logger = logging.getLogger(__name__)
        logger.info( "onRemoveGlobal {0}".format(self.files.globalFile) )

    def removeComboUtility(self,history,file,combo):
        """Utility used by onRemoveMapping/Definition/etc. to update the combo boxes and remove the entry from the file
           history."""
        for v,k in list(zip(history.values(),history.keys())):
            if v is file:
                history.pop(k)
        #updateComboBoxItems(self.definitionCombo, list(self.files.definitionHistory.keys()))
        # Cannot use updateComboBox because it would display the first item in the list. We want
        # the combo box to display a blank until the user switches the selection.
        # TODO: incorporate this as an option into updateComboBox
        with BlockSignals(combo):
            combo.clear()
            if history:
                combo.addItems(history)
            combo.setCurrentIndex(-1)

    def onReloadGlobal(self):
        if self.files.globalFile:
            self.loadGlobalAdjust.emit(self.files.globalFile)
            logger = logging.getLogger(__name__)
            logger.info( "onReloadGlobal {0}".format(self.files.globalFile) )

    def reloadAll(self):
        if self.files.mappingFile:
            self.loadMapping.emit(self.files.mappingFile)
        if self.files.definitionFile:
            self.loadDefinition.emit(self.files.definitionFile, self.shuttlingDefinitionPath() )
        if self.files.globalFile:
            self.loadGlobalAdjust.emit(self.files.globalFile)
        if self.files.localFile:
            self.loadLocalAdjust.emit(self.files.localFile)
            
        
    def onMappingChanged(self, value):
        logger = logging.getLogger(__name__)
        self.files.mappingFile = self.files.mappingHistory[str(value)]
        self.loadMapping.emit(self.files.mappingFile)
        logger.info( "onMappingChanged {0}".format(self.files.mappingFile) )
        
    def onDefinitionChanged(self, value):
        logger = logging.getLogger(__name__)
        self.files.definitionFile = self.files.definitionHistory[str(value)]
        self.loadDefinition.emit(self.files.definitionFile, self.shuttlingDefinitionPath())
        logger.info( "onDefinitionChanged {0}".format(self.files.definitionFile) )
        
    def onGlobalChanged(self, value):
        if value is not None:
            logger = logging.getLogger(__name__)
            value = str(value)
            if  value in self.files.globalHistory:
                self.files.globalFile = self.files.globalHistory[value]
            self.loadGlobalAdjust.emit(self.files.globalFile)
            logger.info( "onGlobalChanged {0}".format(self.files.globalFile) )
        
    def onLocalChanged(self, value):
        pass

    def onLoadMapping(self):
        logger = logging.getLogger(__name__)
        logger.debug( "onLoadMapping" )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open mapping file:", self.lastDir )
        if path!="":
            filedir, filename = os.path.split(path)
            self.lastDir = filedir
            if filename not in self.files.mappingHistory:
                self.files.mappingHistory[filename] = path
                self.mappingCombo.addItem(filename)
            else:
                self.files.mappingHistory[filename] = path
            self.mappingCombo.setCurrentIndex( self.mappingCombo.findText(filename))
            self.files.mappingFile = path
            self.loadMapping.emit(path)
            
    def onLoadDefinition(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open definition file:", self.lastDir)
        self.loadVoltageDef(path)

    def loadVoltageDef(self,path):
        # Load the voltage definition given by path.
        if path!="":
            filedir, filename = os.path.split(path)
            self.lastDir = filedir
            if filename not in self.files.definitionHistory:
                self.files.definitionHistory[filename] = path
                self.definitionCombo.addItem(filename)
            else:
                self.files.definitionHistory[filename] = path
            self.definitionCombo.setCurrentIndex( self.definitionCombo.findText(filename))
            self.files.definitionFile = path
            self.loadDefinition.emit(path, self.shuttlingDefinitionPath(path) )

    def shuttlingDefinitionPath(self, definitionpath=None ):
        path = firstNotNone( definitionpath, self.files.definitionFile )
        filedir, filename = os.path.split(path)
        basename, _ = os.path.splitext(filename)
        return os.path.join( filedir, basename+"_shuttling.xml" )


    def onLoadGlobal(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open global adjust file:", self.lastDir)
        if path!="":
            filedir, filename = os.path.split(path)
            self.lastDir = filedir
            if filename not in self.files.globalHistory:
                self.globalCombo.addItem(filename)
            self.files.globalHistory[filename] = path
            self.globalCombo.setCurrentIndex( self.globalCombo.findText(filename))
            self.files.globalFile = path
            self.loadGlobalAdjust.emit(path)

    def onLoadLocal(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open local adjust file:", self.lastDir)
        if path!="":
            filedir, filename = os.path.split(path)
            self.lastDir = filedir
            if filename not in self.files.localHistory:
                self.localCombo.addItem(filename)
            self.files.localHistory[filename] = path
            self.localCombo.setCurrentIndex( self.localCombo.find(filename))
            self.files.localFile = path
            self.loadLocalAdjust.emit(path)
    
    def saveConfig(self):
        self.config[self.configname] = self.files
        