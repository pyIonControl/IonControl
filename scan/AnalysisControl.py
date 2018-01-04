# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import PyQt5.uic
import logging

import numpy

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from modules.SequenceDict import SequenceDict
from scan.AnalysisTableModel import AnalysisTableModel             #@UnresolvedImport
from modules.GuiAppearance import saveGuiState, restoreGuiState    #@UnresolvedImport
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from scan.PushVariable import PushVariable                         #@UnresolvedImport
from modules.Utility import unique
import copy
from PyQt5 import QtCore, QtGui, QtWidgets
from scan.PushVariableTableModel import PushVariableTableModel     #@UnresolvedImport
from scan.DatabasePushDestination import DatabasePushDestination   #@UnresolvedImport
from fit.FitUiTableModel import FitUiTableModel
from fit.FitResultsTableModel import FitResultsTableModel
from fit.FitFunctionBase import fitFunctionMap
from fit.StoredFitFunction import StoredFitFunction                #@UnresolvedImport
from modules.PyqtUtility import BlockSignals, Override, updateComboBoxItems
from itertools import cycle
from modules.flatten import flattenAll

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/AnalysisControl.ui')
ControlForm, ControlBase = PyQt5.uic.loadUiType(uipath)

class AnalysisDefinitionElement(object):
    def __init__(self):
        self.name = ''
        self.enabled = True
        self.evaluation = None
        self.fitfunctionName = None
        self.pushVariables = SequenceDict()
        self.fitfunction = None
        self.fitfunctionCache = dict()
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('name', '')
        
    stateFields = ['name', 'enabled', 'evaluation', 'fitfunctionName', 'pushVariables', 'fitfunction', 'fitfunctionCache'] 
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))
    
    def pushVariableValues(self):
        """get all push variable values that are within the bounds, no re-evaluation"""
        pushVarValues = list()
        failedList = []
        for pushvar in list(self.pushVariables.values()):
            pushRecord, failedRecord = pushvar.pushRecord()
            failedList.extend( failedRecord )
            pushVarValues.extend( pushRecord )
        return pushVarValues, failedList
    
    def updatePushVariables(self, replacements ):
        for pushvar in self.pushVariables.values():
            pushvar.evaluate( replacements )
            
class AnalysisControlParameters(AttributeComparisonEquality):
    def __init__(self):
        self.autoSave = True

class AnalysisControl(ControlForm, ControlBase ):
    analysisConfigurationChanged = QtCore.pyqtSignal( object )
    currentAnalysisChanged = QtCore.pyqtSignal( object )
    analysisResultSignal = QtCore.pyqtSignal( object )
    def __init__(self, config, globalDict, parentname, evaluationNames, parent=None):
        ControlForm.__init__(self)
        ControlBase.__init__(self, parent)
        self.config = config
        self.configname = 'AnalysisControl.'+parentname
        self.globalDict = globalDict
        self.evaluationNames = evaluationNames
        # History and Dictionary
        try:
            self.analysisDefinitionDict = dict(self.config.items_startswith(self.configname + '.dict.'))
            if not self.analysisDefinitionDict:
                self.analysisDefinitionDict = self.config.get(self.configname+'.dict', dict())
        except TypeError:
            logging.getLogger(__name__).info( "Unable to read analysis control settings dictionary. Setting to empty dictionary." )
            self.analysisDefinitionDict = dict()
        self.analysisDefinitionDict.setdefault('', list() )  # add empty analysis
        try:
            self.analysisDefinition = self.config.get(self.configname, list())
        except Exception:
            logging.getLogger(__name__).info( "Unable to read analysis control settings. Setting to new analysis." )
            self.analysisDefinition = list()
        self.pushDestinations = dict()
        self.currentAnalysisName =  self.config.get(self.configname+'.settingsName', None)
        self.currentEvaluation = None
        self.currentEvaluationIndex = None
        self.fitfunction = None
        self.plottedTraceDict = None
        self.parameters = self.config.get( self.configname+'.parameters', AnalysisControlParameters() )
        
    def setupUi(self, parent):
        ControlForm.setupUi(self, parent)
        # History and Dictionary
        self.removeAnalysisConfigurationButton.clicked.connect( self.onRemoveAnalysisConfiguration )
        self.saveButton.clicked.connect( self.onSave )
        self.reloadButton.clicked.connect( self.onReload )
        self.addAnalysisButton.clicked.connect( self.onAddAnalysis )
        self.removeAnalysisButton.clicked.connect( self.onRemoveAnalysis )
        self.addPushButton.clicked.connect( self.onAddPushVariable )
        self.removePushButton.clicked.connect( self.onRemovePushVariable )
        self.pushButton.clicked.connect( self.onPush )
        self.fitButton.clicked.connect( self.onFit )
        self.fitAllButton.clicked.connect( self.onFitAll )
        self.plotButton.clicked.connect( self.onPlot )
        self.removePlotButton.clicked.connect( self.onRemoveFit )
        self.extractButton.clicked.connect( self.onExtractFit )
        self.fitToStartButton.clicked.connect( self.onFitToStart )
        self.getSmartStartButton.clicked.connect( self.onSmartToStart )
        self.checkBoxUseSmartStartValues.stateChanged.connect( self.onUseSmartStart )
        self.useErrorBarsCheckBox.stateChanged.connect( self.onUseErrorBars )
        self.analysisComboDelegate = ComboBoxDelegate()
        self.analysisTableModel = AnalysisTableModel(self.analysisDefinition, self.config, self.globalDict, self.evaluationNames )
        self.analysisTableModel.fitfunctionChanged.connect( self.onFitfunctionChanged )
        self.analysisTableModel.analysisChanged.connect( self.autoSave )
        self.analysisTableView.setModel( self.analysisTableModel )
        self.analysisTableView.selectionModel().currentChanged.connect( self.onActiveAnalysisChanged )
        self.analysisTableView.setItemDelegateForColumn(2, self.analysisComboDelegate)
        self.analysisTableView.setItemDelegateForColumn(3, self.analysisComboDelegate)
        self.pushTableModel = PushVariableTableModel(self.config, self.globalDict)
        self.pushTableModel.pushChanged.connect( self.autoSave )
        self.pushTableView.setModel( self.pushTableModel )
        self.pushItemDelegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.pushComboDelegate = ComboBoxDelegate()
        for column in range(1, 3):
            self.pushTableView.setItemDelegateForColumn(column, self.pushComboDelegate)
        for column in range(3, 7):
            self.pushTableView.setItemDelegateForColumn(column, self.pushItemDelegate)
        self.pushDestinations['Database'] = DatabasePushDestination('fit')

        self.analysisConfigurationComboBox.addItems( sorted([ key for key in self.analysisDefinitionDict.keys() if key ]) )
        if self.currentAnalysisName in self.analysisDefinitionDict:
            self.analysisConfigurationComboBox.setCurrentIndex( self.analysisConfigurationComboBox.findText(self.currentAnalysisName))
        else:
            self.currentAnalysisName = str( self.analysisConfigurationComboBox.currentText() )
        self.analysisConfigurationComboBox.currentIndexChanged[str].connect( self.onLoadAnalysisConfiguration )
        self.analysisConfigurationComboBox.lineEdit().editingFinished.connect( self.onConfigurationEditingFinished ) 
        self.analysisConfigurationChanged.emit( self.analysisDefinitionDict )

        # FitUi
        self.fitfunctionTableModel = FitUiTableModel(self.config)
        self.parameterTableView.setModel(self.fitfunctionTableModel)
        self.fitfunctionTableModel.parametersChanged.connect( self.autoSave )
        self.magnitudeDelegate = MagnitudeSpinBoxDelegate(self.globalDict, emptyStringValue=None)
        self.parameterTableView.setItemDelegateForColumn(2, self.magnitudeDelegate)
        self.parameterTableView.setItemDelegateForColumn(3, self.magnitudeDelegate)
        self.parameterTableView.setItemDelegateForColumn(4, self.magnitudeDelegate)
        self.fitResultsTableModel = FitResultsTableModel(self.config)
        self.resultsTableView.setModel(self.fitResultsTableModel)
        restoreGuiState( self, self.config.get(self.configname+'.guiState') )
        self.setButtonEnabledState()
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.autoSaveAction = QtWidgets.QAction( "auto save", self)
        self.autoSaveAction.setCheckable(True)
        self.autoSaveAction.setChecked(self.parameters.autoSave )
        self.autoSaveAction.triggered.connect( self.onAutoSave )
        self.addAction( self.autoSaveAction )
        self.autoSave()
        self.currentAnalysisChanged.emit( self.currentAnalysisName )

        # setup actions for copying fit results/parameters from their respective tables
        self.parameterTableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.parameterTableView.customContextMenuRequested.connect(self.parameterRightClickMenu)
        self.resultsTableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.resultsTableView.customContextMenuRequested.connect(self.resultsRightClickMenu)
        self.copyResultsAction = QtWidgets.QAction("copy to clipboard", self)
        self.copyResultsAction.triggered.connect(lambda: self.copyToClipboard(self.resultsTableView, self.fitResultsTableModel))
        self.copyParameterAction = QtWidgets.QAction("copy to clipboard", self)
        self.copyParameterAction.triggered.connect(lambda: self.copyToClipboard(self.parameterTableView, self.fitfunctionTableModel))
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self.parameterTableView, lambda: self.copyToClipboard(self.parameterTableView, self.fitfunctionTableModel), context=QtCore.Qt.WidgetWithChildrenShortcut)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self.resultsTableView, lambda: self.copyToClipboard(self.resultsTableView, self.fitResultsTableModel), context=QtCore.Qt.WidgetWithChildrenShortcut)


    def onUseErrorBars(self, state):
        if self.fitfunction is not None:
            self.fitfunction.useErrorBars = state==QtCore.Qt.Checked
            self.currentEvaluation.fitfunction = StoredFitFunction.fromFitfunction(self.fitfunction)
            self.autoSave()        
        
    def onConfigurationEditingFinished(self):
        self.currentAnalysisName = str(self.analysisConfigurationComboBox.currentText())
        self.autoSave()
        self.currentAnalysisChanged.emit( self.currentAnalysisName )

    def onUseSmartStart(self, state):
        if self.fitfunction is not None:
            self.fitfunction.useSmartStartValues = state==QtCore.Qt.Checked
            self.currentEvaluation.fitfunction = StoredFitFunction.fromFitfunction(self.fitfunction)
            self.autoSave()

    def setButtonEnabledState(self):
        allEnable = self.plottedTraceDict is not None
        currentEnable = self.plottedTraceDict is not None and self.currentEvaluation is not None and self.currentEvaluation.evaluation in self.plottedTraceDict
        self.fitAllButton.setEnabled( allEnable )
        self.getSmartStartButton.setEnabled( currentEnable )
        self.fitButton.setEnabled( currentEnable ) 
        self.plotButton.setEnabled( currentEnable )
        self.removePlotButton.setEnabled( currentEnable )
        self.extractButton.setEnabled( currentEnable )
            
    def onFitfunctionChanged(self, row, newfitname ):
        """Swap out the fitfunction on the current analysis"""
        if self.fitfunction:
            self.currentEvaluation.fitfunctionCache[self.fitfunction.name] = StoredFitFunction.fromFitfunction( self.fitfunction )
        self.currentEvaluation.fitfunctionName = newfitname
        if newfitname in self.currentEvaluation.fitfunctionCache:
            self.currentEvaluation.fitfunction = self.currentEvaluation.fitfunctionCache[newfitname]
            self.setFitfunction(  self.currentEvaluation.fitfunction.fitfunction() )
        else:
            self.setFitfunction( fitFunctionMap[newfitname]() )
            self.currentEvaluation.fitfunction = StoredFitFunction.fromFitfunction(self.fitfunction)
        self.pushTableModel.setPushVariables(self.currentEvaluation.pushVariables, self.fitfunction)
            
    def onActiveAnalysisChanged(self, selected, deselected=None):
        if deselected and self.fitfunction:
            self.currentEvaluation.fitfunction = StoredFitFunction.fromFitfunction(self.fitfunction)
        if selected.row()>=0:
            self.currentEvaluation = self.analysisDefinition[selected.row()] if self.analysisDefinition else None
            self.currentEvaluationIndex = selected.row() if self.analysisDefinition else None
            self.currentEvaluationLabel.setText( self.currentEvaluation.name if self.currentEvaluation else "" )
            if self.currentEvaluation and self.currentEvaluation.fitfunction:
                self.setFitfunction( self.currentEvaluation.fitfunction.fitfunction() )
            else:
                self.setFitfunction( None )
            self.pushTableModel.setPushVariables(self.currentEvaluation.pushVariables if self.currentEvaluation else None, self.fitfunction)
        else:
            self.currentEvaluation = None
            self.currentEvaluationIndex = None
            self.currentEvaluationLabel.setText( "" )
            self.setFitfunction( None )
            self.pushTableModel.setPushVariables( None, self.fitfunction)
        self.setButtonEnabledState()
                       
    def onRemoveAnalysis(self):
        for index in sorted(unique([ i.row() for i in self.analysisTableView.selectedIndexes() ]), reverse=True):
            self.analysisTableModel.removeAnalysis(index)
        self.autoSave()
            
    def onAddAnalysis(self):
        self.analysisTableModel.addAnalysis( AnalysisDefinitionElement() )
        self.autoSave()
       
    def onAddPushVariable(self):
        self.pushTableModel.addVariable( PushVariable() )
        self.autoSave()
    
    def onRemovePushVariable(self):
        for index in sorted(unique([ i.row() for i in self.pushTableView.selectedIndexes() ]), reverse=True):
            self.pushTableModel.removeVariable(index)
        self.autoSave()

    def addPushDestination(self, name, destination ):
        self.pushDestinations[name] = destination
        self.pushTableModel.updateDestinations(self.pushDestinations )

    def onPush(self):
        self.push(self.currentEvaluation)

    def push(self, evaluation ):
        pushVarValues, failedList = evaluation.pushVariableValues()
        for destination, variable, value in pushVarValues:
            if destination in self.pushDestinations:
                self.pushDestinations[destination].update( [(destination, variable, value)] )
        return failedList
                
    def pushAll(self):
        failedList = []
        for analysis in self.analysisDefinition:    
            failedList.extend( self.push( analysis ))
        return failedList 
                
    def pushVariables(self, pushVariables):
        for destination, variable, value in pushVariables:
            if destination in self.pushDestinations:
                self.pushDestinations[destination].update( [(destination, variable, value)] )

    def onAutoSave(self, checked):
        self.parameters.autoSave = checked
        self.autoSave()
        
    def autoSave(self):
        if self.parameters.autoSave:
            if self.currentEvaluation is not None and self.fitfunction is not None:
                self.currentEvaluation.fitfunction = StoredFitFunction.fromFitfunction( self.fitfunction )
            self.onSave()
            self.saveButton.setEnabled( False )
        else:
            self.saveButton.setEnabled( self.saveable() )
            
    def saveable(self):
        if self.currentEvaluation is not None and self.fitfunction is not None:
            self.currentEvaluation.fitfunction = StoredFitFunction.fromFitfunction( self.fitfunction )
        return self.currentAnalysisName != '' and ( self.currentAnalysisName not in self.analysisDefinitionDict or not (self.analysisDefinitionDict[self.currentAnalysisName] == self.analysisDefinition))            
                
    def saveConfig(self):
        self.config.set_string_dict(self.configname + '.dict', self.analysisDefinitionDict)
        self.config[self.configname] = self.analysisDefinition
        self.config[self.configname+'.settingsName'] = self.currentAnalysisName
        self.config[self.configname+'.guiState'] = saveGuiState( self )
        self.config[self.configname+'.parameters'] = self.parameters
    
    def onSave(self):
        if self.currentAnalysisName != '':
            if self.currentAnalysisName not in self.analysisDefinitionDict or self.analysisDefinition != self.analysisDefinitionDict[self.currentAnalysisName]:
                logging.getLogger(__name__).debug("Saving Analysis '{0}' '{1}'".format(self.currentAnalysisName, self.analysisDefinition[0].name if self.analysisDefinition else ""))
                self.analysisDefinitionDict[self.currentAnalysisName] = copy.deepcopy(self.analysisDefinition)
                if self.analysisConfigurationComboBox.findText(self.currentAnalysisName)==-1:
                    updateComboBoxItems(self.analysisConfigurationComboBox, sorted([ key for key in self.analysisDefinitionDict.keys() if key ]))
                self.saveButton.setEnabled( False )
                self.analysisConfigurationChanged.emit( self.analysisDefinitionDict )
        
    def onRemoveAnalysisConfiguration(self):
        if self.currentAnalysisName != '':
            if self.currentAnalysisName in self.analysisDefinitionDict:
                self.analysisDefinitionDict.pop(self.currentAnalysisName)
            idx = self.analysisConfigurationComboBox.findText(self.currentAnalysisName)
            if idx>=0:
                self.analysisConfigurationComboBox.removeItem(idx)
            self.analysisConfigurationChanged.emit( self.analysisDefinitionDict )
       
    def onLoadAnalysisConfiguration(self, name):
        name = str(name)
        if name is not None and name in self.analysisDefinitionDict:
            with Override( self.parameters, 'autoSave', False):
                self.currentAnalysisName = name
                self.setAnalysisDefinition( self.analysisDefinitionDict[name] )
                self.onActiveAnalysisChanged(self.analysisTableModel.createIndex(0, 0) )
                if self.analysisConfigurationComboBox.currentText()!=name:
                    with BlockSignals(self.analysisConfigurationComboBox):
                        self.analysisConfigurationComboBox.setCurrentIndex( self.analysisConfigurationComboBox.findText(name) )
                logging.getLogger(__name__).debug("Loaded Analysis '{0}' '{1}'".format(self.currentAnalysisName, self.analysisDefinition[0].name if self.analysisDefinition else ""))                    
                self.currentAnalysisChanged.emit( self.currentAnalysisName )
            self.autoSave()

    def setAnalysisDefinition(self, analysisDef ):
        self.analysisDefinition = copy.deepcopy(analysisDef)
        self.analysisTableModel.setAnalysisDefinition( self.analysisDefinition)

    def onReload(self):
        self.onLoadAnalysisConfiguration( self.currentAnalysisName )
   
    def updatePushVariables(self, extraDict=None ):
        myReplacementDict = self.replacementDict()
        if extraDict is not None:
            myReplacementDict.update( extraDict )
        for pushvar in list(self.pushVariables.values()):
            try:          
                pushvar.evaluate(myReplacementDict)
            except Exception as e:
                logging.getLogger(__name__).warning( str(e) )

    def onFit(self):
        self.fit( self.currentEvaluation )

    def fit(self, evaluation):
        if self.currentEvaluation is not None and evaluation == self.currentEvaluation:
            plot = self.plottedTraceDict.get( evaluation.evaluation )
            self.fitfunction.evaluate( self.globalDict )
            if plot is not None:
                sigma = None
                if plot.hasHeightColumn:
                    sigma = plot.height
                elif plot.hasTopColumn and plot.hasBottomColumn:
                    sigma = abs(numpy.array(plot.top) + numpy.array(plot.bottom))
                self.fitfunction.leastsq(plot.x, plot.y, sigma=sigma, filt=plot.filt)
                plot.fitFunction = copy.deepcopy(self.fitfunction)
                plot.plot(-2)
                evaluation.fitfunction = StoredFitFunction.fromFitfunction(self.fitfunction)
                self.fitfunctionTableModel.fitDataChanged()
                self.fitResultsTableModel.fitDataChanged()
                replacements = self.fitfunction.replacementDict()
                replacements.update( self.globalDict )
                evaluation.updatePushVariables( replacements )
                self.pushTableModel.fitDataChanged()
        else:
            fitfunction = evaluation.fitfunction.fitfunction()
            fitfunction.evaluate( self.globalDict )
            plot = self.plottedTraceDict.get( evaluation.evaluation )
            if plot is not None:
                sigma = None
                if plot.hasHeightColumn:
                    sigma = plot.height
                elif plot.hasTopColumn and plot.hasBottomColumn:
                    sigma = abs(numpy.array(plot.top) + numpy.array(plot.bottom))
                fitfunction.leastsq(plot.x, plot.y, sigma=sigma, filt=plot.filt)
                plot.fitFunction = fitfunction
                plot.plot(-2)
                evaluation.fitfunction = StoredFitFunction.fromFitfunction(fitfunction)
                self.fitfunctionTableModel.fitDataChanged()
                self.fitResultsTableModel.fitDataChanged()
                replacements = fitfunction.replacementDict()
                replacements.update( self.globalDict )
                evaluation.updatePushVariables( replacements )
        names = evaluation.fitfunction.fitfunction().parameterNames
        vals = evaluation.fitfunction.fitfunction().parameters
        return dict(list(zip(names, vals))) #Return a dictionary of fit parameters and fitted values

    def onSmartToStart(self):
        if self.fitfunction:
            plot = self.plottedTraceDict.get( self.currentEvaluation.evaluation )
            if plot is not None:
                smartParameters = self.fitfunction.smartStartValues(plot.x, plot.y, self.fitfunction.parameters, self.fitfunction.parameterEnabled)
                self.fitfunction.startParameters = list(smartParameters)
                self.fitfunctionTableModel.startDataChanged()            
           
    def onPlot(self):
        if self.currentEvaluation is not None:
            plot = self.plottedTraceDict.get( self.currentEvaluation.evaluation )
            fitfunction = copy.deepcopy(self.fitfunction)
            fitfunction.parameters = [float(param) if unit is None else param.m_as(unit) for unit, param in zip(cycle(flattenAll([fitfunction.units])), fitfunction.startParameters)]
            plot.fitFunction = fitfunction
            plot.plot(-2)
            fitfunction.update()
                    
    def onFitAll(self):
        self.fitAll()
        
    def fitAll(self):
        allResults = dict()
        failedList = list()
        for evaluation in self.analysisDefinition:
            try:
                allResults[evaluation.name] = self.fit(evaluation)
            except Exception as e:
                logging.getLogger(__name__).error("Analysis '{0}' failed with error '{1}'".format(evaluation.name, e))
                failedList.append(evaluation.name)
        self.analysisResultSignal.emit(allResults)
        return failedList
    
    def onLoadFitFunction(self, name=None):
        name = str(name) if name is not None else self.currentAnalysisName
        if name in self.analysisDefinitions:
            if StoredFitFunction.fromFitfunction(self.fitfunction) != self.analysisDefinitions[name]:
                self.setFitfunction( self.analysisDefinitions[name].fitfunction() )

    def setFitfunction(self, fitfunction):
        self.fitfunction = fitfunction
        self.fitfunctionTableModel.setFitfunction(self.fitfunction)
        self.fitResultsTableModel.setFitfunction(self.fitfunction)
        self.descriptionLabel.setText( self.fitfunction.functionString if self.fitfunction else "" )
        if self.fitfunction:
            self.fitfunction.useSmartStartValues = self.fitfunction.useSmartStartValues and self.fitfunction.hasSmartStart
            with BlockSignals(self.checkBoxUseSmartStartValues):
                self.checkBoxUseSmartStartValues.setChecked( self.fitfunction.useSmartStartValues )
                self.checkBoxUseSmartStartValues.setEnabled( self.fitfunction.hasSmartStart )
            with BlockSignals(self.useErrorBarsCheckBox):
                self.useErrorBarsCheckBox.setChecked(self.fitfunction.useErrorBars)
        self.evaluate()

    def setPlottedTraceDict(self, plottedTraceDict):
        self.plottedTraceDict = plottedTraceDict
        self.setButtonEnabledState()

    def analyze(self, plottedTraceDict ):
        self.setPlottedTraceDict(plottedTraceDict)
        self.fitAll()
        failedToPush = self.pushAll()
        return failedToPush

    def evaluate(self, name=None):
        if self.fitfunction is not None:
            self.fitfunction.evaluate( self.globalDict )
            self.fitfunctionTableModel.update()
            self.parameterTableView.viewport().repaint()
            replacements = self.fitfunction.replacementDict()
            replacements.update( self.globalDict )
            self.currentEvaluation.updatePushVariables( replacements )
        
    def onRemoveFit(self):
        if self.currentEvaluation is not None:
            plot = self.plottedTraceDict.get( self.currentEvaluation.evaluation )
            plot.fitFunction = None
            plot.plot(-2)

    def onExtractFit(self):
        if self.currentEvaluation is not None:
            plot = self.plottedTraceDict.get( self.currentEvaluation.evaluation )
            self.setFitfunction( copy.deepcopy(plot.fitFunction))
            
    def onFitToStart(self):
        if self.fitfunction is not None:
            self.fitfunction.startParameters = copy.deepcopy(self.fitfunction.parameters)
            self.fitfunctionTableModel.startDataChanged()

    def copyToClipboard(self, tableview, model):
        """ Copy value to clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        indices = tableview.selectedIndexes()
        role = QtCore.Qt.DisplayRole
        if len(indices) == 1: # just copy the text in the selected box
            clip.setText(str(model.data(indices[0], role)))
        else: # copy contents of selected boxes into a table (nested lists)
            # the following code sorts indices by row (then column) and constructs nested lists to be copied
            sortedIndices = sorted(indices, key=lambda ind: ind.row()*100+ind.column())
            finalDataList = []
            innerDataList = []
            initRow = sortedIndices[0].row()
            for ind in sortedIndices:
                if ind.row() != initRow:
                    finalDataList.append(innerDataList)
                    innerDataList = []
                    initRow = ind.row()
                innerDataList.append(model.data(ind, role))
            finalDataList.append(innerDataList)
            clip.setText(str(finalDataList))

    def parameterRightClickMenu(self, pos):
        """a CustomContextMenu for copying parameters from fit parameter table"""
        menu = QtWidgets.QMenu()
        menu.addAction(self.autoSaveAction)
        menu.addAction(self.copyParameterAction)
        menu.exec_(self.parameterTableView.mapToGlobal(pos))

    def resultsRightClickMenu(self, pos):
        """a CustomContextMenu for copying parameters from fit results table"""
        menu = QtWidgets.QMenu()
        menu.addAction(self.autoSaveAction)
        menu.addAction(self.copyResultsAction)
        menu.exec_(self.resultsTableView.mapToGlobal(pos))

if __name__=="__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = AnalysisControl(config, dict(), "parent")
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())



