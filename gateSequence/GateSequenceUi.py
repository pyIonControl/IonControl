# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import operator
import os.path

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic

from .GateDefinition import GateDefinition
from .GateSequenceCompiler import GateSequenceCompiler
from .GateSequenceContainer import GateSequenceContainer
from modules.enum import enum
from modules.PyqtUtility import updateComboBoxItems, BlockSignals
from modules.HashableDict import HashableDict
import xml.etree.ElementTree as ElementTree
from modules.XmlUtilit import xmlEncodeAttributes, xmlParseAttributes,\
    xmlEncodeDictionary, xmlParseDictionary
from ProjectConfig.Project import getProject
import shutil

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/GateSequence.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


class Settings:
    stateFields = [ 'enabled', 'gate', 'gateDefinition', 'gateSequence', 'active', 'startAddressParam',
                    'thisSequenceRepetition', 'debug', 'gateSequenceCache', 'gateDefinitionCache' ]
    XMLTagName = "GateSequence"
    def __init__(self):
        self.enabled = False
        self.gate = []
        self.gateDefinition = None
        self.gateSequence = None
        self.active = 0
        self.lastDir = ""
        self.startAddressParam = ""
        self.gateSequenceCache = HashableDict()
        self.gateDefinitionCache = HashableDict()
        self.thisSequenceRepetition = 10
        self.debug = False
        self.generatorType = 'GateSequenceList'
        self.gateSet = ''
        self.preparationFiducials = ''
        self.preparationFiducialsIsFile = False
        self.measurementFiducials = ''
        self.measurementFiducialsIsFile = False
        self.germs = ''
        self.germsIsFile = False
        self.lengths = ''

        
    def __setstate__(self, d):
        self.__dict__ = d
        for cache in [self.gateDefinitionCache, self.gateSequenceCache]:
            for key, value in list(cache.items()):
                if not os.path.exists(value):
                    cache.pop(key)
        if not isinstance(self.gateSequenceCache, HashableDict):
            self.gateSequenceCache = HashableDict(self.gateSequenceCache)
        if not isinstance(self.gateDefinitionCache, HashableDict):
            self.gateDefinitionCache =  HashableDict( self.gateDefinitionCache )

    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))
        
    def __repr__(self):
        m = list()
        m.append( "GateSequence {0}".format( {True:'enabled',False:'disabled'}[self.enabled]) )
        m.append( "Gate Definition: {0}".format(self.gateDefinition))
        m.append( "GateSequence StartAddressParam {0}".format(self.startAddressParam))
        if self.active==0: # Full list scan
            m.append( "GateSequence: {0}".format(self.gateSequence))
        else:
            m.append( "Gate {0}".format(self.gate))
        return "\n".join(m)

    documentationList = [ 'gateDefinition', 'gateSequence', 'startAddressParam' ]
    
    def exportXml(self, element):
        myElement = ElementTree.SubElement(element, self.XMLTagName )
        xmlEncodeAttributes( self.__dict__, myElement)
        xmlEncodeDictionary(self.gateDefinitionCache, ElementTree.SubElement(myElement, "GateDefinitionCache" ), "Item")
        xmlEncodeDictionary(self.gateSequenceCache, ElementTree.SubElement(myElement, "GateSequenceCache" ), "Item")
        gateElement = ElementTree.SubElement(myElement, "Gate" )
        gateElement.text = ",".join( self.gate )
        return myElement
    
    @staticmethod
    def fromXmlElement(element):
        myElement = element.find( Settings.XMLTagName )
        s = Settings()
        s.__dict__.update( xmlParseAttributes(myElement) )
        s.gateDefinitionCache = xmlParseDictionary(myElement.find("GateDefinitionCache"), "Item")
        s.gateSequenceCache = xmlParseDictionary(myElement.find("GateSequenceCache"), "Item")
        gateText = myElement.find("Gate").text
        s.gate = gateText.split(",") if gateText else list()
        return s    
    
    def documentationString(self):
        r = "\r\n".join( [ "{0}\t{1}".format(field, getattr(self, field)) for field in self.documentationList] )
        return r
        
    def description(self):
        desc = dict( ((field, getattr(self, field)) for field in self.documentationList) )
        return desc


class GateSequenceUi(Form, Base):    
    Mode = enum('FullList', 'Gate')
    valueChanged = QtCore.pyqtSignal()
    def __init__(self,parent=None):
        Form.__init__(self)
        Base.__init__(self, parent)

    def postInit(self, name, config, pulseProgram):
        self.config = config
        self.configname = "GateSequenceUi."+name
        self.settings = self.config.get(self.configname, Settings())
        self.gatedef = GateDefinition()
        self.gateSequenceContainer = GateSequenceContainer(self.gatedef)
        self.gateSequenceCompiler = GateSequenceCompiler(pulseProgram)

    def setupUi(self, parent):
        super(GateSequenceUi, self).setupUi(parent)
        self.setSettings( self.settings )
        self.GateSequenceEnableCheckBox.stateChanged.connect( self.onEnableChanged )
        self.GateDefinitionButton.clicked.connect( self.onLoadGateDefinition )
        self.GateSequenceButton.clicked.connect( self.onLoadGateSequenceList )
        self.FullListRadioButton.toggled.connect( self.onRadioButtonToggled )
        self.GateEdit.editingFinished.connect( self.onGateEditChanged )
        self.StartAddressBox.currentIndexChanged['QString'].connect( self.onStartAddressParam )
        self.repetitionSpinBox.valueChanged.connect( self.onRepetitionChanged )
        self.GateSequenceBox.currentIndexChanged[str].connect( self.onGateSequenceChanged )
        self.GateDefinitionBox.currentIndexChanged[str].connect( self.onGateDefinitionChanged )
        self.debugCheckBox.stateChanged.connect( self.onDebugChanged )
        self.project = getProject()
        self.defaultGateSequencesDir = self.project.configDir+'/GateSequences'
        if not os.path.exists(self.defaultGateSequencesDir):
            exampleGateSequencesDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/GateSequences')) #/IonControl/config/GateSequences directory
            shutil.copytree(exampleGateSequencesDir, self.defaultGateSequencesDir) #Copy over all example gate sequence files

    def getSettings(self):
        logger = logging.getLogger(__name__)
        logger.debug( "GateSequenceUi GetSettings {0}".format(self.settings.__dict__) )
        return self.settings
        
    def setSettings(self, settings):
        logger = logging.getLogger(__name__)
        logger.debug( str( settings) )
        logger.debug( "GateSequenceUi SetSettings {0}".format( settings.__dict__ ) )
        self.settings = settings
        self.GateSequenceEnableCheckBox.setChecked( self.settings.enabled )
        self.GateSequenceFrame.setEnabled( self.settings.enabled )
        self.GateEdit.setText( ", ".join(self.settings.gate ))
        self.repetitionSpinBox.setValue( self.settings.thisSequenceRepetition )
        if self.settings.startAddressParam:
            self.StartAddressBox.setCurrentIndex(self.StartAddressBox.findText(self.settings.startAddressParam) )
        else:
            self.settings.startAddressParam = str(self.StartAddressBox.currentText())
        self.settings.startAddressParam = str(self.settings.startAddressParam)
        try:
            updateComboBoxItems(self.GateDefinitionBox, list(self.settings.gateDefinitionCache.keys()))
            updateComboBoxItems(self.GateSequenceBox, list(self.settings.gateSequenceCache.keys()))
            self.updateDatastructures()
        except IOError as err:
            logger.warning( "{0} during loading of GateSequence Files, ignored.".format(err) )
        with BlockSignals(self.FullListRadioButton) as w:
            if self.settings.active == self.Mode.FullList:
                self.FullListRadioButton.setChecked(True)
            elif self.settings.active == self.Mode.Gate:
                self.GateRadioButton.setChecked(True)

    def updateDatastructures(self):
        if self.settings.enabled:
            if self.settings.gateDefinition and self.settings.gateDefinition in self.settings.gateDefinitionCache:
                self.loadGateDefinition( self.settings.gateDefinitionCache[self.settings.gateDefinition] )
                self.GateDefinitionBox.setCurrentIndex(self.GateDefinitionBox.findText(self.settings.gateDefinition))
            if self.settings.gateSequence and self.settings.gateSequence in self.settings.gateSequenceCache:
                self.loadGateSequenceList( self.settings.gateSequenceCache[self.settings.gateSequence] )
                self.GateSequenceBox.setCurrentIndex(self.GateSequenceBox.findText(self.settings.gateSequence))
        else:
            self.clearGateDefinition()
            self.clearGateSequenceList()

    def documentationString(self):
        return repr(self.settings)   
    
    def descritpion(self):
        return self.settings.description()     
            
    def onGateDefinitionChanged(self, name):
        name = str(name)
        if name in self.settings.gateDefinitionCache:
            self.loadGateDefinition( self.settings.gateDefinitionCache[name] )  
        self.valueChanged.emit()          
            
    def onGateSequenceChanged(self, name):
        name = str(name)
        if name in self.settings.gateSequenceCache:
            self.loadGateSequenceList( self.settings.gateSequenceCache[name] )
        self.valueChanged.emit()          
            
    def onRepetitionChanged(self, value):
        self.settings.thisSequenceRepetition = value
        self.valueChanged.emit()          
        
    def onStartAddressParam(self, name):
        self.settings.startAddressParam = str(name)       
        self.valueChanged.emit()          
        
    def onEnableChanged(self, state):
        self.settings.enabled = state == QtCore.Qt.Checked
        self.GateSequenceFrame.setEnabled( self.settings.enabled )
        self.updateDatastructures()
        self.valueChanged.emit()          
        
    def onDebugChanged(self, state):
        self.settings.debug = state == QtCore.Qt.Checked        
        self.valueChanged.emit()          
        
    def close(self):
        self.config[self.configname] = self.settings
                
    def onLoadGateDefinition(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Gate definition file:", self.defaultGateSequencesDir)
        if path!="":
            filedir, filename = os.path.split(path)
            self.settings.lastDir = filedir
            self.loadGateDefinition(path)
            if filename not in self.settings.gateDefinitionCache:
                self.settings.gateDefinitionCache[filename] = path
                self.GateDefinitionBox.addItem(filename)
                self.GateDefinitionBox.setCurrentIndex( self.GateDefinitionBox.findText(filename))
        self.valueChanged.emit()          

    def loadGateDefinition(self, path):
        self.gatedef.loadGateDefinition(path)    
        _, filename = os.path.split(path)
        self.settings.gateDefinition = filename
        self.GateDefinitionBox.setCurrentIndex(self.GateDefinitionBox.findText(filename))
        self.gatedef.printGates()
        self.valueChanged.emit()      
        
    def clearGateDefinition(self):    
        self.gatedef.loadGateDefinition(None)    
        self.GateDefinitionBox.setCurrentIndex(-1)
        self.valueChanged.emit()      
    
    def onLoadGateSequenceList(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Gate Set file:", self.defaultGateSequencesDir)
        if path!="":
            filedir, filename = os.path.split(path)
            self.settings.lastDir = filedir
            self.loadGateSequenceList(path)
            if filename not in self.settings.gateSequenceCache:
                self.settings.gateSequenceCache[filename] = path
                self.GateSequenceBox.addItem(filename)
                self.GateSequenceBox.setCurrentIndex( self.GateSequenceBox.findText(filename))
        self.valueChanged.emit()          
            
    def loadGateSequenceList(self, path):
        logger = logging.getLogger(__name__)
        self.gateSequenceContainer.loadXml(path)
        logger.debug( "loaded {0} gateSequences from {1}.".format(len(self.gateSequenceContainer.GateSequenceDict), path) )
        _, filename = os.path.split(path)
        self.settings.gateSequence = filename
        self.GateSequenceBox.setCurrentIndex(self.GateSequenceBox.findText(filename))
        
    def clearGateSequenceList(self):
        self.gateSequenceContainer.loadXml(None)
        self.GateSequenceBox.setCurrentIndex(-1)
    
    def onGateEditChanged(self):
        self.settings.gate = list(map(operator.methodcaller('strip'), str(self.GateEdit.text()).split(',')))
        self.GateEdit.setText( ", ".join(self.settings.gate ))
        self.valueChanged.emit()          
    
    def onRadioButtonToggled(self):
        if self.FullListRadioButton.isChecked():
            self.settings.active = self.Mode.FullList 
        else:
            self.settings.active = self.Mode.Gate   
        self.valueChanged.emit()          
            
    def gateSequenceScanData(self):
        if self.settings.active == self.Mode.FullList:
            address, data = self.gateSequenceCompiler.gateSequencesCompile( self.gateSequenceContainer )
        else:
            self.gateSequenceCompiler.gateCompile( self.gateSequenceContainer.gateDefinition )
            data = self.gateSequenceCompiler.gateSequenceCompile( self.settings.gate )
            address = [0]*self.settings.thisSequenceRepetition
        return address, data, self.settings
    
    def gateSequenceAttributes(self):
        if self.settings.active == self.Mode.FullList:
            return list(self.gateSequenceContainer.GateSequenceAttributes.values())
        return None
        
    def setVariables(self, variabledict):
        self.variabledict = variabledict
        #oldParameterName = self.StartAddressBox.currentText()
        self.StartAddressBox.clear()
        for _, var in iter(sorted(variabledict.items())):
            if var.type == "address":
                self.StartAddressBox.addItem(var.name)
        if self.settings.startAddressParam:
            self.StartAddressBox.setCurrentIndex(self.StartAddressBox.findText(self.settings.startAddressParam) )
        else:
            self.settings.startAddressParam = self.StartAddressBox.currentText()


if __name__ == "__main__":
    from pulseProgram.PulseProgram import PulseProgram
    pp = PulseProgram()
    pp.debug = False
    pp.loadSource(r"C:\Users\Public\Documents\experiments\test3\config\PulsePrograms\YbGateSequenceTomography.pp")
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = GateSequenceUi()
    ui.postInit("test", config, pp)
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    app.exec_()
    address, data, parameter = ui.gateSequenceScanData()
    a = address[541]
    l = data[ a/4 ]
    print(a, l)
    print(data[ a/4 : a/4+3*l+1 ])
    address, data, parameter = ui.gateSequenceScanData()
    a = address[36]
    l = data[ a/4 ]
    print(a, l)
    print(data[ a/4 : a/4+3*l+1 ])
    print(config)
    print("done")
