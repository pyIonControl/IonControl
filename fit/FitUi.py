# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import copy
import logging

import numpy
from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic

#from trace.Traceui import traceFocus
import trace
from fit.FitFunctionBase import fitFunctionMap, fitFunUpdate
from fit.FitResultsTableModel import FitResultsTableModel
from fit.FitUiTableModel import FitUiTableModel
from modules.AttributeComparisonEquality import AttributeComparisonEquality
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.PyqtUtility import BlockSignals
from modules.GuiAppearance import restoreGuiState, saveGuiState   #@UnresolvedImport
from fit.StoredFitFunction import StoredFitFunction               #@UnresolvedImport
from itertools import cycle

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/FitUi.ui')
fitForm, fitBase = PyQt5.uic.loadUiType(uipath)


class Parameters(AttributeComparisonEquality):
    def __init__(self):
        self.autoSave = False

class FitUi(fitForm, QtWidgets.QWidget):
    analysisNamesChanged = QtCore.pyqtSignal(object)
    def __init__(self, traceui, config, parentname, globalDict=None, parent=None, namedtraceui=None):
        QtWidgets.QWidget.__init__(self, parent)
        fitForm.__init__(self)
        self.config = config
        self.parentname = parentname
        self.fitfunction = None
        self.traceui = traceui
        self.namedtraceui = namedtraceui
        self.focusui = self.traceui
        self.configname = "FitUi.{0}.".format(parentname)
        try:
            self.fitfunctionCache = self.config.get(self.configname+"FitfunctionCache", dict() )
        except Exception:
            self.fitfunctionCache = dict()
        try:
            self.analysisDefinitions = self.config.get(self.configname+"AnalysisDefinitions", dict())
        except Exception:
            self.analysisDefinitions = dict()
        try:
            self.parameterDefinitions = self.config.get(self.configname+"parameterDefinitions", dict())
        except Exception:
            self.parameterDefinitions = dict()
        if self.fitfunctionCache:
            self.initializeParameterDefs()
        self.parameters = self.config.get(self.configname+".Parameters", Parameters())
        self.globalDict = globalDict
            
    def setupUi(self,widget, showCombos=True ):
        fitForm.setupUi(self, widget)
        self.fitButton.clicked.connect( self.onFit )
        self.plotButton.clicked.connect( self.onPlot )
        self.removePlotButton.clicked.connect( self.onRemoveFit )
        self.extractButton.clicked.connect( self.onExtractFit )
        self.getSmartStartButton.clicked.connect( self.onGetSmartStart )
        self.copyButton.clicked.connect( self.onCopy )
        self.removeAnalysisButton.clicked.connect( self.onRemoveAnalysis )
        self.saveButton.clicked.connect( self.onSaveAnalysis )
        self.reloadButton.clicked.connect( self.onLoadAnalysis )
        self.fitSelectionComboBox.addItems( sorted(fitFunctionMap.keys()) )
        self.fitSelectionComboBox.currentIndexChanged[str].connect( self.onFitfunctionChanged )
        fitFunUpdate.dataChanged.connect(self.onFitFunctionsUpdated)
        self.fitfunctionTableModel = FitUiTableModel(self.config)
        self.fitfunctionTableModel.parametersChanged.connect( self.autoSave )
        self.parameterTableView.setModel(self.fitfunctionTableModel)
        self.magnitudeDelegate = MagnitudeSpinBoxDelegate(self.globalDict, emptyStringValue=None)
        self.parameterTableView.setItemDelegateForColumn(2, self.magnitudeDelegate)
        self.parameterTableView.setItemDelegateForColumn(3, self.magnitudeDelegate)
        self.parameterTableView.setItemDelegateForColumn(4, self.magnitudeDelegate)
        self.fitResultsTableModel = FitResultsTableModel(self.config)
        self.resultsTableView.setModel(self.fitResultsTableModel)
        self.onFitfunctionChanged(str(self.fitSelectionComboBox.currentText()))
        # Analysis stuff
        lastAnalysisName = self.config.get(self.configname+"LastAnalysis", None)
        self.analysisNameComboBox.addItems( list(self.analysisDefinitions.keys()) )
        self.analysisNameComboBox.activated[str].connect( self.onLoadAnalysis )
        if lastAnalysisName and lastAnalysisName in self.analysisDefinitions:
            self.analysisNameComboBox.setCurrentIndex( self.analysisNameComboBox.findText(lastAnalysisName))
        try:
            fitfunction = self.config.get(self.configname+"LastFitfunction", None)
        except Exception:
            fitfunction = None
        if fitfunction:
            if isinstance(fitfunction, str):
                if fitfunction in fitFunctionMap.keys():
                    self.setFitfunction(fitFunctionMap[fitfunction]())
                    self.fitSelectionComboBox.setCurrentIndex(self.fitSelectionComboBox.findText(self.fitfunction.name))
            else:
                self.setFitfunction(fitfunction)
                self.fitSelectionComboBox.setCurrentIndex(self.fitSelectionComboBox.findText(self.fitfunction.name))
        self.checkBoxUseSmartStartValues.stateChanged.connect( self.onUseSmartStartValues )
        self.useErrorBarsCheckBox.stateChanged.connect( self.onUseErrorBars )
        # Context Menu
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.parameterTableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.parameterTableView.customContextMenuRequested.connect(self.parameterRightClickMenu)
        self.resultsTableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.resultsTableView.customContextMenuRequested.connect(self.resultsRightClickMenu)
        self.autoSaveAction = QtWidgets.QAction( "auto save", self)
        self.autoSaveAction.setCheckable(True)
        self.autoSaveAction.setChecked(self.parameters.autoSave )
        self.autoSaveAction.triggered.connect( self.onAutoSave )
        self.addAction( self.autoSaveAction )

        # setup actions for copying fit results/parameters from their respective tables
        self.copyResultsAction = QtWidgets.QAction("copy to clipboard", self)
        self.copyResultsAction.triggered.connect(lambda: self.copyToClipboard(self.resultsTableView, self.fitResultsTableModel))
        self.copyParameterAction = QtWidgets.QAction("copy to clipboard", self)
        self.copyParameterAction.triggered.connect(lambda: self.copyToClipboard(self.parameterTableView, self.fitfunctionTableModel))
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self.parameterTableView, lambda: self.copyToClipboard(self.parameterTableView, self.fitfunctionTableModel), context=QtCore.Qt.WidgetWithChildrenShortcut)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self.resultsTableView, lambda: self.copyToClipboard(self.resultsTableView, self.fitResultsTableModel), context=QtCore.Qt.WidgetWithChildrenShortcut)

        restoreGuiState( self, self.config.get(self.configname+".guiState") )
        if not showCombos:
            self.fitSelectionComboBox.setVisible( False )
            self.widget.setVisible( False )
        self.autoSave()
            
    def onAutoSave(self, state):
        self.parameters.autoSave = state
        self.autoSave()
            
    def onShowAnalysisEnabled(self, status):
        self.showAnalysisEnabled = status==QtCore.Qt.Checked
        
    def onUseSmartStartValues(self, state):
        self.fitfunction.useSmartStartValues = state==QtCore.Qt.Checked
        self.autoSave()

    def onUseErrorBars(self, state):
        self.fitfunction.useErrorBars = state==QtCore.Qt.Checked
        self.autoSave()

    def onFitfunctionChanged(self, name, reload=False):
        name = str(name)
        if self.fitfunction and not reload:
            self.fitfunctionCache[self.fitfunction.name] = self.fitfunction
        if name in self.fitfunctionCache:
            self.setFitfunction(self.fitfunctionCache[name])
        else:
            self.fitfunctionCache[name] = fitFunctionMap[name]()
            self.setFitfunction(self.fitfunctionCache[name])
        self.autoSave()

    def onFitFunctionsUpdated(self, name, overwrite=False):
        if overwrite:
            if name in self.parameterDefinitions.keys():
                del self.parameterDefinitions[name]
        with BlockSignals(self.fitSelectionComboBox) as cmb:
            currenttext = cmb.currentText()
            updatedind = cmb.findText(name)
            if updatedind != -1:
                cmb.removeItem(updatedind)
            if name in fitFunctionMap.keys():
                cmb.addItem(name)
            if name in self.fitfunctionCache.keys():
                del self.fitfunctionCache[name]
            if currenttext:
                revertind = cmb.findText(currenttext)
            else:
                revertind = cmb.findText(self.fitfunction.name)
                currenttext = self.fitfunction.name
            if revertind == -1:
                revertind = cmb.findText(name)
                currenttext = name
            cmb.setCurrentIndex(revertind)
            if currenttext in fitFunctionMap.keys():
                self.onFitfunctionChanged(currenttext, True)

    def setFitfunction(self, fitfunction, applyParamDef=True):
        self.fitfunction = fitfunction
        if applyParamDef:
            if self.fitfunction.name in self.parameterDefinitions.keys():
                for field in StoredFitFunction.stateFields:
                    try:
                        if field != 'name' and field != 'results':
                            setattr(self.fitfunction, field, getattr(self.parameterDefinitions[self.fitfunction.name], field))
                    except:
                        continue
        self.fitfunctionTableModel.setFitfunction(self.fitfunction)
        self.fitResultsTableModel.setFitfunction(self.fitfunction)
        self.descriptionLabel.setText( self.fitfunction.functionString )
        if str(self.fitSelectionComboBox.currentText())!= self.fitfunction.name:
            with BlockSignals(self.fitSelectionComboBox):
                self.fitSelectionComboBox.setCurrentIndex(self.fitSelectionComboBox.findText(self.fitfunction.name))
        self.fitfunction.useSmartStartValues = self.fitfunction.useSmartStartValues and self.fitfunction.hasSmartStart
        self.checkBoxUseSmartStartValues.setChecked( self.fitfunction.useSmartStartValues )
        self.checkBoxUseSmartStartValues.setEnabled( self.fitfunction.hasSmartStart )
        self.useErrorBarsCheckBox.setChecked( self.fitfunction.useErrorBars )
        self.evaluate()
        if applyParamDef:
            self.analysisNameComboBox.setCurrentText('')

    def getFocus(self):
        if trace.Traceui.traceFocus == 'namedtrace' and self.namedtraceui is not None:
            self.focusui = self.namedtraceui
        else:
            self.focusui = self.traceui

    def onGetSmartStart(self):
        self.getFocus()
        for plot in self.focusui.selectedTraces(useLastIfNoSelection=True, allowUnplotted=False):
            smartParameters = self.fitfunction.enabledSmartStartValues(plot.x, plot.y, self.fitfunction.parameters)
            self.fitfunction.startParameters = list(smartParameters)
            self.fitfunctionTableModel.startDataChanged()     
        
    def onFit(self):
        """Fit the selected traces using the current fit settings"""
        self.getFocus()
        for plottedTrace in self.focusui.selectedTraces(useLastIfNoSelection=True, allowUnplotted=False):
            self.fit(plottedTrace)

    def fit(self, plottedTrace):
        """Fit plottedTrace using the current fit settings"""
        sigma = None
        if plottedTrace.hasHeightColumn:
            sigma = plottedTrace.height
        elif plottedTrace.hasTopColumn and plottedTrace.hasBottomColumn:
            sigma = numpy.abs(numpy.array(plottedTrace.top) + numpy.array(plottedTrace.bottom))
        self.fitfunction.leastsq(plottedTrace.x, plottedTrace.y, sigma=sigma, filt=plottedTrace.filt)
        plottedTrace.fitFunction = copy.deepcopy(self.fitfunction)
        plottedTrace.plot(-2)
        self.fitfunctionTableModel.fitDataChanged()
        self.fitResultsTableModel.fitDataChanged()

    def showAnalysis(self, analysis, fitfunction):
        if self.showAnalysisEnabled and analysis in self.analysisDefinitions:
            with BlockSignals(self.analysisNameComboBox):
                self.analysisNameComboBox.setCurrentIndex( self.analysisNameComboBox.findText(analysis) )
            self.setFitfunction( fitfunction )
                
    def onPlot(self):
        self.getFocus()
        for plot in self.focusui.selectedTraces(useLastIfNoSelection=True, allowUnplotted=False):
            fitfunction = copy.deepcopy(self.fitfunction)
            fitfunction.parameters = [float(param) if unit is None else param.m_as(unit) for unit, param in zip(cycle(fitfunction.units if isinstance(fitfunction.units, list) else [fitfunction.units]), fitfunction.startParameters)]
            plot.fitFunction = fitfunction
            plot.plot(-2)
            fitfunction.update()
                
    def onRemoveFit(self):
        self.getFocus()
        for plot in self.focusui.selectedTraces(useLastIfNoSelection=True):
            plot.fitFunction = None
            plot.plot(-2)
    
    def onExtractFit(self):
        logger = logging.getLogger(__name__)
        self.getFocus()
        plots = self.focusui.selectedTraces(useLastIfNoSelection=True)
        logger.debug( "onExtractFit {0} plots selected".format(len(plots) ) )
        if plots:
            plot = plots[0]
            self.setFitfunction(copy.deepcopy(plot.fitFunction))
            self.fitSelectionComboBox.setCurrentIndex( self.fitSelectionComboBox.findText(self.fitfunction.name))
    
    def onCopy(self):
        self.fitfunction.startParameters = copy.deepcopy(self.fitfunction.parameters)
        self.fitfunctionTableModel.startDataChanged()
    
    def saveConfig(self):
        if self.fitfunction is not None:
            self.fitfunctionCache[self.fitfunction.name] = self.fitfunction
        self.config[self.configname+"parameterDefinitions"] = self.parameterDefinitions
        self.config[self.configname+"FitfunctionCache"] = dict()
        self.config[self.configname+"AnalysisDefinitions"] = copy.deepcopy(self.analysisDefinitions)
        self.config[self.configname+"LastAnalysis"] = str(self.analysisNameComboBox.currentText()) 
        self.config[self.configname+"LastFitfunction"] = self.fitfunction.name
        self.config[self.configname+".Parameters"] = self.parameters
        self.config[self.configname+".guiState"] = saveGuiState( self )
                
    def onRemoveAnalysis(self):
        name = str(self.analysisNameComboBox.currentText())
        if name in self.analysisDefinitions:
            self.analysisDefinitions.pop(name)
            index = self.analysisNameComboBox.findText(name)
            if index>=0:
                self.analysisNameComboBox.removeItem(index)
            self.analysisNamesChanged.emit( list(self.analysisDefinitions.keys()) )

    def onSaveAnalysis(self):
        name = str(self.analysisNameComboBox.currentText())
        pdefinition = StoredFitFunction.fromFitfunction(self.fitfunction)
        self.parameterDefinitions[pdefinition.fitfunctionName] = pdefinition
        if name:
            definition = StoredFitFunction.fromFitfunction(self.fitfunction)
            definition.name = name
            isNew = name not in self.analysisDefinitions
            self.analysisDefinitions[name] = definition
            if self.analysisNameComboBox.findText(name)<0:
                self.analysisNameComboBox.addItem(name)
            if isNew:
                self.analysisNamesChanged.emit( list(self.analysisDefinitions.keys()) )
            self.saveButton.setEnabled( False )
        
    def autoSave(self):
        pdefinition = StoredFitFunction.fromFitfunction(self.fitfunction)
        self.parameterDefinitions[pdefinition.fitfunctionName] = pdefinition
        if self.parameters.autoSave:
            self.onSaveAnalysis()
            self.saveButton.setEnabled( False )
        else:
            self.saveButton.setEnabled( self.saveable() )
 
    def saveable(self):
        name = str(self.analysisNameComboBox.currentText())       
        definition = StoredFitFunction.fromFitfunction(self.fitfunction)
        definition.name = name
        return name != '' and ( name not in self.analysisDefinitions or not (self.analysisDefinitions[name] == definition) )
                       
    def onLoadAnalysis(self, name=None):
        name = str(name) if name is not None else str(self.analysisNameComboBox.currentText())
        if name in self.analysisDefinitions:
            if StoredFitFunction.fromFitfunction(self.fitfunction) != self.analysisDefinitions[name]:
                self.setFitfunction(self.analysisDefinitions[name].fitfunction(), False)

    def analysisNames(self):
        return list(self.analysisDefinitions.keys())
    
    def analysisFitfunction(self, name):
        return self.analysisDefinitions[name].fitfunction()

    def evaluate(self, name=None):
        self.fitfunction.evaluate( self.globalDict )
        self.fitfunctionTableModel.update()
        self.parameterTableView.viewport().repaint()

    def initializeParameterDefs(self):
        for k, v in self.fitfunctionCache.items():
            definition = StoredFitFunction.fromFitfunction(self.fitfunctionCache[k])
            definition.name = k
            self.parameterDefinitions[k] = definition

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


