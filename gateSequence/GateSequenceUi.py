# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import operator
import os.path
from enum import Enum
from functools import partial
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic
from pygsti.objects import GateString

from modules.filetype import isXmlFile
from trace.PlottedStructure import PlottedStructureProperties
from .GateDefinition import GateDefinition
from .GateSequenceCompiler import GateSequenceCompiler
from .GateSequenceContainer import GateSequenceContainer
from modules.enum import enum
from modules.PyqtUtility import updateComboBoxItems, BlockSignals, setCurrentComboText
from modules.HashableDict import HashableDict
import lxml.etree as ElementTree
from modules.XmlUtilit import xmlEncodeAttributes, xmlParseAttributes,\
    xmlEncodeDictionary, xmlParseDictionary
from ProjectConfig.Project import getProject
import shutil

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/GateSequence.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


def split(text):
    ''''Split a list if , are present it will use , as separator else whitespace'''
    if text.find(',')>=0:
        return map(operator.methodcaller('strip'), text.split(','))
    return text.split()

class Settings:
    stateFields = ['enabled', 'gate', 'gateDefinition', 'gateSequence', 'active', 'startAddressParam',
                   'thisSequenceRepetition', 'debug', 'gateSequenceCache', 'gateDefinitionCache',
                   'generatorType', 'gateSet', 'preparationFiducials', 'measurementFiducials',
                   'germs', 'lengths', 'keepFraction', 'keepSeed', 'preparationFiducialsCache',
                   'measurementFiducialsCache', 'germsCache', 'lengthsCache', 'gateSetCache',
                   'plotProperties', 'packWidth']
    XMLTagName = "GateSequence"
    class GeneratorType(Enum):
        GateSequenceList = 0
        GST = 1

    def __init__(self):
        self.enabled = False
        self.gate = GateString(None, "{}")
        self.gateDefinition = None
        self.gateSequence = None
        self.active = 0
        self.lastDir = ""
        self.startAddressParam = ""
        self.gateSequenceCache = HashableDict()
        self.gateDefinitionCache = HashableDict()
        self.thisSequenceRepetition = 10
        self.debug = False
        self.generatorType = self.GeneratorType.GateSequenceList
        self.gateSet = ''
        self.preparationFiducials = ''
        self.measurementFiducials = ''
        self.germs = ''
        self.lengths = ''
        self.keepFraction = 1
        self.keepSeed = 0
        self.gateSetCache = HashableDict()
        self.preparationFiducialsCache = HashableDict()
        self.measurementFiducialsCache = HashableDict()
        self.germsCache = HashableDict()
        self.lengthsCache = HashableDict()
        self.plotProperties = PlottedStructureProperties()
        self.packWidth = 0  # if != 0 pack data using that many bits

    def __setstate__(self, d):
        self.__dict__ = d
        for cache in [self.gateDefinitionCache, self.gateSequenceCache]:
            for key, value in list(cache.items()):
                if not os.path.exists(value):
                    cache.pop(key)
        if not isinstance(self.gateSequenceCache, HashableDict):
            self.gateSequenceCache = HashableDict(self.gateSequenceCache)
        if not isinstance(self.gateDefinitionCache, HashableDict):
            self.gateDefinitionCache = HashableDict( self.gateDefinitionCache )
        self.__dict__.setdefault('generatorType', self.GeneratorType.GateSequenceList)
        self.__dict__.setdefault('gateSet', '')
        self.__dict__.setdefault('preparationFiducials', '')
        self.__dict__.setdefault('measurementFiducials', '')
        self.__dict__.setdefault('germs', '')
        self.__dict__.setdefault('lengths', '')
        self.__dict__.setdefault('keepFraction', 1)
        self.__dict__.setdefault('keepSeed', 0)
        self.__dict__.setdefault('preparationFiducialsCache', HashableDict())
        self.__dict__.setdefault('measurementFiducialsCache', HashableDict())
        self.__dict__.setdefault('germsCache', HashableDict())
        self.__dict__.setdefault('lengthsCache', HashableDict())
        self.__dict__.setdefault('gateSetCache', HashableDict())
        self.__dict__.setdefault('plotProperties', PlottedStructureProperties())
        self.__dict__.setdefault('packWidth', 0)
        if isinstance(self.generatorType, str):
            self.generatorType = self.GeneratorType.GateSequenceList
        if not isinstance(self.gate, GateString):
            self.gate = GateString(None, "{}")

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
        gateElement.text = str(self.gate)
        return myElement
    
    @staticmethod
    def fromXmlElement(element):
        myElement = element.find( Settings.XMLTagName )
        s = Settings()
        s.__dict__.update( xmlParseAttributes(myElement) )
        s.gateDefinitionCache = xmlParseDictionary(myElement.find("GateDefinitionCache"), "Item")
        s.gateSequenceCache = xmlParseDictionary(myElement.find("GateSequenceCache"), "Item")
        gateText = myElement.find("Gate").text
        s.gate = GateString(None, gateText)
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
        self._usePyGSTi = False

    def postInit(self, name, config, pulseProgram):
        self.config = config
        self.configname = "GateSequenceUi."+name
        self.settings = self.config.get(self.configname, Settings())
        self.gatedef = GateDefinition()
        self.gateSequenceContainer = GateSequenceContainer(self.gatedef)
        self.gateSequenceCompiler = GateSequenceCompiler(pulseProgram)

    def setupUi(self, parent):
        super(GateSequenceUi, self).setupUi(parent)
        self.setSettings(self.settings)
        self.GateSequenceEnableCheckBox.stateChanged.connect(self.onEnableChanged)
        self.GateDefinitionButton.clicked.connect(partial(self.onLoadGeneric, self.GateDefinitionBox, 'gateDefinitionCache', self.loadGateDefinition, message="Open Gate Definition:"))
        self.GateSequenceButton.clicked.connect(partial(self.onLoadGeneric, self.GateSequenceBox, 'gateSequenceCache', self.loadGateSequenceList, message="Open Gate Sequence File:"))
        self.FullListRadioButton.toggled.connect(self.onRadioButtonToggled)
        self.GateSetButton.clicked.connect(partial(self.onLoadGeneric, self.GateSetBox, 'gateSetCache', self.loadGateSet, message="Open Gate Set:"))
        self.PreparationButton.clicked.connect(partial(self.onLoadGeneric, self.PreparationBox, 'preparationFiducialsCache', self.loadPreparation, message="Open Preparation Fiducials:"))
        self.MeasurementButton.clicked.connect(partial(self.onLoadGeneric, self.MeasurementBox, 'measurementFiducialsCache', self.loadMeasurement, message="Open Measurement Fiducials:"))
        self.GermsButton.clicked.connect(partial(self.onLoadGeneric, self.GermsBox, 'germsCache', self.loadGerms, message="Open Germs:"))
        self.LengthsButton.clicked.connect(partial(self.onLoadGeneric, self.LengthsBox, 'lengthsCache', self.loadLengths, message="Open Lengths:"))
        self.GateEdit.editingFinished.connect(self.onGateEditChanged)
        self.StartAddressBox.currentIndexChanged['QString'].connect(self.onStartAddressParam)
        self.repetitionSpinBox.valueChanged.connect(self.onRepetitionChanged)
        self.GateSequenceBox.currentIndexChanged[str].connect(self.onGateSequenceChanged)
        self.GateDefinitionBox.currentIndexChanged[str].connect(self.onGateDefinitionChanged)
        self.sourceSelect.currentIndexChanged[int].connect(self.onChangeSource)
        self.debugCheckBox.stateChanged.connect(self.onDebugChanged)
        self.keepFractionBox.valueChanged.connect(partial(setattr, self, 'keepFraction'))
        self.keepSeedBox.valueChanged.connect(partial(setattr, self, 'keepSeed'))
        self.PreparationBox.lineEdit().editingFinished.connect(self.loadPreparation)
        self.MeasurementBox.lineEdit().editingFinished.connect(self.loadMeasurement)
        self.GermsBox.lineEdit().editingFinished.connect(self.loadGerms)
        self.LengthsBox.lineEdit().editingFinished.connect(self.loadLengths)
        self.packWidthCombo.addItems(['0', '2', '4', '8', '16', '32', '64'])
        self.packWidthCombo.currentIndexChanged[str].connect(self.onPackWidthChanged)
        self.project = getProject()
        self.defaultGateSequencesDir = self.project.configDir + '/GateSequences'
        if not os.path.exists(self.defaultGateSequencesDir):
            # /IonControl/config/GateSequences directory
            exampleGateSequencesDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..','config/GateSequences'))
            shutil.copytree(exampleGateSequencesDir,
                            self.defaultGateSequencesDir)  # Copy over all example gate sequence files
        self.treeWidget.setParameters(self.settings.plotProperties.parameters())

    def onPackWidthChanged(self, value):
        self.settings.packWidth = int(value)

    def onChangeSource(self, index):
        try:
            self.settings.generatorType = Settings.GeneratorType(index)
        except ValueError:
            self.settings.generatorType = Settings.GeneratorType.GateSequenceList
        self.gateSequenceContainer.usePyGSTi = self._usePyGSTi = self.settings.generatorType == Settings.GeneratorType.GST

    def getSettings(self):
        logger = logging.getLogger(__name__)
        logger.debug( "GateSequenceUi GetSettings {0}".format(self.settings.__dict__) )
        return self.settings
        
    def setSettings(self, settings):
        logger = logging.getLogger(__name__)
        logger.debug( str( settings) )
        logger.debug( "GateSequenceUi SetSettings {0}".format( settings.__dict__ ) )
        self.settings = settings
        self.loadGateSet(self.settings.gateSetCache.get(self.settings.gateSet))
        self.loadPreparation(self.settings.preparationFiducialsCache.get(self.settings.preparationFiducials))
        self.loadMeasurement(self.settings.measurementFiducialsCache.get(self.settings.measurementFiducials))
        self.loadGerms(self.settings.germsCache.get(self.settings.germs))
        self.loadLengths(self.settings.lengthsCache.get(self.settings.lengths))
        self.keepFractionBox.setValue(self.settings.keepFraction)
        self.keepSeedBox.setValue(self.settings.keepSeed)
        self.sourceSelect.setCurrentIndex(self.settings.generatorType.value)
        self.GateSequenceEnableCheckBox.setChecked( self.settings.enabled )
        self.GateSequenceFrame.setEnabled( self.settings.enabled )
        self.GateEdit.setText(str(self.settings.gate))
        self.repetitionSpinBox.setValue( self.settings.thisSequenceRepetition )
        self.packWidthCombo.setCurrentIndex(self.packWidthCombo.findText(str(self.settings.packWidth)))
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
        updateComboBoxItems(self.PreparationBox, list(self.settings.preparationFiducialsCache.keys()))
        updateComboBoxItems(self.MeasurementBox, list(self.settings.measurementFiducialsCache.keys()))
        updateComboBoxItems(self.GermsBox, list(self.settings.germsCache.keys()))
        updateComboBoxItems(self.LengthsBox, list(self.settings.lengthsCache.keys()))
        updateComboBoxItems(self.GateSetBox, list(self.settings.gateSetCache.keys()))
        with BlockSignals(self.FullListRadioButton) as w:
            if self.settings.active == self.Mode.FullList:
                self.FullListRadioButton.setChecked(True)
            elif self.settings.active == self.Mode.Gate:
                self.GateRadioButton.setChecked(True)
        self.treeWidget.setParameters(self.settings.plotProperties.parameters())

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
        self.GateSequenceFrame.setEnabled(self.settings.enabled)
        self.sequenceOriginWidget.setEnabled(self.settings.enabled)
        self.sourceSelect.setEnabled(self.settings.enabled)
        self.updateDatastructures()
        self.valueChanged.emit()          
        
    def onDebugChanged(self, state):
        self.settings.debug = state == QtCore.Qt.Checked        
        self.valueChanged.emit()          
        
    def close(self):
        self.config[self.configname] = self.settings
                
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

    def onLoadGeneric(self, combobox, cache_name, loader, message="Open"):
        cache = getattr(self.settings, cache_name)
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, message, self.defaultGateSequencesDir)
        if path:
            filedir, filename = os.path.split(path)
            self.settings.lastDir = filedir
            loader(path)
            if filename not in cache:
                cache[filename] = path
                combobox.addItem(filename)
            combobox.setCurrentIndex(combobox.findText(filename))
        self.valueChanged.emit()

    def loadGateSequenceList(self, path):
        logger = logging.getLogger(__name__)
        self.gateSequenceContainer.load(path)
        if self.gateSequenceContainer._gate_string_list:
            logger.debug("loaded {0} gateSequences from {1}.".format(len(self.gateSequenceContainer._gate_string_list), path))
        _, filename = os.path.split(path)
        self.settings.gateSequence = filename
        self.GateSequenceBox.setCurrentIndex(self.GateSequenceBox.findText(filename))

    def loadGateSet(self, path):
        if path:
            self.gateSequenceContainer.loadGateSet(path)
            _, filename = os.path.split(path)
            self.settings.gateSet = filename
            self.GateSetBox.setCurrentIndex(self.GateSetBox.findText(filename))

    def loadPreparation(self, path_or_literal=None):
        if path_or_literal is None:
            path_or_literal = self.PreparationBox.currentText()
        if path_or_literal:
            file_or_literal = self.gateSequenceContainer.setPreparation(path_or_literal)
            self.settings.preparationFiducials = file_or_literal
            setCurrentComboText(self.PreparationBox, file_or_literal)
            self.settings.preparationFiducialsCache[file_or_literal] = path_or_literal

    def loadMeasurement(self, path_or_literal=None):
        if path_or_literal is None:
            path_or_literal = self.MeasurementBox.currentText()
        if path_or_literal:
            file_or_literal = self.gateSequenceContainer.setMeasurement(path_or_literal)
            self.settings.measurementFiducials = file_or_literal
            setCurrentComboText(self.MeasurementBox, file_or_literal)
            self.settings.measurementFiducialsCache[file_or_literal] = path_or_literal

    def loadGerms(self, path_or_literal=None):
        if path_or_literal is None:
            path_or_literal = self.GermsBox.currentText()
        if path_or_literal:
            file_or_literal = self.gateSequenceContainer.setGerms(path_or_literal)
            self.settings.germs = file_or_literal
            setCurrentComboText(self.GermsBox, file_or_literal)
            self.settings.germsCache[file_or_literal] = path_or_literal

    def loadLengths(self, path_or_literal=None):
        if path_or_literal is None:
            path_or_literal = self.LengthsBox.currentText()
        if path_or_literal:
            file_or_literal = self.gateSequenceContainer.setLengths(path_or_literal)
            self.settings.lengths = file_or_literal
            setCurrentComboText(self.LengthsBox, file_or_literal)
            self.settings.lengthsCache[file_or_literal] = path_or_literal

    def clearGateSequenceList(self):
        self.gateSequenceContainer.loadXml(None)
        self.GateSequenceBox.setCurrentIndex(-1)
    
    def onGateEditChanged(self):
        self.settings.gate = GateString(None, self.GateEdit.text())
        self.GateEdit.setText(str(self.settings.gate))
        self.valueChanged.emit()          
    
    def onRadioButtonToggled(self):
        if self.FullListRadioButton.isChecked():
            self.settings.active = self.Mode.FullList 
        else:
            self.settings.active = self.Mode.Gate   
        self.valueChanged.emit()

    def gateSequenceScanData(self):
        if self._usePyGSTi:
            address, data = self.gateSequenceCompiler.gateSequencesCompile(self.gateSequenceContainer, self.settings.packWidth)
        else:
            if self.settings.active == self.Mode.FullList:
                address, data = self.gateSequenceCompiler.gateSequencesCompile(self.gateSequenceContainer, self.settings.packWidth)
            else:
                self.gateSequenceCompiler.gateCompile(self.gateSequenceContainer.gateDefinition)
                data = self.gateSequenceCompiler.gateSequenceCompile(self.settings.gate, self.settings.packWidth)
                address = [0] * self.settings.thisSequenceRepetition
        return address, data, self.settings
    
    def plaquettes(self):
        if self._usePyGSTi:
            return self.gateSequenceContainer._gate_string_struct._plaquettes
        elif self.settings.active == self.Mode.FullList and self.gateSequenceContainer._gate_string_struct is not None:
            return self.gateSequenceContainer._gate_string_struct._plaquettes
        return None

    def gateString(self, index):
        if self._usePyGSTi:
            if self.gateSequenceContainer.sequenceList is None:
                return None
            return self.gateSequenceContainer.sequenceList[index]
        if self.settings.active == self.Mode.FullList:
            return self.gateSequenceContainer.sequenceList[index]
        else:
            return self.settings.gate

    @property
    def gateStringList(self):
        if self._usePyGSTi:
            if self.gateSequenceContainer.sequenceList is None:
                return None
            return self.gateSequenceContainer.sequenceList
        else:
            if self.settings.active == self.Mode.FullList:
                return self.gateSequenceContainer.sequenceList
            else:
                return [self.settings.gate] * self.settings.thisSequenceRepetition

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

    @property
    def gateSequenceInfo(self):
        if self._usePyGSTi:
            return {'gatestring_list': self.gateStringList, 'plaquettes': self.plaquettes(),
                    'target_gateset' : self.gateSequenceContainer.gateSet,
                    'prepFiducials': self.gateSequenceContainer.prep, 'measFiducials': self.gateSequenceContainer.meas,
                    'germs': self.gateSequenceContainer.germs, 'maxLengths':self.gateSequenceContainer.maxLengths}
        else:
            if self.settings.active == self.Mode.FullList:
                return {'gatestring_list': self.gateStringList, 'plaquettes': self.plaquettes(),
                        'target_gateset': self.gateSequenceContainer.gateSet,
                        'prepFiducials': self.gateSequenceContainer.prep,
                        'measFiducials': self.gateSequenceContainer.meas,
                        'germs': self.gateSequenceContainer.germs, 'maxLengths': self.gateSequenceContainer.maxLengths}
            else:
                return {'gatestring_list': self.gateStringList, 'plaquettes': self.plaquettes(),
                        'target_gateset': self.gateSequenceContainer.gateSet,
                        'prepFiducials': self.gateSequenceContainer.prep,
                        'measFiducials': self.gateSequenceContainer.meas,
                        'germs': self.gateSequenceContainer.germs, 'maxLengths': self.gateSequenceContainer.maxLengths}

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
