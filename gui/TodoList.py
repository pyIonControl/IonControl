# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import uic, QtCore, QtGui, QtWidgets

from GlobalVariables.GlobalVariablesModel import MagnitudeSpinBoxGridDelegate
from modules.AttributeComparisonEquality import AttributeComparisonEquality
from modules.statemachine import Statemachine
from .TodoListTableModel import TodoListTableModel
from uiModules.KeyboardFilter import KeyListFilter
from modules.Utility import unique
from functools import partial
from modules.ScanDefinition import ScanSegmentDefinition
import logging
from modules.HashableList import HashableList
from copy import deepcopy, copy
from modules.PyqtUtility import updateComboBoxItems
from modules.SequenceDict import SequenceDict
from gui.TodoListSettingsTableModel import TodoListSettingsTableModel 
from uiModules.TodoListChameleonDelegate import  ComboBoxGridDelegate, PlainGridDelegate
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.GuiAppearance import saveGuiState, restoreGuiState   #@UnresolvedImport
from modules.firstNotNone import firstNotNone
from collections import defaultdict, deque

Form, Base = uic.loadUiType('ui/TodoList.ui')

class TodoListEntry(object):
    def __init__(self, scan=None, measurement=None, evaluation=None, analysis=None):
        super().__init__()
        self.parent = None
        self.parentInd = 0
        self.children = list()
        self.scan = scan
        self.evaluation = evaluation
        self.measurement = measurement
        self.analysis = analysis
        self.scanParameter = None
        self.enabled = True
        self.stopFlag = False
        self.scanSegment = ScanSegmentDefinition()
        self.settings = SequenceDict()
        self.revertSettings = False
        self.conditionEnabled = False
        self.condition = ''
        self.label = ''

    def __setstate__(self, s):
        self.__dict__ = s
        self.__dict__.setdefault('scanParameter', None )
        self.__dict__.setdefault('measurement', None )
        self.__dict__.setdefault('scan', None )
        self.__dict__.setdefault('evaluation', None )
        self.__dict__.setdefault('enabled', True )
        self.__dict__.setdefault('stopFlag', False)
        self.__dict__.setdefault('settings', SequenceDict())
        self.__dict__.setdefault('revertSettings', False)
        self.__dict__.setdefault('analysis', None)
        self.__dict__.setdefault('conditionEnabled', False)
        self.__dict__.setdefault('condition', '')
        self.__dict__.setdefault('parentInd', 0)
        self.__dict__.setdefault('label', '')
        self.scan = str(self.scan) if self.scan is not None else None

    stateFields = ['scan', 'measurement', 'scanParameter', 'evaluation', 'analysis', 'settings', 'enabled', 'stopFlag' ]

    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        if not isinstance(self.todoList, HashableList):
            logging.getLogger(__name__).info("Replacing list with hashable list")
            self.todoList = HashableList(self.todoList)
        return hash(tuple(getattr(self, field) for field in self.stateFields))
    

class Settings:
    def __init__(self):
        self.todoList = list()
        self.currentIndex = 0
        self.repeat = False
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault( 'currentIndex', 0)
        self.__dict__.setdefault( 'repeat', False)

    stateFields = ['currentIndex', 'repeat', 'todoList'] 
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        if not isinstance(self.todoList, HashableList):
            logging.getLogger(__name__).info("Replacing list with hashable list")
            self.todoList = HashableList(self.todoList)
        return hash(tuple(getattr(self, field) for field in self.stateFields))
    

class MasterSettings(AttributeComparisonEquality):
    def __init__(self):
        self.currentSettingName = None
        self.autoSave = False

    def __setstate__(self, d):
        self.__dict__ = d
        self.__dict__.setdefault( 'autoSave', False )

class TodoList(Form, Base):
    def __init__(self,scanModules,config,currentScan,setCurrentScan,globalVariablesUi,scriptingUi,parent=None):
        Base.__init__(self, parent)    
        Form.__init__(self)
        self.config = config
        self.settings = config.get('TodolistSettings', Settings())
        self.settingsCache = config.get( 'TodolistSettings.Cache', dict())
        self.masterSettings = config.get( 'Todolist.MasterSettings', MasterSettings())
        self.scanModules = scanModules
        self.scripting = scriptingUi
        self.scriptFiles = self.scripting.allFiles
        self.scanModuleMeasurements = {'Script': sorted(self.scriptFiles.keys()), 'Todo List': dict()}
        self.scanModuleEvaluations = {'Script': dict(), 'Todo List': dict()}
        self.scanModuleAnalysis = {'Script': dict(), 'Todo List': dict()}
        self.currentMeasurementsDisplayedForScan = None
        self.currentScan = currentScan
        self.setCurrentScan = setCurrentScan
        self.globalVariablesUi = globalVariablesUi
        self.revertGlobalsList = list()
        self.idleConfiguration = None
        self.scriptconnected = False
        self.currentScript = None
        self.currentScriptCode = None
        self.indexStack = deque()
        self.todoStack = deque()
        self.rescanItems = deque()
        self.fullRescanList = deque()
        self.rescan = False
        self.cachedIndex = None
        self.currentTodoList = self.settings.todoList
        self.labelDict = defaultdict(lambda: None)
        self.todoListGenerator = None

    def setupStatemachine(self):
        self.statemachine = Statemachine()        
        self.statemachine.addState( 'Idle', self.enterIdle, self.exitIdle  )
        self.statemachine.addState( 'MeasurementRunning')
        self.statemachine.addState( 'Waiting for Completion', lambda:self.statusLabel.setText('Waiting for completion of measurement') )
        self.statemachine.addStateGroup('InMeasurement', ['MeasurementRunning', 'Waiting for Completion'], self.enterMeasurementRunning, self.exitMeasurementRunning )
        self.statemachine.addState( 'Check' )
        self.statemachine.addState( 'Paused', self.enterPaused )
        self.statemachine.initialize( 'Idle' )
        self.statemachine.addTransition('startCommand', 'Idle', 'MeasurementRunning', self.checkReadyToRun )
        self.statemachine.addTransitionList('stopCommand', ['Idle', 'Paused'], 'Idle')
        self.statemachine.addTransition( 'stopCommand', 'MeasurementRunning', 'Waiting for Completion')
        self.statemachine.addTransition('measurementFinished', 'MeasurementRunning', 'Idle', self.checkStopFlag)
        self.statemachine.addTransition('measurementFinished', 'MeasurementRunning', 'Check', lambda state: not self.checkStopFlag(state) and self.checkReadyToRun(state))
        self.statemachine.addTransition('measurementFinished', 'Waiting for Completion', 'Idle')
        self.statemachine.addTransition('docheck', 'Check', 'MeasurementRunning', lambda state: (True or self.settings.currentIndex>0 or self.settings.repeat) and self.isSomethingTodo())
        self.statemachine.addTransition('docheck', 'Check', 'Idle', lambda state: (True or self.settings.currentIndex == 0 and not self.settings.repeat) or not self.isSomethingTodo())
                
    def setupUi(self):
        super(TodoList, self).setupUi(self)
        self.setupStatemachine()
        self.populateMeasurements()
        self.scanSelectionBox.addItems(['Scan', 'Script', 'Todo List', 'Rescan'])
        self.scanSelectionBox.currentIndexChanged[str].connect( self.updateMeasurementSelectionBox )
        self.updateMeasurementSelectionBox( self.scanSelectionBox.currentText() )
        self.tableModel = TodoListTableModel( self.settings.todoList, self.settingsCache, self.labelDict, self.fullRescanList)
        self.activeItem = self.nodeFromIndex()
        self.tableModel.measurementSelection = self.scanModuleMeasurements
        self.tableModel.evaluationSelection = self.scanModuleEvaluations
        self.tableModel.analysisSelection = self.scanModuleAnalysis
        self.tableModel.valueChanged.connect( self.checkSettingsSavable )
        self.tableView.setModel( self.tableModel )
        self.tableView.setExpandsOnDoubleClick(False)
        self.comboBoxDelegate = ComboBoxGridDelegate()
        self.gridDelegate = PlainGridDelegate()
        self.boldGridDelegate = PlainGridDelegate(bold=True)
        self.tableView.setItemDelegateForColumn(0, self.boldGridDelegate)
        self.tableView.setItemDelegateForColumn(5, self.gridDelegate)
        for column in range(1, 5):
            self.tableView.setItemDelegateForColumn(column, self.comboBoxDelegate)
        self.tableModel.measurementSelection = self.scanModuleMeasurements
        self.tableModel.evaluationSelection = self.scanModuleEvaluations     
        self.tableModel.analysisSelection = self.scanModuleAnalysis     
        self.addMeasurementButton.clicked.connect( self.onAddMeasurement )
        self.removeMeasurementButton.clicked.connect( self.onDropMeasurement )
        self.runButton.clicked.connect( partial( self.statemachine.processEvent, 'startCommand' ) )
        self.stopButton.clicked.connect( partial( self.statemachine.processEvent, 'stopCommand' ) )
        self.repeatButton.setChecked( self.settings.repeat )
        self.repeatButton.clicked.connect( self.onRepeatChanged )
        self.filter = KeyListFilter( [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown] )
        self.filter.keyPressed.connect( self.onReorder )
        self.tableView.installEventFilter(self.filter)
        self.tableModel.setActiveRow(list(self.indexStack)+[self.settings.currentIndex], False)
        self.tableView.doubleClicked.connect( self.setCurrentIndex )
        # naming and saving of todo lists
        self.toolButtonDelete.clicked.connect( self.onDeleteSaveTodoList )
        self.toolButtonSave.clicked.connect( self.onSaveTodoList )
        self.toolButtonReload.clicked.connect( self.onLoadTodoList )
        self.comboBoxListCache.addItems( sorted(self.settingsCache.keys()) )
        if self.masterSettings.currentSettingName is not None and self.masterSettings.currentSettingName in self.settingsCache:
            self.comboBoxListCache.setCurrentIndex( self.comboBoxListCache.findText(self.masterSettings.currentSettingName))
        self.comboBoxListCache.currentIndexChanged[str].connect( self.onLoadTodoList )
        self.checkSettingsSavable()
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.autoSaveAction = QtWidgets.QAction( "auto save", self )
        self.autoSaveAction.setCheckable(True)
        self.autoSaveAction.setChecked( self.masterSettings.autoSave )
        self.autoSaveAction.triggered.connect( self.onAutoSaveChanged )
        self.addAction( self.autoSaveAction )
        # Settings
        self.settingTableModel = TodoListSettingsTableModel( SequenceDict(), self.globalVariablesUi.globalDict )
        self.settingTableView.setModel( self.settingTableModel )
        self.settingTableModel.edited.connect( self.checkSettingsSavable )
        self.comboBoxDelegate2 = ComboBoxDelegate()
        self.magnitudeSpinBoxDelegate = MagnitudeSpinBoxDelegate()
        self.settingTableView.setItemDelegateForColumn( 0, self.comboBoxDelegate2 )
        self.settingTableView.setItemDelegateForColumn( 1, self.magnitudeSpinBoxDelegate )
        self.addSettingButton.clicked.connect( self.onAddSetting )
        self.removeSettingButton.clicked.connect( self.onRemoveSetting )
        self.tableView.selectionModel().currentChanged.connect( self.onActiveItemChanged )
        # Context Menu for Table
        self.tableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.loadLineAction = QtWidgets.QAction( "load line settings", self)
        self.loadLineAction.triggered.connect( self.onLoadLine  )
        self.tableView.addAction( self.loadLineAction )
        # set stop flag
        self.enableStopFlagAction = QtGui.QAction( "toggle stop flag" , self)
        self.enableStopFlagAction.triggered.connect( self.onEnableStopFlag  )
        self.tableView.addAction( self.enableStopFlagAction )

        # 
        restoreGuiState( self, self.config.get('Todolist.guiState'))
        
        # Copy rows
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self, self.copy_to_clipboard, context=QtCore.Qt.WidgetWithChildrenShortcut)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Paste), self, self.paste_from_clipboard, context=QtCore.Qt.WidgetWithChildrenShortcut)
        #QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Delete), self, self.delete_row)

        self.tableView.setStyleSheet("""
            QTreeView::item::selected {
                background-color: rgb(255,255,165);
                color: rgb(40,40,40);
            }
        """)

    def copy_to_clipboard(self):
        """ Copy the list of selected rows to the clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        rows = [ i.row() for i in self.tableView.selectedIndexes()]
        clip.setText(str(rows))
        
    def paste_from_clipboard(self):
        """ Append the string of rows from the clipboard to the end of the TODO list. """
        clip = QtWidgets.QApplication.clipboard()
        
        row_string = str(clip.text())
        try:
            row_list = list(map(int, row_string.strip('[]').split(',')))
        except ValueError:
            raise ValueError("Invalid data on clipboard. Cannot paste into TODO list")
    
        # Stuff
        self.tableModel.copy_rows(row_list)

    def onActiveItemChanged(self, modelIndex, modelIndex2 ):
        todoListElement = self.refineTodoListElement(modelIndex)
        self.settingTableModel.setSettings( todoListElement.settings )
        self.currentlySelectedLabel.setText( "{0} - {1}".format( todoListElement.measurement, todoListElement.evaluation) )

    def populateStacks(self, todolist, idx):
        self.indexStack.clear()
        self.todoStack.clear()
        self.indexStack.extendleft(self.populateIndexStack(idx))
        self.currentTodoList = self.settings.todoList
        for index in self.indexStack:
            #self.todoStack.append(deepcopy(self.currentTodoList))
            self.todoStack.append(self.currentTodoList)
            self.currentTodoList = self.currentTodoList[index].children
        self.currentTodoList = self.todoStack.pop()
        self.settings.currentIndex = self.indexStack.pop()

    def populateIndexStack(self, idx, lst=None):
        if lst is None:
            lst = []
        lst.append(idx.row())
        if idx.parent().isValid():# != -1:
            return self.populateIndexStack(idx.parent(), lst)
        return lst

    def refineTodoListElement(self, idx):
        indexList = self.populateIndexStack(idx)
        localTodo = self.settings.todoList
        for i in reversed(indexList[1:]):
            localTodo = localTodo[i].children
        return localTodo[indexList[0]]


    def onAddSetting(self):
        self.settingTableModel.addSetting()
        
    def onRemoveSetting(self):
        for index in sorted(unique([ i.row() for i in self.settingTableView.selectedIndexes() ]), reverse=True):
            self.settingTableModel.dropSetting(index)
        
    def onAutoSaveChanged(self, state):
        self.masterSettings.autoSave = state
        if state:
            self.checkSettingsSavable()
        
    def checkSettingsSavable(self, savable=None):
        self.tableView.expandAll()
        if savable is None:
            text = str(self.comboBoxListCache.currentText())
            savable = False
            if text is not None and text !=  "":
                savable = text!=self.masterSettings.currentSettingName or text not in self.settingsCache or self.settings!=self.settingsCache[text]
        if savable and self.masterSettings.autoSave:
            self.onSaveTodoList()
            savable = False
        self.toolButtonSave.setEnabled( savable )
        return savable

    def onSaveTodoList(self):
        text = str(self.comboBoxListCache.currentText())
        if text is not None and text != "":
            new = text not in self.settingsCache
            if new or self.settings!=self.settingsCache[text]:
                self.settingsCache[text] = deepcopy( self.settings )
                self.masterSettings.currentSettingName = text
                if new:
                    updateComboBoxItems(self.comboBoxListCache, sorted(self.settingsCache.keys()))
        self.checkSettingsSavable(savable=False)
            
    def onDeleteSaveTodoList(self):
        text = str(self.comboBoxListCache.currentText())
        if text in self.settingsCache:
            self.settingsCache.pop(text)
            updateComboBoxItems(self.comboBoxListCache, sorted(self.settingsCache.keys()))
            
    def onLoadTodoList(self, text=None):
        text = str(text) if text is not None else str(self.comboBoxListCache.currentText())
        if text in self.settingsCache:
            self.masterSettings.currentSettingName = text
            self.setSettings( deepcopy( self.settingsCache[text] ) )
        self.checkSettingsSavable()
        
    def setSettings(self, newSettings):
        self.settings = newSettings
        self.tableModel.setTodolist(self.settings.todoList)
        self.currentTodoList = self.settings.todoList
        self.indexStack.clear()
        self.todoStack.clear()
        self.tableModel.setActiveItem(self.activeItem, self.statemachine.currentState=='MeasurementRunning' )
        #self.tableModel.setActiveRow( list(self.indexStack)+[self.settings.currentIndex], self.statemachine.currentState=='MeasurementRunning' )
        self.repeatButton.setChecked( self.settings.repeat )
        
    def setCurrentIndex(self, index):
        if self.todoListGenerator is not None:
            try:
                self.todoListGenerator.send(None)
            except StopIteration:
                pass
        self.activeItem = self.nodeFromIndex(index)
        self.settings.currentIndex = index.row()
        self.todoListGenerator = self.tableModel.entryGenerator(self.nodeFromIndex(index))
        self.activeItem = next(self.todoListGenerator)
        self.tableModel.setActiveItem(self.activeItem, self.statemachine.currentState=='MeasurementRunning')

        self.checkSettingsSavable()
        '''
        self.rescanItems.clear()
        self.fullRescanList.clear()
        self.rescan = False
        self.settings.currentIndex = index.row()
        self.currentTodoList = self.settings.todoList
        self.populateStacks(self.settings.todoList, index)
        while self.currentTodoList[self.settings.currentIndex].scan == 'Todo List' or \
                        self.currentTodoList[self.settings.currentIndex].scan == 'Rescan':
            self.settings.currentIndex -= 1
            self.incrementIndex()#overrideRepeat=True)
        self.activeItem = self.nodeFromIndex()
        self.tableModel.setActiveItem(self.activeItem, self.statemachine.currentState=='MeasurementRunning')
        #self.tableModel.setActiveRow(list(self.indexStack)+[self.settings.currentIndex], self.statemachine.currentState=='MeasurementRunning')
        self.checkSettingsSavable()
        '''

    def updateMeasurementSelectionBox(self, newscan ):
        newscan = str(newscan)
        if self.currentMeasurementsDisplayedForScan != newscan:
            self.currentMeasurementsDisplayedForScan = newscan
            if newscan == 'Scan':
                self.evaluationSelectionBox.show()
                self.analysisSelectionBox.show()
                updateComboBoxItems(self.measurementSelectionBox, self.scanModuleMeasurements[newscan] )
                updateComboBoxItems(self.evaluationSelectionBox, self.scanModuleEvaluations[newscan] )
                updateComboBoxItems(self.analysisSelectionBox, self.scanModuleAnalysis[newscan] )
            elif newscan == 'Script':
                self.evaluationSelectionBox.hide()
                self.analysisSelectionBox.hide()
                updateComboBoxItems(self.measurementSelectionBox, sorted(self.scriptFiles.keys()))
                updateComboBoxItems(self.evaluationSelectionBox, {})
                updateComboBoxItems(self.analysisSelectionBox, {})
            elif newscan == 'Todo List':
                self.evaluationSelectionBox.hide()
                self.analysisSelectionBox.hide()
                updateComboBoxItems(self.measurementSelectionBox, sorted(self.settingsCache.keys()))
                updateComboBoxItems(self.evaluationSelectionBox, {})
                updateComboBoxItems(self.analysisSelectionBox, {})
            elif newscan == 'Rescan':
                self.evaluationSelectionBox.hide()
                self.analysisSelectionBox.hide()
                updateComboBoxItems(self.measurementSelectionBox, sorted(self.labelDict.keys()))
                updateComboBoxItems(self.evaluationSelectionBox, {})
                updateComboBoxItems(self.analysisSelectionBox, {})

    def populateMeasurements(self):
        self.scanModuleMeasurements = {'Script': sorted(self.scriptFiles.keys()),
                                       'Todo List': sorted(self.settingsCache.keys()),
                                       'Rescan': sorted(self.labelDict.keys())}
        for name, widget in self.scanModules.items():
            if name == 'Scan':
                if hasattr(widget, 'scanControlWidget' ):
                    self.populateMeasurementsItem( name, widget.scanControlWidget.settingsDict )
                else:
                    self.populateMeasurementsItem( name, {} )
                if hasattr(widget, 'evaluationControlWidget' ):
                    self.populateEvaluationItem( name, widget.evaluationControlWidget.settingsDict )
                else:
                    self.populateEvaluationItem( name, {} )
                if hasattr(widget, 'analysisControlWidget' ):
                    self.populateAnalysisItem( name, widget.analysisControlWidget.analysisDefinitionDict )
                else:
                    self.populateAnalysisItem( name, {} )
            elif name == 'Script':
                self.populateMeasurementsItem(name, self.scriptFiles)
                self.populateEvaluationItem( name, {} )
                self.populateAnalysisItem( name, {} )
            elif name == 'Todo List':
                self.populateMeasurementsItem(name, self.settingsCache)
                self.populateEvaluationItem( name, {} )
                self.populateAnalysisItem( name, {} )
            elif name == 'Rescan':
                self.populateMeasurementsItem(name, self.labelDict)
                self.populateEvaluationItem( name, {} )
                self.populateAnalysisItem( name, {} )
        if hasattr(self, 'tableModel'):
            self.tableModel.measurementSelection = self.scanModuleMeasurements
            self.tableModel.evaluationSelection = self.scanModuleEvaluations
            self.tableModel.analysisSelection = self.scanModuleAnalysis

    def populateMeasurementsItem(self, name, settingsDict ):
        self.scanModuleMeasurements[name] = sorted(settingsDict.keys())
        #if name == self.currentMeasurementsDisplayedForScan:
        updateComboBoxItems( self.measurementSelectionBox, self.scanModuleMeasurements[name] )

    def populateEvaluationItem(self, name, settingsDict ):
        self.scanModuleEvaluations[name] = sorted(settingsDict.keys())
        #if name == self.currentMeasurementsDisplayedForScan:
        updateComboBoxItems( self.evaluationSelectionBox, self.scanModuleEvaluations[name] )

    def populateAnalysisItem(self, name, settingsDict ):
        self.scanModuleAnalysis[name] = sorted(settingsDict.keys())
        #if name == self.currentMeasurementsDisplayedForScan:
        updateComboBoxItems( self.analysisSelectionBox, self.scanModuleAnalysis[name] )

    def onReorder(self, key):
        if key in [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown]:
            indexes = self.tableView.selectedIndexes()
            up = key==QtCore.Qt.Key_PageUp
            delta = -1 if up else 1
            rows = sorted(unique([ i.row() for i in indexes ]), reverse=not up)
            if self.tableModel.moveRow( rows, up=up ):
                selectionModel = self.tableView.selectionModel()
                selectionModel.clearSelection()
                for index in indexes:
                    selectionModel.select( self.tableModel.createIndex(index.row()+delta, index.column()), QtCore.QItemSelectionModel.Select )
#            self.selectionChanged.emit( self.enabledParametersObjects )
        self.checkSettingsSavable()

    def onAddMeasurement(self):
        if self.currentMeasurementsDisplayedForScan and self.measurementSelectionBox.currentText():
            self.tableModel.addMeasurement( TodoListEntry(self.currentMeasurementsDisplayedForScan, str(self.measurementSelectionBox.currentText()), 
                                                          str(self.evaluationSelectionBox.currentText()), str(self.analysisSelectionBox.currentText())))
        self.checkSettingsSavable()
    
    def onDropMeasurement(self):
        for index in sorted(unique([ i.row() for i in self.tableView.selectedIndexes() ]), reverse=True):
            self.tableModel.dropMeasurement(index)
        numEntries = self.tableModel.rowCount()
        if self.settings.currentIndex >= numEntries:
            self.settings.currentIndex = 0
        self.checkSettingsSavable()

    def checkReadyToRun(self, state, _=True ):
        _, current = self.currentScan()
        return current.state()==0 and self.isSomethingTodo()

    def checkStopFlag(self, state):
        return self.currentTodoList[self.settings.currentIndex].stopFlag

    def onStateChanged(self, newstate ):
        if newstate=='idle':
            self.statemachine.processEvent('measurementFinished')
            self.statemachine.processEvent('docheck')
    
    def onRepeatChanged(self, enabled):
        self.settings.repeat = enabled
        self.checkSettingsSavable()

    def enterIdle(self):
        self.statusLabel.setText('Idle')
        if self.idleConfiguration is not None:
            (previousName, previousScan, previousEvaluation, previousAnalysis) = self.idleConfiguration
            currentname, currentwidget = self.currentScan()
            if previousName!=currentname:
                self.setCurrentScan(previousName)
            currentwidget.scanControlWidget.loadSetting( previousScan )   
            currentwidget.evaluationControlWidget.loadSetting( previousEvaluation )  
            currentwidget.analysisControlWidget.onLoadAnalysisConfiguration( previousAnalysis )
        
    def exitIdle(self):
        currentname, currentwidget = self.currentScan()
        currentScan = currentwidget.scanControlWidget.settingsName  
        currentEvaluation = currentwidget.evaluationControlWidget.settingsName
        currentAnalysis = currentwidget.analysisControlWidget.currentAnalysisName
        self.idleConfiguration = (currentname, currentScan, currentEvaluation, currentAnalysis)
        
    def onLoadLine(self):
        allrows = sorted(unique([ i.row() for i in self.tableView.selectedIndexes() ]))
        if len(allrows)==1: 
            self.loadLine(self.currentTodoList[ allrows[0] ])

    def loadLine(self, entry ):
        currentname, currentwidget = self.currentScan()
        # switch to the scan for the first line
        if entry.scan!=currentname:
            self.setCurrentScan(entry.scan)
        # load the correct measurement
        currentwidget.scanControlWidget.loadSetting( entry.measurement )   
        currentwidget.evaluationControlWidget.loadSetting( entry.evaluation )  
        currentwidget.analysisControlWidget.onLoadAnalysisConfiguration( firstNotNone( entry.analysis, "")  )

    def onEnableStopFlag(self):
        allrows = sorted(unique([ i.row() for i in self.tableView.selectedIndexes() ]))
        if len(allrows)==1:
            self.enableStopFlag(self.currentTodoList[ allrows[0] ])

    def enableStopFlag(self, entry ):
        entry.stopFlag = not entry.stopFlag

    def nodeFromIndex(self, index=None):
        if index is None:
            index = self.settings.currentIndex
        return self.tableModel.recursiveLookup(list(self.indexStack)+[self.settings.currentIndex])

    def incrementIndex2(self, overrideRepeat=False):
        modindex = (self.settings.currentIndex+1) % len(self.currentTodoList)
        if self.currentTodoList[modindex].scan == 'Todo List':
            if self.currentTodoList[modindex].enabled:# and (not self.rescan or self.currentTodoList[modindex] in self.rescanItems):
                self.indexStack.append(modindex)
                self.todoStack.append(self.currentTodoList)
                self.currentTodoList = self.currentTodoList[modindex].children
                self.settings.currentIndex = -1
                return self.incrementIndex(overrideRepeat)
            else:
                self.settings.currentIndex = modindex
                return self.incrementIndex()
        elif self.currentTodoList[modindex].scan == 'Rescan':
            if self.currentTodoList[modindex].enabled:
                self.rescan = True
                self.rescanItems.extend(self.labelDict[lbl].entry for lbl in self.currentTodoList[modindex].measurement)
                self.fullRescanList.extend(self.labelDict[lbl].entry for lbl in self.currentTodoList[modindex].measurement)
                print(self.currentTodoList[modindex].measurement)
                self.cachedIndex = modindex
                self.settings.currentIndex = -1
                return self.incrementIndex(overrideRepeat)
            else:
                self.settings.currentIndex = modindex
                return self.incrementIndex()
        else:
            if modindex == 0 and len(self.indexStack) > 0:# and not overrideRepeat:
                modindex = self.indexStack.pop()
                self.currentTodoList = self.todoStack.pop()
                self.settings.currentIndex = modindex
                return self.incrementIndex(overrideRepeat)
            if self.rescan:
                if len(self.rescanItems) > 0:
                    print(self.rescanItems[0].scan)
                    if self.currentTodoList[modindex] in self.rescanItems:
                        self.rescanItems.popleft()
                        self.settings.currentIndex = modindex
                        if self.validTodoItem(self.currentTodoList[modindex]):
                            self.activeItem = self.nodeFromIndex()
                            return modindex
                        return self.incrementIndex()
                    else:
                        self.settings.currentIndex = modindex
                        return self.incrementIndex()
                else:
                    self.rescan = False
                    self.fullRescanList.clear()
                    self.settings.currentIndex = self.cachedIndex
                    return self.incrementIndex(overrideRepeat)
            if modindex == 0 and not self.settings.repeat:
                self.settings.currentIndex = (self.lastValidIndex+1) % len(self.currentTodoList)
                self.lastValidIndex = self.settings.currentIndex
                self.activeItem = self.nodeFromIndex()#self.currentTodoList[modindex]
                self.enterIdle()
                return self.lastValidIndex
            curItem = self.currentTodoList[modindex]
            if self.validTodoItem(curItem):
                self.settings.currentIndex = modindex
                self.activeItem = self.nodeFromIndex()
                self.lastValidIndex = modindex
                return modindex
            return self.incrementIndex()

    def validTodoItem(self, item):
        #return item.enabled and (item.condition == '' or (eval(item.condition) and not item.stopFlag))
        return item.enabled #and (item.condition == '' or (eval(item.condition) and not item.stopFlag))

    #def stepTodoList(self):
        #if self.todoGenerator is None:
            #self.todoGenerator = self.incrementer(self.activeItem)
            #self.activeItem = next(self.todoGenerator)
        #nextItem =
        #self.activeItem = self.todoGenerator.send(self.active)

    def incrementIndex(self):#, currentNode, overrideRepeat=False):
        #currentNode = yield currentNode
        #while True:
            #index = currentNode.index()
            #nextindex = currentNode.sibling(index.row()+1, 0, index)


        while True:
            try:
                self.activeItem = next(self.todoListGenerator)
            except StopIteration:
                self.settings.currentIndex = 1
                self.activeItem = self.tableModel.rootNodes[0]
                self.enterIdle()
                break
            if self.validTodoItem(self.activeItem.entry):
                self.settings.currentIndex = 1#self.activeItem.row
                break
        return self.activeItem
        '''
        #modindex = (self.settings.currentIndex+1) % len(self.currentTodoList)
        if self.currentTodoList[modindex].scan == 'Todo List':
            if self.currentTodoList[modindex].enabled:# and (not self.rescan or self.currentTodoList[modindex] in self.rescanItems):
                self.indexStack.append(modindex)
                self.todoStack.append(self.currentTodoList)
                self.currentTodoList = self.currentTodoList[modindex].children
                self.settings.currentIndex = -1
                return self.incrementIndex(overrideRepeat)
            else:
                self.settings.currentIndex = modindex
                return self.incrementIndex()
        elif self.currentTodoList[modindex].scan == 'Rescan':
            if self.currentTodoList[modindex].enabled:
                self.rescan = True
                self.rescanItems.extend(self.labelDict[lbl].entry for lbl in self.currentTodoList[modindex].measurement)
                self.fullRescanList.extend(self.labelDict[lbl].entry for lbl in self.currentTodoList[modindex].measurement)
                print(self.currentTodoList[modindex].measurement)
                self.cachedIndex = modindex
                self.settings.currentIndex = -1
                return self.incrementIndex(overrideRepeat)
            else:
                self.settings.currentIndex = modindex
                return self.incrementIndex()
        else:
            if modindex == 0 and len(self.indexStack) > 0:# and not overrideRepeat:
                modindex = self.indexStack.pop()
                self.currentTodoList = self.todoStack.pop()
                self.settings.currentIndex = modindex
                return self.incrementIndex(overrideRepeat)
            if self.rescan:
                if len(self.rescanItems) > 0:
                    print(self.rescanItems[0].scan)
                    if self.currentTodoList[modindex] in self.rescanItems:
                        self.rescanItems.popleft()
                        self.settings.currentIndex = modindex
                        if self.validTodoItem(self.currentTodoList[modindex]):
                            self.activeItem = self.nodeFromIndex()
                            return modindex
                        return self.incrementIndex()
                    else:
                        self.settings.currentIndex = modindex
                        return self.incrementIndex()
                else:
                    self.rescan = False
                    self.fullRescanList.clear()
                    self.settings.currentIndex = self.cachedIndex
                    return self.incrementIndex(overrideRepeat)
            if modindex == 0 and not self.settings.repeat:
                self.settings.currentIndex = (self.lastValidIndex+1) % len(self.currentTodoList)
                self.lastValidIndex = self.settings.currentIndex
                self.activeItem = self.nodeFromIndex()#self.currentTodoList[modindex]
                self.enterIdle()
                return self.lastValidIndex
            curItem = self.currentTodoList[modindex]
            if self.validTodoItem(curItem):
                self.settings.currentIndex = modindex
                self.activeItem = self.nodeFromIndex()
                self.lastValidIndex = modindex
                return modindex
            return self.incrementIndex()
            '''

    def incrementer(self):
        print('start')
        x = yield
        print('temp')

    def isSomethingTodo2(self):
        for index in list(range( self.settings.currentIndex, len(self.currentTodoList))) + (list(range(0, self.settings.currentIndex)) if self.settings.repeat or len(self.indexStack) > 0 else []):
            if len(self.rescanItems) == 0 or self.currentTodoList[index] in self.rescanItems:
                if self.currentTodoList[ index ].enabled:
                    if self.currentTodoList[index].condition != '':
                        if eval(self.currentTodoList[index].condition):
                            self.settings.currentIndex = index
                            return True
                        elif self.currentTodoList[index].stopFlag:
                            self.settings.currentIndex = index
                            self.incrementIndex()
                            self.tableModel.setActiveItem(self.activeItem, False)
                            #self.tableModel.setActiveRow(list(self.indexStack)+[self.settings.currentIndex], False)
                            self.enterIdle()
                            return False
                    else:
                        self.settings.currentIndex = index
                        return True
        return False

    def isSomethingTodo(self):
        return True #isn't there always?

    def enterMeasurementRunning(self):
        entry = self.currentTodoList[ self.settings.currentIndex ]
        if entry.scan == 'Scan':
            self.statusLabel.setText('Measurement Running')
            _, currentwidget = self.currentScan()
            self.loadLine( entry )
            # set the global variables
            #self.revertGlobalsList = [('Global', key, self.globalVariablesUi.globalDict[key]) for key in entry.settings.iterkeys()]
            #self.globalVariablesUi.update( ( ('Global', k, v) for k,v in entry.settings.items() ))
            # start
            currentwidget.onStart([(k, v) for k, v in entry.settings.items()])
            self.tableModel.setActiveItem(self.activeItem, True)
            #self.tableModel.setActiveRow(list(self.indexStack)+[self.settings.currentIndex], True)
        elif entry.scan == 'Script':
            self.statusLabel.setText('Script Running')
            self.currentScript = self.scripting.script.fullname
            self.currentScriptCode = str(self.scripting.textEdit.toPlainText())
            self.scripting.loadFile(self.scriptFiles[entry.measurement])
            self.scripting.onStartScript()
            self.scripting.script.finished.connect(self.exitMeasurementRunning)
            self.scriptconnected = True
            self.tableModel.setActiveItem(self.activeItem, True)
            #self.tableModel.setActiveRow(list(self.indexStack)+[self.settings.currentIndex], True)

    def exitMeasurementRunning(self):
        if self.scriptconnected:
            self.scripting.script.finished.disconnect(self.exitMeasurementRunning)
            self.scriptconnected = False
            if self.currentScript is not None:
                self.scripting.loadFile(self.currentScript)
                self.scripting.textEdit.setPlainText(self.currentScriptCode)
            self.onStateChanged('idle')
        else:
            self.incrementIndex()
            self.tableModel.setActiveItem(self.activeItem, False)
            #self.tableModel.setActiveRow(list(self.indexStack)+[self.settings.currentIndex], False)
        #self.globalVariablesUi.update(self.revertGlobalsList)
        
    def enterPaused(self):
        self.statusLabel.setText('Paused')
        
    def saveConfig(self):
        self.config['TodolistSettings'] = self.settings
        self.config['TodolistSettings.Cache'] = self.settingsCache
        self.config['Todolist.MasterSettings'] = self.masterSettings
        self.config['Todolist.guiState'] = saveGuiState( self )
       
        
        