# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os.path

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic
import logging

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from modules.file_data_cache import file_data_cache
from modules.iteratortools import first
from modules.quantity import Q

from .BinaryTableModel import CounterTableModel, TriggerTableModel, ShutterTableModel
from ProjectConfig.Project import getProject
from pulseProgram import PulseProgram
from pulseProgram.PulseProgramSourceEdit import PulseProgramSourceEdit
from pulseProgram.VariableDictionary import VariableDictionary
from pulseProgram.VariableTableModel import VariableTableModel
from pulser.Encodings import EncodingDict
from uiModules.RotatedHeaderView import RotatedHeaderView
from modules.enum import enum
from pppCompiler.astCompiler import pppCompiler
from pppCompiler.CompileException import CompileException
from pppCompiler.Symbol import SymbolTable
from modules.PyqtUtility import BlockSignals, updateComboBoxItems
from pyparsing import ParseException
import copy
from .ShutterDictionary import ShutterDictionary
from .TriggerDictionary import TriggerDictionary
from .CounterDictionary import CounterDictionary
from uiModules.KeyboardFilter import KeyListFilter
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from .PulseProgram import Variable, OPS
import functools
import yaml
import shutil
from collections import OrderedDict
from networkx import DiGraph, simple_cycles, dfs_edges

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/PulseProgram.ui')
PulseProgramWidget, PulseProgramBase = PyQt5.uic.loadUiType(uipath)


class CyclicDependencyError(Exception):
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        super().__init__(*args, **kwargs)


def getPpFileName( filename ):
    if filename is None:
        return filename
    _, ext = os.path.splitext(filename)
    if ext != '.ppp':
        return filename
    path, leafname = os.path.split( filename )
    _, tail = os.path.split(path)
    pp_path = os.path.join(path, "generated_pp") if tail != "generated_pp" else path    
    if not os.path.exists(pp_path):
        os.makedirs(pp_path)
    base, _ = os.path.splitext(leafname)
    return os.path.join(pp_path, base+".ppc")


class PulseProgramContext:
    def __init__(self, globaldict):
        self.parameters = VariableDictionary()
        self.parameters.setGlobaldict(globaldict)
        self.shutters = ShutterDictionary()
        self.triggers = TriggerDictionary()
        self.counters = CounterDictionary()
        self.pulseProgramFile = None
        self.pulseProgramMode = 'pp'
        self.ramFile = None
        self.writeRam = False
        self.parentContext = None

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('ramFile', '')
        self.__dict__.setdefault('writeRam', False)
        self.__dict__.setdefault('parentContext', None)

    stateFields = ['parameters', 'shutters', 'triggers', 'counters', 'pulseProgramFile', 'pulseProgramMode', 'ramFile',
                   'writeRam', 'parentContext']
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and\
               tuple(getattr(self, field) for field in self.stateFields) == tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))
    
    def merge(self, variabledict, overwrite=False, linkNewToParent=False):
        self.parameters.merge(variabledict, overwrite=overwrite, linkNewToParent=linkNewToParent)
        self.shutters.merge(variabledict, overwrite)
        self.triggers.merge(variabledict, overwrite)
        self.counters.merge(variabledict, overwrite)
        
    def setGlobaldict(self, globaldict):
        self.parameters.setGlobaldict(globaldict)
        

class ConfiguredParams(AttributeComparisonEquality):
    def __init__(self):
        self.recentFiles = dict()
        self.recentRamFiles = dict()
        self.lastContextName = None
        self.autoSaveContext = True
        
    def __setstate__(self, d):
        self.recentFiles = d['recentFiles']
        self.recentRamFiles =getattr(self, 'recentRamFiles', dict())
        self.lastContextName = d.get('lastContextName', None )
        self.autoSaveContext = d.get('autoSaveContext', True)

class PulseProgramUi(PulseProgramWidget, PulseProgramBase):
    pulseProgramChanged = QtCore.pyqtSignal() 
    contextDictChanged = QtCore.pyqtSignal(object)
    definitionWords = ['counter', 'var', 'shutter', 'parameter', 'masked_shutter', 'trigger', 'address', 'exitcode', 'const']
    builtinWords = []
    for key, val in SymbolTable().items(): #Extract the builtin words which should be highlighted
        if type(val).__name__ == 'Builtin':
            builtinWords.append(key)

    SourceMode = enum('pp', 'ppp') 
    def __init__(self, config, parameterdict, channelNameData, pulser=None):
        PulseProgramWidget.__init__(self)
        PulseProgramBase.__init__(self)
        self.dependencyGraph = DiGraph()
        self.pulser = pulser
        self.numDDSChannels = len(self.pulser.pulserConfiguration().ddsChannels) if self.pulser.pulserConfiguration() else 8
        self.pulseProgram = PulseProgram.PulseProgram(ddsnum=self.numDDSChannels)
        self.sourceCodeEdits = dict()
        self.pppCodeEdits = dict()
        self.config = config
        self.variableTableModel = None
        self.globalVariablesChanged = None
        self.channelNameData = channelNameData
        self.pppCompileException = None
        self.globaldict = parameterdict
        self.project = getProject()
        self.defaultPPPDir = self.project.configDir+'/PulseProgramsPlus'
        if not os.path.exists(self.defaultPPPDir):
            os.makedirs(self.defaultPPPDir)
            examplePPPDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/PulseProgramsPlus')) #/IonControl/config/PulseProgramsPlus directory
            for basename in os.listdir(examplePPPDir):
                if basename.endswith('.ppp'):
                    pathname = os.path.join(examplePPPDir, basename)
                    if os.path.isfile(pathname):
                        shutil.copy(pathname, self.defaultPPPDir) #Copy over all example PPP pulse programs
        self.defaultRAMDir = self.project.configDir+'/RAMFiles'
        if not os.path.exists(self.defaultRAMDir):
            exampleRAMDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/RAMFiles')) #/IonControl/config/RAMFiles directory
            shutil.copytree(exampleRAMDir, self.defaultRAMDir) #Copy over all example RAM files

    def setupUi(self, experimentname, parent):
        super(PulseProgramUi, self).setupUi(parent)
        self.setCentralWidget(None) #No central widget
        self.experimentname = experimentname
        self.configname = 'PulseProgramUi.' + self.experimentname
        self.contextConfigname = self.configname + '.contextdict'
        self.contextDict = dict(self.config.items_startswith(self.contextConfigname + "."))
        if not self.contextDict:
            self.contextDict = self.config.get(self.contextConfigname, dict())
        self.populateDependencyGraph()
        for context in self.contextDict.values():    # set the global dict as this field does not survive pickling
            context.setGlobaldict(self.globaldict)
        self.currentContext = self.config.get(self.configname + '.currentContext', PulseProgramContext(self.globaldict))
        self.currentContext.setGlobaldict(self.globaldict)
        self.configParams = self.config.get(self.configname, ConfiguredParams())
        self.currentContextName = self.configParams.lastContextName
        
        self.filenameComboBox.addItems([key for key, path in self.configParams.recentFiles.items() if os.path.exists(path)])
        self.contextComboBox.addItems(sorted(self.contextDict.keys()))
        self.parentComboBox.addItems([''] + sorted(self.contextDict.keys()))
        self.ramFilenameComboBox.addItems([''] + [key for key, path in self.configParams.recentRamFiles.items() if os.path.exists(path)])
        self.writeRamCheckbox.setChecked(self.currentContext.writeRam)

        #setup documentation list
        definitionDict, builtinDict, encodingDict = self.getDocs()
        self.addDocs(definitionDict, "Variable Definitions")
        self.addDocs(builtinDict, "Pulse Program Commands")
        self.addDocs(encodingDict, "Encodings")

        #connect actions
        self.actionOpen.triggered.connect( self.onLoad )
        self.actionSave.triggered.connect( self.onSave )
        self.actionReset.triggered.connect(self.onReset)
        self.loadButton.setDefaultAction( self.actionOpen )
        self.saveButton.setDefaultAction( self.actionSave )
        self.resetButton.setDefaultAction( self.actionReset )
        self.loadButtonRam.clicked.connect( self.onLoadRamFile )
        self.writeRamCheckbox.clicked.connect( self.onWriteRamCheckbox )
        self.shutterTableView.setHorizontalHeader( RotatedHeaderView(QtCore.Qt.Horizontal, self.shutterTableView) )
        self.triggerTableView.setHorizontalHeader( RotatedHeaderView(QtCore.Qt.Horizontal, self.triggerTableView ) )
        self.counterTableView.setHorizontalHeader( RotatedHeaderView(QtCore.Qt.Horizontal, self.counterTableView ) )
        self.reloadContextButton.clicked.connect( self.onReloadContext )
        self.saveContextButton.clicked.connect( self.onSaveContext )
        self.deleteContextButton.clicked.connect( self.onDeleteContext )
        self.contextComboBox.currentIndexChanged[str].connect( self.onLoadContext )
        self.parentComboBox.currentIndexChanged[str].connect(self.onSetParent)
        self.linkAllButton.clicked.connect(self.onLinkAllToParent)
        self.unlinkAllButton.clicked.connect(self.onUnlinkAllFromParent)
        self.filenameComboBox.currentIndexChanged[str].connect( self.onFilenameChange )
        self.ramFilenameComboBox.currentIndexChanged[str].connect( self.onRamFilenameChange )
        self.removeCurrent.clicked.connect( self.onRemoveCurrent )
        self.removeCurrentRamFile.clicked.connect( self.onRemoveCurrentRamFile )

        self.variableTableModel = VariableTableModel( self.currentContext.parameters, self.config, self.currentContextName )
        if self.globalVariablesChanged:
            self.globalVariablesChanged.connect(self.variableTableModel.recalculateDependent )
        self.variableView.setModel(self.variableTableModel)
        self.variableView.resizeColumnToContents(0)
        self.variableView.clicked.connect(self.onVariableViewClicked)
        self.filter = KeyListFilter( [], [QtCore.Qt.Key_B, QtCore.Qt.Key_W, QtCore.Qt.Key_R] )
        self.filter.controlKeyPressed.connect( self.onControl )
        self.variableView.installEventFilter(self.filter)
        self.shutterTableModel = ShutterTableModel( self.currentContext.shutters, self.channelNameData[0], size=48, globalDict=self.globaldict, channelSignal=self.channelNameData[1] )
        self.triggerTableModel = TriggerTableModel( self.currentContext.triggers, self.channelNameData[2], size=32, globalDict=self.globaldict, channelSignal=self.channelNameData[3] )
        self.counterTableModel = CounterTableModel( self.currentContext.counters, self.channelNameData[4], globalDict=self.globaldict )
        self.delegates = list()
        for model, view in [ (self.shutterTableModel, self.shutterTableView),
                             (self.triggerTableModel, self.triggerTableView),
                             (self.counterTableModel, self.counterTableView)]:
            view.setModel(model)
            delegate = MagnitudeSpinBoxDelegate(globalDict=self.globaldict)
            self.delegates.append(delegate)  # we need to keep those around, otherwise python will crash.
            view.setItemDelegateForColumn(model.numericDataColumn, delegate)
            if model.tristate:
                view.setItemDelegateForColumn(model.numericMaskColumn, delegate)
            view.clicked.connect(model.onClicked)
            view.resizeColumnsToContents()
            view.setupUi(self.globaldict)
            if self.globalVariablesChanged:
                self.globalVariablesChanged.connect( model.recalculateAllDependents )
        self.counterIdDelegate = MagnitudeSpinBoxDelegate()
        self.counterTableView.setItemDelegateForColumn(self.counterTableModel.idColumn, self.counterIdDelegate)
        try:
            self.loadContext(self.currentContext)
            if self.configParams.lastContextName:
                index = self.contextComboBox.findText(self.configParams.lastContextName)
                with BlockSignals(self.contextComboBox) as w:
                    w.setCurrentIndex(index)
        except:
            logging.getLogger(__name__).exception("Loading of previous context failed")
        #self.contextComboBox.editTextChanged.connect( self.updateSaveStatus )
        self.contextComboBox.lineEdit().editingFinished.connect( self.updateSaveStatus ) 
        self.variableTableModel.contentsChanged.connect( self.updateSaveStatus )
        self.counterTableModel.contentsChanged.connect( self.updateSaveStatus )
        self.shutterTableModel.contentsChanged.connect( self.updateSaveStatus )
        self.triggerTableModel.contentsChanged.connect( self.updateSaveStatus )
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.autoSaveAction = QtWidgets.QAction("Automatically save configuration", self)
        self.autoSaveAction.setCheckable(True)
        self.autoSaveAction.setChecked( self.configParams.autoSaveContext )
        self.autoSaveAction.triggered.connect( self.onAutoSave )
        self.addAction( self.autoSaveAction )

        #background color context menu
        setBackgroundColorAction = QtGui.QAction("Set Background Color", self)
        setBackgroundColorAction.triggered.connect(self.onSetBackgroundColor)
        self.addAction(setBackgroundColorAction)
        removeBackgroundColorAction = QtGui.QAction("Remove Background Color", self)
        removeBackgroundColorAction.triggered.connect(self.onRemoveBackgroundColor)
        self.addAction(removeBackgroundColorAction)

        self.initMenu()
        self.tabifyDockWidget(self.shutterDock, self.triggerDock)
        self.tabifyDockWidget(self.triggerDock, self.counterDock)
        self.restoreLayout()

    def populateDependencyGraph(self):
        self.dependencyGraph = DiGraph()
        self.dependencyGraph.add_nodes_from(self.contextDict.keys())
        for name, context in self.contextDict.items():
            if context.parentContext is not None:
                try:
                    self.dependencySetParent(name, context.parentContext)
                except CyclicDependencyError as ce:
                    context.parentContext = ce.parent

    def dependencySetParent(self, child, parent):
        parent = parent if parent else None
        oldParentEdges = self.dependencyGraph.out_edges([child])
        _, oldParent = first(oldParentEdges, (None, None))
        if parent != oldParent:
            self.dependencyGraph.remove_edges_from(oldParentEdges)
            if parent:
                self.dependencyGraph.add_edge(child, parent)
                cycles = simple_cycles(self.dependencyGraph)
                try:
                    cycle = next(cycles)
                    # StopIteration is raised if there are cycles
                    self.dependencyGraph.remove_edge(child, parent)
                    self.dependencyGraph.add_edges_from(oldParentEdges)
                    raise CyclicDependencyError(oldParent)
                except StopIteration:
                    pass

    def restoreLayout(self):
        """Restore layout from config settings"""
        windowState = self.config.get(self.configname+".state")
        if windowState: self.restoreState(windowState)
        docSplitterState = self.config.get(self.configname+'.docSplitter')
        if docSplitterState: self.docSplitter.restoreState(docSplitterState)

    def initMenu(self):
        self.menuView.clear()
        dockList = self.findChildren(QtWidgets.QDockWidget)
        for dock in dockList:
            self.menuView.addAction(dock.toggleViewAction())

    def onAutoSave(self, checked):
        self.configParams.autoSaveContext = checked
        if checked:
            self.onSaveContext()

    def loadContext(self, newContext ):
        previousContext = self.currentContext
        self.currentContext = copy.deepcopy(newContext)
        #changeMode = self.currentContext.pulseProgramMode != previousContext.pulseProgramMode
        if self.currentContext.pulseProgramFile != previousContext.pulseProgramFile or len(self.sourceCodeEdits)==0:
            self.currentContext.pulseProgramFile = self.project.findFile(self.currentContext.pulseProgramFile)
            self.adaptiveLoadFile(self.currentContext.pulseProgramFile)
        if self.currentContext.ramFile != previousContext.ramFile or (self.currentContext.ramFile):
            self.currentContext.ramFile = self.project.findFile(self.currentContext.ramFile)
            self.loadRamFile(self.currentContext.ramFile)
        self.mergeVariablesIntoContext( self.pulseProgram.variabledict )
        self.updateDisplayContext()
        self.updateSaveStatus(isSaved=True)
        
    def onReloadContext(self):
        self.loadContext( self.contextDict[str(self.contextComboBox.currentText())] )
        self.updateSaveStatus()
    
    def onSaveContext(self):
        name = str(self.contextComboBox.currentText())
        isNewContext = not name in self.contextDict
        self.contextDict[ name ] = copy.deepcopy(self.currentContext)
        if self.contextComboBox.findText(name)<0:
            with BlockSignals(self.contextComboBox) as w:
                w.addItem(name)
            with BlockSignals(self.parentComboBox) as w:
                w.addItem(name)
        if isNewContext:
            self.contextDictChanged.emit(list(self.contextDict.keys()))
        self.updateSaveStatus(isSaved=True)
        self.currentContextName = name
    
    def onDeleteContext(self):
        name = str(self.contextComboBox.currentText())
        index = self.contextComboBox.findText(name)
        if index>=0:
            self.contextDict.pop(name)
            self.contextComboBox.removeItem( index )
            self.parentComboBox.removeItem(self.parentComboBox.findText(name))
            self.contextDictChanged.emit(list(self.contextDict.keys()))
            self.updateSaveStatus()
            self.currentContextName = None

    def onLoadContext(self):
        name = str(self.contextComboBox.currentText())
        self.currentContextName = name
        if name in self.contextDict:
            self.loadContext( self.contextDict[name] )
        else:
            self.onSaveContext()

    def onSetParent(self, parent):
        try:
            parent = parent if parent else None
            self.dependencySetParent(self.currentContextName, parent)
            self.currentContext.parentContext = parent
            self.variableTableModel.setContextHasParent(bool(parent))
        except CyclicDependencyError as ce:
            parent = ce.parent
            self.currentContext.parentContext = parent
            self.parentComboBox.setCurrentIndex(self.parentComboBox.findText(parent if parent else ''))
        self.currentContext.parentContext = parent
        self.setParentData(self.currentContext.parentContext)

    def loadContextByName(self, name):
        if name in self.contextDict:
            self.loadContext( self.contextDict[name] )
            with BlockSignals(self.contextComboBox) as w:
                w.setCurrentIndex( w.findText( name ))
      
    def updatepppDisplay(self):
        for pppTab in list(self.pppCodeEdits.values()):
            self.sourceTabs.removeTab( self.sourceTabs.indexOf(pppTab) )
        self.pppCodeEdits = dict()
        if self.currentContext.pulseProgramMode == 'ppp':
            for name, text in [(self.pppSourceFile, self.pppSource)]:
                textEdit = PulseProgramSourceEdit(mode='ppp')
                encodingStrings = [encoding for encoding in EncodingDict.keys() if type(encoding) == str]
                textEdit.setupUi(textEdit, extraKeywords1=self.definitionWords+encodingStrings, extraKeywords2=self.builtinWords)
                textEdit.setPlainText(text)
                self.pppCodeEdits[name] = textEdit
                self.sourceTabs.addTab( textEdit, name )
                
    def updateppDisplay(self):
        for pppTab in list(self.sourceCodeEdits.values()):
            self.sourceTabs.removeTab( self.sourceTabs.indexOf(pppTab) )
        self.sourceCodeEdits = dict()
        for name, text in self.pulseProgram.source.items():
            textEdit = PulseProgramSourceEdit()
            textEdit.setupUi(textEdit, extraKeywords1=self.definitionWords, extraKeywords2=[key for key in OPS])
            textEdit.setPlainText(text)
            self.sourceCodeEdits[name] = textEdit
            self.sourceTabs.addTab( textEdit, name )
            textEdit.setReadOnly( self.currentContext.pulseProgramMode!='pp' )

    def updateDisplayContext(self):
        self.setParentData(self.currentContext.parentContext)
        self.variableTableModel.setVariables(self.currentContext.parameters, self.currentContextName)
        self.variableTableModel.setContextHasParent(bool(self.currentContext.parentContext))
        with BlockSignals(self.parentComboBox) as w:
            w.setCurrentIndex(self.parentComboBox.findText(self.currentContext.parentContext
                                                           if self.currentContext.parentContext else ''))
        self.variableView.resizeColumnsToContents()
        self.shutterTableModel.setDataDict(self.currentContext.shutters)
        self.triggerTableModel.setDataDict(self.currentContext.triggers)
        self.counterTableModel.setDataDict(self.currentContext.counters)
        self.writeRamCheckbox.setChecked(self.currentContext.writeRam)

    def documentationString(self):
        messages = [ "PulseProgram {0}".format( self.configParams.lastLoadFilename ) ]
        r = "\n".join(messages)
        return "\n".join( [r, self.pulseProgram.currentVariablesText()])      
    
    def description(self):
        desc = dict()
        desc["PulseProgram"] =  self.configParams.lastLoadFilename
        desc.update( self.pulseProgram.variables() )
        return desc
               
    def onFilenameChange(self, name ):
        name = str(name)
        if name in self.configParams.recentFiles and self.configParams.recentFiles[name]!=self.currentContext.pulseProgramFile:
            self.adaptiveLoadFile(self.configParams.recentFiles[name])
            if str(self.filenameComboBox.currentText())!=name:
                with BlockSignals(self.filenameComboBox) as w:
                    w.setCurrentIndex( self.filenameComboBox.findText( name ))
        self.updateSaveStatus()

    def onRamFilenameChange(self, name ):
        name = str(name)
        if name in self.configParams.recentRamFiles and self.configParams.recentRamFiles[name]!=self.currentContext.ramFile:
            self.loadRamFile(self.configParams.recentRamFiles[name])
            if str(self.ramFilenameComboBox.currentText())!=name:
                with BlockSignals(self.ramFilenameComboBox) as w:
                    w.setCurrentIndex( self.ramFilenameComboBox.findText( name ))
        self.updateSaveStatus()
        
    def onOk(self):
        pass
    
    def onLoadRamFile(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open RAM file', self.defaultRAMDir, filter='*.yml')
        if path:
            self.loadRamFile(path)
        self.updateSaveStatus()

    @QtCore.pyqtProperty(list)
    def ramData(self):
        return self.loadRamData(filename=self.currentContext.ramFile)

    @QtCore.pyqtProperty(bool)
    def writeRam(self):
        return self.currentContext.writeRam

    @file_data_cache(maxsize=3)
    def loadRamData(self, filename=''):
        """load in the data from a RAM file"""
        with open(filename, 'r') as f:
            yamldata = yaml.load(f)
        return [self.pulseProgram.convertParameter(Q(float(ramValue['value']), ramValue['unit']), ramValue['encoding']) for ramValue in yamldata]

    def loadRamFile(self, path):
        if path and os.path.exists(path):
            self.currentContext.ramFile = path
            filename = os.path.basename(path)
            if filename not in self.configParams.recentRamFiles:
                self.ramFilenameComboBox.addItem(filename)
            self.configParams.recentRamFiles[filename]=path
            with BlockSignals(self.ramFilenameComboBox) as w:
                w.setCurrentIndex( self.ramFilenameComboBox.findText(filename))
        else:
            self.currentContext.ramFile = ''
            with BlockSignals(self.ramFilenameComboBox) as w:
                w.setCurrentIndex( self.ramFilenameComboBox.findText(''))

    def onWriteRamCheckbox(self):
        self.currentContext.writeRam = self.writeRamCheckbox.isChecked()
        self.updateSaveStatus()

    def onRemoveCurrentRamFile(self):
        text = str(self.ramFilenameComboBox.currentText())
        if text in self.configParams.recentRamFiles:
            self.configParams.recentRamFiles.pop(text)
        self.ramFilenameComboBox.removeItem(self.ramFilenameComboBox.currentIndex())
        self.currentContext.ramFile = ''
        self.updateSaveStatus()

    def onLoad(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Pulse Programmer file', self.defaultPPPDir, filter='*.ppp *.pp')
        if path!="":
            self.adaptiveLoadFile(path)
        self.updateSaveStatus()
        
    def adaptiveLoadFile(self, path):
        if path:
            _, ext = os.path.splitext(path)
            self.currentContext.pulseProgramFile = path
            if ext==".ppp":
                self.currentContext.pulseProgramMode = 'ppp'
                self.loadpppFile(path)
            else:
                self.currentContext.pulseProgramMode = 'pp'
                self.updatepppDisplay()
                self.loadppFile(path)            
            self.configParams.lastLoadFilename = path
            
    def onReset(self):
        if self.configParams.lastLoadFilename is not None:
            self.variabledict = VariableDictionary( self.pulseProgram.variabledict, self.parameterdict )
            self.adaptiveLoadFile(self.configParams.lastLoadFilename)
    
    def loadpppFile(self, path):
        self.pppSourcePath = path
        _, self.pppSourceFile = os.path.split(path)
        with open(path, "r") as f:
            self.pppSource = f.read()
        self.updatepppDisplay()
        ppFilename = getPpFileName(path)
        if self.compileppp(ppFilename):
            self.loadppFile(ppFilename, cache=False)
        filename = os.path.basename(path)
        if filename not in self.configParams.recentFiles:
            self.filenameComboBox.addItem(filename)
        self.configParams.recentFiles[filename]=path
        with BlockSignals(self.filenameComboBox) as w:
            w.setCurrentIndex( self.filenameComboBox.findText(filename))

    def saveppp(self, path):
        if self.pppSource and path:
            with open(path, 'w') as f:
                f.write( self.pppSource )

    def compileppp(self, savefilename):
        self.pppSource = self.pppSource.expandtabs(4)
        success = False
        try:
            compiler = pppCompiler()
            ppCode = compiler.compileString( self.pppSource )
            #self.pppReverseLineLookup = dict()#compiler.reverseLineLookup
            self.pppReverseLineLookup = compiler.reverseLineLookup
            self.pppCompileException = None
            with open(savefilename, "w") as f:
                f.write(ppCode)
            success = True
            self.pppCodeEdits[self.pppSourceFile].clearHighlightError()
        except CompileException as e:
            self.pppCodeEdits[self.pppSourceFile].highlightError( e.message(), e.lineno(), col=e.col())
        except ParseException as e:
            e.__class__ = CompileException  # cast to CompileException. Is possible because CompileException does ONLY add behavior
            self.pppCodeEdits[self.pppSourceFile].highlightError( e.message(), e.lineno(), col=e.col())
        return success
    
    def loadppFile(self, path, cache=True):
        self.pulseProgram.loadSource(path, docompile=False)
        self.updateppDisplay()
        try:
            self.pulseProgram.compileCode()
        except PulseProgram.ppexception as compileexception:
            self.sourceCodeEdits[ compileexception.file ].highlightError(str(compileexception), compileexception.line, compileexception.context )
        if cache:
            filename = os.path.basename(path)
            if filename not in self.configParams.recentFiles:
                self.filenameComboBox.addItem(filename)
            self.configParams.recentFiles[filename]=path
            self.filenameComboBox.setCurrentIndex( self.filenameComboBox.findText(filename))

        # Merge any new values into the current context
        self.mergeVariablesIntoContext( self.pulseProgram.variabledict )
        self.updateDisplayContext()
        self.pulseProgramChanged.emit()

    def mergeVariablesIntoContext( self, variabledict ):
        """Merge variables into context, propagating variable changes up the parentContext list"""
        # Follow the parenting links
        parent = self.currentContext.parentContext
        parents = []
        while parent is not None and parent in self.contextDict and parent not in parents:
            parentContext = self.contextDict[parent]
            if parentContext.pulseProgramFile != self.currentContext.pulseProgramFile:
                break # Stop if the parent's pulse program does not match the current
            parents.append(parent) # Prevents infinite loops
            parent = parentContext.parentContext
        # Propagate variable changes up the parentContext tree in reverse order so the variable
        # linking up the tree doesn't break.
        linkNewToParent = False
        for parent in reversed(parents):
            self.contextDict[parent].merge( variabledict, linkNewToParent=linkNewToParent)
            linkNewToParent = True
        # Finally, merge into the current context
        self.currentContext.merge( variabledict, linkNewToParent=linkNewToParent )

    def onRemoveCurrent(self):
        text = str(self.filenameComboBox.currentText())
        if text in self.configParams.recentFiles:
            self.configParams.recentFiles.pop(text)
        self.filenameComboBox.removeItem(self.filenameComboBox.currentIndex())

    def onSave(self):
        self.onApply()
        if self.currentContext.pulseProgramMode=='pp':
            self.pulseProgram.saveSource()
        else:
            self.saveppp(self.pppSourcePath)
    
    def onApply(self):
        if self.currentContext.pulseProgramMode=='pp':
            try:
                positionCache = dict()
                for name, textEdit in self.sourceCodeEdits.items():
                    self.pulseProgram.source[name] = str(textEdit.toPlainText())
                    positionCache[name] = ( textEdit.textEdit.cursorPosition(),
                                            textEdit.textEdit.scrollPosition() )
                self.pulseProgram.loadFromMemory()
                self.updateppDisplay()
                for name, textEdit in self.sourceCodeEdits.items():
                    textEdit.clearHighlightError()
                    if name in positionCache:
                        cursorpos, scrollpos = positionCache[name]
                        textEdit.textEdit.setCursorPosition( *cursorpos )
                        textEdit.textEdit.setScrollPosition( scrollpos )
            except PulseProgram.ppexception as ppex:
                textEdit = self.sourceCodeEdits[ ppex.file ].highlightError(str(ppex), ppex.line, ppex.context )
        else:
            positionCache = dict()
            for name, textEdit in self.pppCodeEdits.items():
                self.pppSource = str(textEdit.toPlainText())
                positionCache[name] = ( textEdit.textEdit.cursorPosition(),
                                        textEdit.textEdit.scrollPosition() )
            ppFilename = getPpFileName( self.pppSourcePath )
            if self.compileppp(ppFilename):
                self.loadppFile(ppFilename, cache=False)
                for name, textEdit in self.pppCodeEdits.items():
                    textEdit.clearHighlightError()
                    if name in positionCache:
                        cursorpos, scrollpos = positionCache[name]
                        textEdit.textEdit.setCursorPosition( *cursorpos )
                        textEdit.textEdit.setScrollPosition( scrollpos )
            
                    
    def onAccept(self):
        self.saveConfig()
    
    def onReject(self):
        pass
        
    def saveConfig(self):
        """Save the pulse program configuration state"""
        self.configParams.lastContextName = str(self.contextComboBox.currentText())
        self.config[self.configname+".state"] = self.saveState() #Arrangement of dock widgets
        self.config[self.configname] = self.configParams
        self.config.set_string_dict(self.contextConfigname, self.contextDict)
        self.config[self.configname+'.currentContext'] = self.currentContext
        self.config[self.configname+'.docSplitter'] = self.docSplitter.saveState()
        self.variableTableModel.saveConfig()
       
    def getPulseProgramBinary(self,parameters=dict(),override=dict()):
        # need to update variables self.pulseProgram.updateVariables( self.)
        substitutes = dict(self.currentContext.parameters.valueView.items())
        for model in [self.shutterTableModel, self.triggerTableModel, self.counterTableModel]:
            substitutes.update( model.getVariables() )
        substitutes.update(override)
        self.pulseProgram.updateVariables(substitutes)
        return self.pulseProgram.toBinary()
    
    def exitcode(self, number):
        return self.pulseProgram.exitcode(number)
        
    def getVariableValue(self, name):
        return self.variableTableModel.getVariableValue(name)
    
    def variableScanCode(self, variablename, values, extendedReturn=False):
        tempparameters = copy.deepcopy( self.currentContext.parameters )
        updatecode = list()
        numVariablesPerUpdate = 0
        for currentval in values:
            upd_names, upd_values = tempparameters.setValue(variablename, currentval)
            numVariablesPerUpdate = len(upd_names)
            upd_names.append( variablename )
            upd_values.append( currentval )
            updatecode.extend( self.pulseProgram.multiVariableUpdateCode( upd_names, upd_values ) )
            logging.getLogger(__name__).info("{0}: {1}".format(upd_names, upd_values))
        if extendedReturn:
            return updatecode, numVariablesPerUpdate
        return updatecode

    def updateSaveStatus(self, isSaved=None):
        try:
            if isSaved is None:
                currentText = str(self.contextComboBox.currentText())
                if not currentText:
                    self.contextSaveStatus = True
                elif currentText in self.contextDict:
                    self.contextSaveStatus = self.contextDict[currentText]==self.currentContext
                else:
                    self.contextSaveStatus = False
                if self.configParams.autoSaveContext and not self.contextSaveStatus:
                    self.onSaveContext()
                    self.contextSaveStatus = True
            else:
                self.contextSaveStatus = isSaved
            self.saveContextButton.setEnabled( not self.contextSaveStatus )
        except Exception:
            pass

    def onControl(self, key):
        if key==QtCore.Qt.Key_B:
            self.onBold()
        elif key==QtCore.Qt.Key_W:
            self.onSetBackgroundColor()
        elif key==QtCore.Qt.Key_R:
            self.onRemoveBackgroundColor()

    def onBold(self):
        indexes = self.variableView.selectedIndexes()
        for index in indexes:
            self.variableTableModel.toggleBold( index )

    def onSetBackgroundColor(self):
        indexes = self.variableView.selectedIndexes()
        if indexes:
            color = QtGui.QColorDialog.getColor()
            if not color.isValid():
                color = None
            for index in indexes:
                self.variableTableModel.setBackgroundColor(index, color)

    def onRemoveBackgroundColor(self):
        indexes = self.variableView.selectedIndexes()
        for index in indexes:
            self.variableTableModel.removeBackgroundColor(index)

    def lineOfInstruction(self, binaryelement ):
        ppline = self.pulseProgram.lineOfInstruction(binaryelement)
        pppline = self.pppReverseLineLookup.get(ppline, None) if hasattr(self, 'pppReverseLineLookup') else None
        return ppline, pppline

    def setTimingViolations(self, linelist):
        edit = self.pppCodeEdits.get(self.pppSourceFile)
        if edit:
            edit.highlightTimingViolation( [l[1]-1 for l in linelist] )

    def getDocs(self):
        """Assemble the pulse program function documentation into dictionaries"""
        definitionDocPath = os.path.join(os.path.dirname(__file__), '..', r'docs/manual/pppDefinitionDocs.include')
        definitionDict = self.readDocFile(definitionDocPath)
        encodingDocPath = os.path.join(os.path.dirname(__file__), '..', r'docs/manual/pppEncodingDocs.include')
        encodingDict = self.readDocFile(encodingDocPath)
        builtinDict = OrderedDict()
        symbolTable = SymbolTable()
        for name in self.builtinWords:
            builtinDict[name] = symbolTable[name].doc or "This should be documentation for builtin word {0}".format(name)
        return definitionDict, builtinDict, encodingDict

    def readDocFile(self, filename):
        """Read in the rst file 'filename' """
        docdict = OrderedDict()
        try:
            with open(filename, 'r') as f:
                docs = f.read()
            sepdocs = docs.split('.. py:data:: ')
            for doc in sepdocs:
                if doc:
                    doclines = doc.splitlines()
                    name = doclines.pop(0)
                    for line in doclines:
                        if line:
                            documentation = line.strip() #Take the first line with content as the documentation to display in the program
                            break
                    docdict[name] = documentation
        except Exception as e:
            logging.getLogger(__name__).warning("Unable to load documentation: {0}".format(e))
        return docdict

    def addDocs(self, docDict, category):
        """Add the documentation dictionary docDict to the docTree under 'category' """
        categoryItem = QtWidgets.QTreeWidgetItem(self.docTreeWidget, [category])
        self.docTreeWidget.addTopLevelItem(categoryItem)
        for name, documentation in docDict.items():
            nameItem = QtWidgets.QTreeWidgetItem(categoryItem, [name])
            label = QtWidgets.QLabel(documentation)
            label.setWordWrap(True)
            docItem = QtWidgets.QTreeWidgetItem(nameItem)
            self.docTreeWidget.setItemWidget(docItem, 0, label)

    def onVariableViewClicked(self, index):
        if index.column() == 1 and self.currentContext.parentContext:
            var = self.currentContext.parameters.at(index.row())
            if var.hasParent:
                var.useParentValue ^= True
                try:
                    self.setParentData(self.currentContext.parentContext, var)
                except KeyError:
                    var.hasParent = False
                self.variableTableModel.onClicked(index)
                self.updateSaveStatus()

    def onLinkAllToParent(self):
        """ Link all variables to their parents """
        self.variableTableModel.beginResetModel()
        if self.currentContext.parentContext:
            for var in self.currentContext.parameters.values():
                if var.hasParent:
                    var.useParentValue = True
            self.setParentData(self.currentContext.parentContext)
        self.variableTableModel.endResetModel()
        self.updateSaveStatus()

    def onUnlinkAllFromParent(self):
        """ Unlink all variables from their parents """
        self.variableTableModel.beginResetModel()
        for var in self.currentContext.parameters.values():
            var.useParentValue = False
        self.setParentData(self.currentContext.parentContext)
        self.variableTableModel.endResetModel()
        self.updateSaveStatus()

    def setParentData(self, parentContext, var=None):
        for var in [var] if var is not None else self.currentContext.parameters.values():
            try:
                var.hasParent = bool(parentContext)
                if var.useParentValue and var.hasParent:
                    rootName = self.findControllingNode(var.name)
                    self.setParentValue(var.name, rootName)
                    var.parentObject = self.contextDict[rootName].parameters[var.name]
                else:
                    self.currentContext.parameters.setStrValue(var.name, var.strvalue)
                    var.parentObject = None
            except KeyError:
                var.hasParent = False

    def findControllingNode(self, paramName):
        current, parent = self.currentContextName, self.currentContext.parentContext
        var = self.currentContext.parameters[paramName]
        child = None
        if not (parent and var.useParentValue):
            return None
        for child, parent in dfs_edges(self.dependencyGraph, parent):
            try:
                var = self.contextDict[parent].parameters[paramName]
                if not (var.useParentValue and var.hasParent):
                    return child
            except KeyError:
                return child
        return parent

    def setParentValue(self, paramName, contextName):
        self.currentContext.parameters.setParentValue(paramName,
                                                      self.contextDict[contextName].parameters[paramName].value)
        self.currentContext.parameters.setParentStrValue(paramName,
                                                         self.contextDict[contextName].parameters[paramName].strvalue)


class PulseProgramSetUi(QtWidgets.QDialog):
    class Parameters:
        pass
    
    def __init__(self, config, channelNameData, pulser=None):
        super(PulseProgramSetUi, self).__init__()
        self.config = config
        self.configname = 'PulseProgramSetUi'
        self.pulseProgramSet = dict()        # ExperimentName -> PulseProgramUi
        self.lastExperimentFile = dict()     # ExperimentName -> last pp file used for this experiment
        self.isShown = False
        self.channelNameData = channelNameData
        self.pulser = pulser
    
    def setupUi(self, parent):
        self.horizontalLayout = QtWidgets.QHBoxLayout(parent)
        self.tabWidget = QtWidgets.QTabWidget(parent)
        self.horizontalLayout.addWidget(self.tabWidget)
        self.setWindowTitle('Pulse Program')
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinMaxButtonsHint)
        self.setWindowIcon(QtGui.QIcon(":/petersIcons/icons/pulser1.png"))

    def addExperiment(self, experiment, globalDict=dict(), globalVariablesChanged=None):
        if not experiment in self.pulseProgramSet:
            programUi = PulseProgramUi(self.config, globalDict, self.channelNameData, pulser=self.pulser)
            programUi.globalVariablesChanged = globalVariablesChanged
            programUi.setupUi(experiment, programUi)
            programUi.myindex = self.tabWidget.addTab(programUi, experiment)
            self.pulseProgramSet[experiment] = programUi
        return self.pulseProgramSet[experiment]
            
    def setCurrentTab(self, name):
        if name in self.pulseProgramSet:
            self.tabWidget.setCurrentWidget( self.pulseProgramSet[name] )        
            
    def getPulseProgram(self, experiment):
        return self.pulseProgramSet[experiment]
        
    def accept(self):
        self.config[self.configname+'.pos'] = self.pos()
        self.config[self.configname+'.size'] = self.size()
        self.hide()
        self.recipient.onSettingsApply()  
        for page in list(self.pulseProgramSet.values()):
            page.onAccept()
        
    def reject(self):
        self.config[self.configname+'.pos'] = self.pos()
        self.config[self.configname+'.size'] = self.size()
        self.hide()
        for page in list(self.pulseProgramSet.values()):
            page.onAccept()
        
    def show(self):
        super(PulseProgramSetUi, self).show()
        if self.configname+'.pos' in self.config:
            self.move(self.config[self.configname+'.pos'])
        if self.configname+'.size' in self.config:
            self.resize(self.config[self.configname+'.size'])
        for page in list(self.pulseProgramSet.values()):
            page.restoreLayout()
        self.isShown = True
        
    def saveConfig(self):
        self.config[self.configname+'.pos'] = self.pos()
        self.config[self.configname+'.size'] = self.size()
        self.config[self.configname+'.isVisible'] = self.isVisible()
        if self.isShown:
            for page in list(self.pulseProgramSet.values()):
                page.saveConfig()
                
    def onClose(self):
        self.reject()



#    def resizeEvent(self, event):
#        self.config['PulseProgramSetUi.size'] = event.size()
#        super(PulseProgramSetUi,self).resizeEvent(event)
#    
#    def moveEvent(self,event):
#        super(PulseProgramSetUi,self).moveEvent(event)
#        self.config['PulseProgramSetUi.pos'] = self.pos()
        
        
    
if __name__ == "__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = PulseProgramSetUi(config)
    ui.setupUi(ui)
    ui.addExperiment("Sequence")
    ui.addExperiment("Doppler Recooling")
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
    print(config)
