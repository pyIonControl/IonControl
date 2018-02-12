# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import copy
import functools
import logging
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from . import ScanList
from gateSequence import GateSequenceUi
from modules.PyqtUtility import BlockSignals
from modules.PyqtUtility import updateComboBoxItems
from modules.Utility import unique
from modules.enum import enum 
from modules.quantity import Q
from modules.ScanDefinition import ScanSegmentDefinition
from .ScanSegmentTableModel import ScanSegmentTableModel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate 
from modules.function_base import linspace
from modules.concatenate_iter import concatenate_iter
import random
from modules.concatenate_iter import interleave_iter
from gateSequence.GateSequenceContainer import GateSequenceException
from modules.firstNotNone import firstNotNone

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ScanControlUi.ui')
ScanControlForm, ScanControlBase = PyQt5.uic.loadUiType(uipath)


class Scan:
    ScanMode = enum('ParameterScan', 'StepInPlace', 'GateSequenceScan', 'Freerunning')
    ScanType = enum('LinearStartToStop', 'LinearStopToStart', 'Randomized', 'CenterOut')
    def __init__(self):
        # Scan
        self.scanParameter = None
        self.parallelInternalScanParameter = "None"
        self.scanTarget = None
        self.start = 0
        self.stop = 0
        self.center = 0
        self.span = 0
        self.steps = 0
        self.stepSize = 1
        self.stepsSelect = 0
        self.scantype = 0
        self.scanMode = 0
        self.filename = ""
        self.histogramFilename = ""
        self.autoSave = True
        self.histogramSave = False
        self.xUnit = ""
        self.xExpression = ""
        self.loadPP = False
        self.loadPPName = ""
        self.saveRawData = False
        self.saveQubitData = False
        self.rawFilename = ""
        self.qubitFilename = ""
        # GateSequence Settings
        self.gateSequenceSettings = GateSequenceUi.Settings()
        self.scanSegmentList = [ScanSegmentDefinition()]
        self.maxPoints = 0
        
    def __setstate__(self, state):
        """this function ensures that the given fields are present in the class object
        after unpickling. Only new class attributes need to be added here.
        """
        self.__dict__ = state
        self.__dict__.setdefault('xUnit', '')
        self.__dict__.setdefault('xExpression', '')
        self.__dict__.setdefault('loadPP', False)
        self.__dict__.setdefault('loadPPName', "")
        self.__dict__.setdefault('stepSize', 1)
        self.__dict__.setdefault('center', 0)
        self.__dict__.setdefault('span', 0)
        self.__dict__.setdefault('gateSequenceSettings', GateSequenceUi.Settings())
        self.__dict__.setdefault('scanSegmentList', [ScanSegmentDefinition()])
        self.__dict__.setdefault('externalScanParameter', None)
        self.__dict__.setdefault('histogramFilename', "")
        self.__dict__.setdefault('histogramSave', False)
        self.__dict__.setdefault('scanTarget', None)
        self.__dict__.setdefault('saveRawData', False)
        self.__dict__.setdefault('rawFilename', "")
        self.__dict__.setdefault('saveQubitData', False)
        self.__dict__.setdefault('qubitDataFormat', 'Pickle')
        self.__dict__.setdefault('maxPoints', 0)
        self.__dict__.setdefault('repeats', 1)
        self.__dict__.setdefault('parallelInternalScanParameter', "None")

    def __eq__(self, other):
        try:
            equal = isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)
        except ValueError:
            equal = False
        return equal

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))
        
    stateFields = ['scanParameter', 'scanTarget', 'scantype', 'scanMode', 'filename', 'histogramFilename',
                   'autoSave', 'histogramSave', 'xUnit', 'xExpression', 'loadPP', 'loadPPName',
                   'gateSequenceSettings', 'scanSegmentList', 'saveRawData', 'rawFilename', 'saveQubitData',
                   'qubitDataFormat', 'maxPoints', 'parallelInternalScanParameter', 'repeats']

    documentationList = ['scanParameter', 'scanTarget', 'scantype', 'scanMode',
                         'xUnit', 'xExpression', 'loadPP', 'loadPPName', 'parallelInternalScanParameter']

    def documentationString(self):
        r = "\r\n".join( [ "{0}\t{1}".format(field, getattr(self, field)) for field in self.documentationList] )
        r += self.gateSequenceSettings.documentationString()
        return r
    
    def description(self):
        desc = dict( ((field, getattr(self, field)) for field in self.documentationList) )
        return desc
    
    def evaluate(self, globalDictionary ):
        return any( [segment.evaluate(globalDictionary) for segment in self.scanSegmentList ] )            


class ScanControlParameters(AttributeComparisonEquality):
    def __init__(self):
        self.autoSave = True
        self.useDefaultFilename = True
        self.useHdf5Filetype = False
        self.currentScanTarget = None
        self.scanTargetCache = dict()
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault( 'currentScanTarget', None )
        self.__dict__.setdefault( 'scanTargetCache', dict() )
        self.__dict__.setdefault( 'useDefaultFilename', True )
        self.__dict__.setdefault('useHdf5Filetype', False)
        if self.scanTargetCache is None:
            self.scanTargetCache = dict()

class ScanControl(ScanControlForm, ScanControlBase ):
    ScanModes = enum('SingleScan', 'StepInPlace', 'GateSequenceScan')
    currentScanChanged = QtCore.pyqtSignal( object )
    integrationMode = enum('IntegrateAll', 'IntegrateRun', 'NoIntegration')
    scanConfigurationListChanged = QtCore.pyqtSignal( object )
    logger = logging.getLogger(__name__)
    def __init__(self, config, globalVariablesUi, parentname, plotnames=None, parent=None, analysisNames=None):
        logger = logging.getLogger(__name__)
        ScanControlForm.__init__(self)
        ScanControlBase.__init__(self, parent)
        self.config = config
        self.configname = 'ScanControl.'+parentname
        self.globalDict = globalVariablesUi.globalDict
        # History and Dictionary
        try:
            self.settingsDict = dict(self.config.items_startswith(self.configname+'.dict.'))
            # if there are no individual entries, try loading the whole dictionary
            if not self.settingsDict:
                self.settingsDict = self.config.get(self.configname+'.dict', dict())
        except (TypeError, AttributeError):
            logger.info( "Unable to read scan control settings dictionary. Setting to empty dictionary." )
            self.settingsDict = dict()
        self.scanConfigurationListChanged.emit( self.settingsDict )
        self.settingsHistory = list()
        self.settingsHistoryPointer = None
        self.historyFinalState = None
        try:
            self.settings = self.config.get(self.configname, Scan())
        except (TypeError, AttributeError):
            logger.info( "Unable to read scan control settings. Setting to new scan." )
            self.settings = Scan()
        self.gateSequenceUi = None
        self.settingsName = self.config.get(self.configname+'.settingsName', '')
        self.pulseProgramUi = None
        self.parameters = self.config.get( self.configname+'.parameters', ScanControlParameters() )
        self.globalVariablesUi = globalVariablesUi
        self.scanTargetDict = dict()
        
    def setupUi(self, parent):
        ScanControlForm.setupUi(self, parent)
        # History and Dictionary
        self.saveButton.clicked.connect( self.onSave )
        self.removeButton.clicked.connect( self.onRemove )
        self.reloadButton.clicked.connect( self.onReload )

        self.tableModel = ScanSegmentTableModel(self.checkSettingsSavable, self.globalDict )
        self.tableView.setModel( self.tableModel )
        self.addSegmentButton.clicked.connect( self.onAddScanSegment )
        self.removeSegmentButton.clicked.connect( self.onRemoveScanSegment )
        self.magnitudeDelegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegate( self.magnitudeDelegate )
        self.tableView.resizeRowsToContents()
               
#        try:
        self.setSettings( self.settings )
#         except AttributeError:
#             logger.error( "Ignoring exception" )
        self.comboBox.addItems( sorted(self.settingsDict.keys()))
        if self.settingsName and self.comboBox.findText(self.settingsName):
            self.comboBox.setCurrentIndex( self.comboBox.findText(self.settingsName) )
        self.comboBox.currentIndexChanged[str].connect( self.onLoad )
        self.comboBox.lineEdit().editingFinished.connect( self.checkSettingsSavable ) 
        # update connections
        self.comboBoxParameter.currentIndexChanged[str].connect( self.onCurrentTextChanged )
        self.parallelInternalScanComboBox.currentIndexChanged[str].connect(self.onCurrentParallelScanChanged)
        self.scanTypeCombo.currentIndexChanged[int].connect( functools.partial(self.onCurrentIndexChanged, 'scantype') )
        self.autoSaveCheckBox.stateChanged.connect( functools.partial(self.onStateChanged, 'autoSave') )
        self.saveRawCheckBox.stateChanged.connect( functools.partial(self.onStateChanged, 'saveRawData') )
        self.saveQubitCheckBox.stateChanged.connect( functools.partial(self.onStateChanged, 'saveQubitData'))
        self.histogramSaveCheckBox.stateChanged.connect( functools.partial(self.onStateChanged, 'histogramSave') )
        self.scanModeComboBox.currentIndexChanged[int].connect( self.onModeChanged )
        self.filenameEdit.editingFinished.connect( functools.partial(self.onEditingFinished, self.filenameEdit, 'filename') )
        self.rawFilenameEdit.editingFinished.connect( functools.partial(self.onEditingFinished, self.rawFilenameEdit, 'rawFilename') )
        self.qubitDataFormatBox.currentIndexChanged[str].connect(self.onQubitDataFormatChanged)
        self.histogramFilenameEdit.editingFinished.connect( functools.partial(self.onEditingFinished, self.histogramFilenameEdit, 'histogramFilename') )
        self.xUnitEdit.editingFinished.connect( functools.partial(self.onEditingFinished, self.xUnitEdit, 'xUnit') )
        self.xExprEdit.editingFinished.connect( functools.partial(self.onEditingFinished, self.xExprEdit, 'xExpression') )
        self.maxPointsBox.valueChanged.connect(partial(self.onSetIntField, 'maxPoints'))
        self.repeatsBox.valueChanged.connect(partial(self.onSetIntField, 'repeats'))
        self.loadPPcheckBox.stateChanged.connect( functools.partial(self.onStateChanged, 'loadPP' ) )
        self.loadPPComboBox.currentIndexChanged[str].connect( self.onLoadPP )
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )

        self.autoSaveAction = QtWidgets.QAction( "auto save", self)
        self.autoSaveAction.setCheckable(True)
        self.autoSaveAction.setChecked(self.parameters.autoSave )
        self.autoSaveAction.triggered.connect( self.onAutoSave )
        self.addAction( self.autoSaveAction )

        self.settings.evaluate(self.globalDict)
        self.globalVariablesUi.valueChanged.connect( self.evaluate )
        self.comboBoxScanTarget.currentIndexChanged[str].connect( self.onChangeScanTarget )
        self.currentScanChanged.emit( self.settingsName )

        self.defaultFilenameAction = QtWidgets.QAction('Use default filename', self)
        self.defaultFilenameAction.setCheckable(True)
        self.defaultFilenameAction.setChecked(self.parameters.useDefaultFilename)
        self.defaultFilenameAction.triggered.connect(self.onDefaultFilename)
        self.addAction(self.defaultFilenameAction)
        self.defaultHdf5TypeAction = QtGui.QAction('Use hdf5 as default file type', self)
        self.defaultHdf5TypeAction.setCheckable(True)
        self.defaultHdf5TypeAction.setChecked(self.parameters.useHdf5Filetype)
        self.defaultHdf5TypeAction.triggered.connect(self.onDefaultHdf5Type)
        self.addAction(self.defaultHdf5TypeAction)
        self.onDefaultFilename()
        self.parallelInternalScanComboBox.setVisible(self.parameters.currentScanTarget != "Internal")

    def onQubitDataFormatChanged(self, f):
        self.settings.qubitDataFormat = f

    def evaluate(self, name):
        if self.settings.evaluate( self.globalDict ):
            self.tableModel.update()
            self.tableView.viewport().repaint()
        
    def onAutoSave(self, checked):
        self.parameters.autoSave = checked
        if self.parameters.autoSave:
            self.onSave()

    @QtCore.pyqtSlot(bool)
    def onDefaultFilename(self, checked=None):
        if checked is not None:
            self.parameters.useDefaultFilename = checked
        if self.parameters.useDefaultFilename:
            self.settings.filename = self.settingsName if self.settingsName else 'untitled'
            if self.parameters.useHdf5Filetype:
                self.settings.filename += '.hdf5'
            self.filenameEdit.setText(self.settings.filename)
            self.filenameEdit.setDisabled(True)
        else:
            self.filenameEdit.setDisabled(False)

    @QtCore.pyqtSlot(bool)
    def onDefaultHdf5Type(self, checked):
        self.parameters.useHdf5Filetype = checked
        self.onDefaultFilename()

    def onAddScanSegment(self):
        self.settings.scanSegmentList.append( ScanSegmentDefinition() )
        self.tableModel.setScanList(self.settings.scanSegmentList)
        
    def onRemoveScanSegment(self):
        for index in sorted(unique([ i.column() for i in self.tableView.selectedIndexes() ]), reverse=True):
            del self.settings.scanSegmentList[index]
            self.tableModel.setScanList(self.settings.scanSegmentList)
        
    def setSettings(self, settings):
        self.settings = copy.deepcopy(settings)
        if self.globalDict:
            self.settings.evaluate(self.globalDict)
        self.scanModeComboBox.setCurrentIndex( self.settings.scanMode )
        self.scanTypeCombo.setCurrentIndex(self.settings.scantype )
        self.autoSaveCheckBox.setChecked(self.settings.autoSave)
        self.saveRawCheckBox.setChecked(self.settings.saveRawData)
        self.saveQubitCheckBox.setChecked(self.settings.saveQubitData)
        self.histogramSaveCheckBox.setChecked(self.settings.histogramSave)
        if self.settings.scanTarget:
            self.settings.scanParameter = self.doChangeScanTarget(self.settings.scanTarget, self.settings.scanParameter)
        elif self.comboBoxScanTarget.count()>0:
            self.settings.scanTarget = str( self.comboBoxScanTarget.currentText() )
            self.settings.scanParameter = self.doChangeScanTarget(self.settings.scanTarget, None)
        if self.settings.parallelInternalScanParameter:
            updateComboBoxItems(self.parallelInternalScanComboBox, self.scanTargetDict.get('Internal'), self.settings.parallelInternalScanParameter)
        filename = getattr(self.settings, 'filename', '')
        self.filenameEdit.setText(filename if filename else '')
        self.rawFilenameEdit.setText( getattr(self.settings, 'rawFilename', '') )
        self.qubitDataFormatBox.setCurrentIndex(self.qubitDataFormatBox.findText(getattr(self.settings, 'qubitDataFormat', 'Pickle')))
        self.histogramFilenameEdit.setText( getattr(self.settings, 'histogramFilename', '') )
        self.scanTypeCombo.setEnabled(self.settings.scanMode in [0, 1])
        self.xUnitEdit.setText(self.settings.xUnit)
        self.xExprEdit.setText(self.settings.xExpression)
        self.maxPointsBox.setValue(self.settings.maxPoints)
        self.repeatsBox.setValue(self.settings.repeats)
        self.qubitDataFormatBox.setCurrentIndex(self.qubitDataFormatBox.findText(self.settings.qubitDataFormat))

        self.loadPPcheckBox.setChecked( self.settings.loadPP )
        if self.settings.loadPPName: 
            index = self.loadPPComboBox.findText(self.settings.loadPPName)
            if index>=0:
                self.loadPPComboBox.setCurrentIndex( index )
                self.onLoadPP(self.settings.loadPPName)
        self.onModeChanged(self.settings.scanMode)
        if self.gateSequenceUi:
            self.gateSequenceUi.setSettings( self.settings.gateSequenceSettings )
        self.checkSettingsSavable()
        self.tableModel.setScanList(self.settings.scanSegmentList)

    def checkSettingsSavable(self, savable=None):
        if not isinstance(savable, bool):
            currentText = str(self.comboBox.currentText())
            try:
                if currentText is None or currentText=="":
                    savable = False
                elif self.settingsName and self.settingsName in self.settingsDict:
                    savable = self.settingsDict[self.settingsName]!=self.settings or currentText!=self.settingsName
                else:
                    savable = True
                if self.parameters.autoSave and savable:
                    self.onSave()
                    savable = False
            except ValueError:
                pass
        self.saveButton.setEnabled( savable )
            
    def onLoadPP(self, ppname):
        logger = logging.getLogger(__name__)
        self.settings.loadPPName = str(ppname)
        logger.debug( "ScanControl.onLoadPP {0} {1} {2}".format( self.settings.loadPP, bool(self.settings.loadPPName), self.settings.loadPPName ) )
        if self.settings.loadPP and self.settings.loadPPName and hasattr(self, "pulseProgramUi"):
            self.pulseProgramUi.loadContextByName( self.settings.loadPPName )
        self.checkSettingsSavable()
            
    def onRecentPPFilesChanged(self, namelist):
        updateComboBoxItems( self.loadPPComboBox, sorted( namelist ) )
        self.checkSettingsSavable()
        
    def setPulseProgramUi(self, pulseProgramUi ):
        logger = logging.getLogger(__name__)
        logger.debug( "ScanControl.setPulseProgramUi {0}".format(list(pulseProgramUi.configParams.recentFiles.keys())) )
        isStartup = self.pulseProgramUi is None
        self.pulseProgramUi = pulseProgramUi
        updateComboBoxItems(self.loadPPComboBox, sorted(pulseProgramUi.contextDict.keys()), self.settings.loadPPName)
        try:
            self.pulseProgramUi.contextDictChanged.connect( self.onRecentPPFilesChanged, QtCore.Qt.UniqueConnection )
        except TypeError:
            pass  # is raised if the connection already existed
            

        if not self.gateSequenceUi:
            self.gateSequenceUi = GateSequenceUi.GateSequenceUi()
            self.gateSequenceUi.valueChanged.connect( self.checkSettingsSavable )
            self.gateSequenceUi.postInit('test', self.config, self.pulseProgramUi.pulseProgram )
            self.gateSequenceUi.setupUi(self.gateSequenceUi)
            self.toolBox.addItem(self.gateSequenceUi, "Gate Sequences")
        if pulseProgramUi.currentContext.parameters:
            self.gateSequenceUi.setVariables( pulseProgramUi.currentContext.parameters )
        try:
            self.gateSequenceUi.setSettings( self.settings.gateSequenceSettings )
        except GateSequenceException as e:
            logger.exception(e)
        if isStartup:
            self.onLoadPP(self.settings.loadPPName)

    def onEditingFinished(self, edit, attribute):        
        setattr( self.settings, attribute, str(edit.text())  )        
        self.checkSettingsSavable()
                
    def onStateChanged(self, attribute, state):        
        setattr( self.settings, attribute, (state == QtCore.Qt.Checked)  )        
        self.checkSettingsSavable()
        
    def onCurrentTextChanged(self, text):        
        self.settings.scanParameter = str(text)        
        self.checkSettingsSavable()

    def onCurrentParallelScanChanged(self, text):
        self.settings.parallelInternalScanParameter = str(text)
        self.checkSettingsSavable()

    def onCurrentIndexChanged(self, attribute, index):        
        setattr( self.settings, attribute, index )        
        self.checkSettingsSavable()

    def onSetIntField(self, field, value):
        setattr(self.settings, field, int(value))
        self.checkSettingsSavable()

    def onModeChanged(self, index):       
        self.settings.scanMode = index
        self.scanTypeCombo.setEnabled(index in [0, 2])
        self.xUnitEdit.setEnabled( index in [0, 3] )
        self.xExprEdit.setEnabled( index in [0, 3] )
        self.comboBoxParameter.setEnabled( index==0 )
        self.comboBoxScanTarget.setEnabled( index==0 )
        self.addSegmentButton.setEnabled( index==0 )
        self.removeSegmentButton.setEnabled( index==0 )
        self.tableView.setEnabled( index==0 )
        self.maxPointsLabel.setVisible( index==1 )
        self.maxPointsBox.setVisible( index==1 )
        self.checkSettingsSavable()
        self.parallelInternalScanComboBox.setEnabled(index==0)
    
    def onValueChanged(self, attribute, value):        
        setattr(self.settings, attribute, Q(value))
        self.checkSettingsSavable()

    def onBareValueChanged(self, attribute, value):        
        setattr( self.settings, attribute, value )        
        self.checkSettingsSavable()
              
    def onIntValueChanged(self, attribute, value):       
        setattr( self.settings, attribute, value )        
        self.checkSettingsSavable()
        
    def setVariables(self, variabledict):
        self.updateScanTarget('Internal', sorted(var.name for var in variabledict.values() if var.type=='parameter'))
        self.variabledict = variabledict
        if self.settings.scanParameter:
            self.comboBoxParameter.setCurrentIndex(self.comboBoxParameter.findText(self.settings.scanParameter) )
        elif self.comboBoxParameter.count()>0:  # if scanParameter is None set it to the current selection
            self.settings.scanParameter = str(self.comboBoxParameter.currentText())
        if self.settings.parallelInternalScanParameter:   # TODO:
            self.parallelInternalScanComboBox.setCurrentIndex(self.parallelInternalScanComboBox.findText(self.settings.parallelInternalScanParameter))
        if self.gateSequenceUi:
            self.gateSequenceUi.setVariables(variabledict)
        self.checkSettingsSavable()
            
    def updateScanTarget(self, target, scannames):
        if target=="Internal":
            extended = ["None"]
            extended.extend(sorted(scannames))
        else:
            extended = sorted(scannames)
        self.scanTargetDict[target] = extended
        updateComboBoxItems( self.comboBoxScanTarget, list(self.scanTargetDict.keys()), self.parameters.currentScanTarget )
        self.parameters.currentScanTarget = firstNotNone(self.parameters.currentScanTarget, target)
        if target==self.parameters.currentScanTarget:
            self.settings.scanParameter = str(updateComboBoxItems( self.comboBoxParameter, self.scanTargetDict[target], self.settings.scanParameter ))
        if not self.settings.scanTarget:
            self.settings.scanTarget = self.parameters.currentScanTarget
        if target=="Internal":
            updateComboBoxItems(self.parallelInternalScanComboBox, self.scanTargetDict[target], self.settings.parallelInternalScanParameter)

    def onChangeScanTarget(self, name):
        """ called on currentIndexChanged[QString] signal of ComboBox"""
        name = str(name)
        if name!=self.parameters.currentScanTarget:
            self.parameters.scanTargetCache[self.parameters.currentScanTarget] = self.settings.scanParameter
            cachedParam = self.parameters.scanTargetCache.get(name)
            cachedParam = updateComboBoxItems( self.comboBoxParameter, sorted(self.scanTargetDict[name]), cachedParam )
            self.settings.scanParameter = cachedParam
            self.settings.scanTarget = name
            self.parameters.currentScanTarget = name
        self.parallelInternalScanComboBox.setVisible(name!="Internal")
        self.checkSettingsSavable()

    def doChangeScanTarget(self, name, scanParameter):
        """ Change the scan target as part of loading a parameter set,
        we know the ScanParameter to select and want it either selected or added as red item """
        name = str(name)
        if name!=self.parameters.currentScanTarget:
            with BlockSignals(self.comboBoxScanTarget):
                self.comboBoxScanTarget.setCurrentIndex( self.comboBoxScanTarget.findText(name) )
            targets = self.scanTargetDict.get(name)
            if targets is not None:
                targets = sorted(targets)
            scanParameter = updateComboBoxItems(self.comboBoxParameter, targets , scanParameter)
            self.settings.scanTarget = name
            self.parameters.currentScanTarget = name
        else:
            self.comboBoxParameter.setCurrentIndex( self.comboBoxParameter.findText(scanParameter) )
        self.checkSettingsSavable()
        return scanParameter
                
    def getScan(self):
        scan = copy.deepcopy(self.settings)
        if scan.scanMode!=0:
            scan.scanTarget = 'Internal'
        scan.scanTarget = str(scan.scanTarget)
        scan.type = [ ScanList.ScanType.LinearUp, ScanList.ScanType.LinearDown, ScanList.ScanType.Randomized, ScanList.ScanType.CenterOut][self.settings.scantype]
        
        if scan.scanMode==Scan.ScanMode.Freerunning:
            scan.list = None
        else:
            scan.list = list(concatenate_iter(*[linspace(segment.start, segment.stop, segment.steps) for segment in scan.scanSegmentList]))
            scan.singleScanLength = len(scan.list)
            if scan.type==0:
                scan.list = sorted( scan.list )
                scan.start = scan.list[0]
                scan.stop = scan.list[-1]
            elif scan.type==1:
                scan.list = sorted( scan.list, reverse=True )
                scan.start = scan.list[-1]
                scan.stop = scan.list[0]
            elif scan.type==2:
                scan.list = sorted( scan.list )
                scan.start = scan.list[0]
                scan.stop = scan.list[-1]
                random.shuffle( scan.list )
            elif scan.type==3:        
                scan.list = sorted( scan.list )
                center = len(scan.list)//2
                scan.list = list( interleave_iter(scan.list[center:], reversed(scan.list[:center])) )
            scan.list *= scan.repeats
        scan.gateSequenceUi = self.gateSequenceUi
        scan.settingsName = self.settingsName
        return scan
        
    def saveConfig(self):
        self.config[self.configname] = self.settings
        for e in self.settingsDict.values():
            e.scanTarget = str(e.scanTarget)
            e.scanParameter = str(e.scanParameter)
        self.config.set_string_dict(self.configname+'.dict', self.settingsDict)
        self.config[self.configname+'.settingsName'] = self.settingsName
        self.config[self.configname+'.parameters'] = self.parameters

    def onSave(self):
        self.settingsName = str(self.comboBox.currentText())
        if self.settingsName != '':
            if self.settingsName not in self.settingsDict:
                if self.comboBox.findText(self.settingsName)==-1:
                    self.comboBox.addItem(self.settingsName)
            self.settingsDict[self.settingsName] = copy.deepcopy(self.settings)
            self.scanConfigurationListChanged.emit( self.settingsDict )
        self.checkSettingsSavable(savable=False)
        self.currentScanChanged.emit( self.settingsName )

    def onRemove(self):
        name = str(self.comboBox.currentText())
        if name != '':
            if name in self.settingsDict:
                self.settingsDict.pop(name)
            idx = self.comboBox.findText(name)
            if idx>=0:
                self.comboBox.removeItem(idx)
            self.scanConfigurationListChanged.emit( self.settingsDict )
       
    def onLoad(self, name):
        self.settingsName = str(name)
        if self.settingsName !='' and self.settingsName in self.settingsDict:
            self.setSettings(self.settingsDict[self.settingsName])
        if self.parameters.useDefaultFilename:
            self.settings.filename = self.settingsName
            self.filenameEdit.setText(self.settingsName)
        self.checkSettingsSavable()
        self.currentScanChanged.emit( self.settingsName )

    def loadSetting(self, name):
        if name and self.comboBox.findText(name)>=0:
            self.comboBox.setCurrentIndex( self.comboBox.findText(name) )  
            self.onLoad(name)      

    def onReload(self):
        self.onLoad( self.comboBox.currentText() )
   
    def documentationString(self):
        return self.settings.documentationString()
    
    def editEvaluationTable(self, index):
        if index.column() in [0, 1, 2, 4]:
            self.evalTableView.edit(index)
            

if __name__=="__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = ScanControl(config, "parent")
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
        
