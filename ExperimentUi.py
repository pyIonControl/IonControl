# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import cProfile
import pstats
import webbrowser

import time
from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport
import PyQt5.uic

from OptionalSoftwareFeatures.MemoryProfiler import MemoryProfiler
from ProjectConfig.Project import Project, ProjectInfoUi
import sys
import logging
import os

from dedicatedCounters.WavemeterInterlock import Interlock
from dedicatedCounters.WavemeterInterlockUi import WavemeterInterlockUi
from modules.SequenceDict import SequenceDict
from functools import partial
from GlobalVariables.GlobalVariablesUi import GlobalVariablesUi
from gui import ScanExperiment
from dedicatedCounters.DedicatedCounters import DedicatedCounters
from externalParameter import ExternalParameterSelection
from externalParameter import ExternalParameterUi
from externalParameter.InstrumentLoggingDisplay import InstrumentLoggingDisplay
from logicAnalyzer.LogicAnalyzer import LogicAnalyzer
from modules import DataDirectory, MyException
from modules.DataChanged import DataChanged
from persist import configshelve
from pulseProgram import PulseProgramUi
from uiModules.ImportErrorPopup import importErrorPopup
from gui.TodoList import TodoList
from gui.Preferences import PreferencesUi
from gui.MeasurementLogUi.MeasurementLogUi import MeasurementLogUi
from gui.ValueHistoryUi import ValueHistoryUi
from scripting.ScriptingUi import ScriptingUi
#from trace.NamedTraceui import NamedTraceui
from gui.UserFunctionsEditor import UserFunctionsEditor
from pulser import DDSUi
from pulser.DACUi import DACUi
from pulser.DACController import DACController    #@UnresolvedImport
from pulser.PulserHardwareClient import PulserHardware
from pulser.ChannelNameDict import ChannelNameDict
from pulser import ShutterUi
from pulser.OKBase import OKBase
from pulser.PulserParameterUi import PulserParameterUi
from pulser.PulserHardwareServer import PulserHardwareException
from gui.FPGASettings import FPGASettings
from gui.StashButton import StashButtonControl
from expressionFunctions import UserFunctions
from expressionFunctions.UserFuncImporter import userFuncLoader
from ProjectConfig.Project import getProject
from pathlib import Path
import importlib
import ctypes
import locket
import yaml
import glob
import scan.EvaluationMethods
import scan.FitHistogramsEvaluation
import Experiment_rc
from AWG.AWGUi import AWGUi
from AWG import AWGDevices
from pygsti_addons import yaml as _yaml
from persist import Timeseries

_ = Timeseries.TimeseriesPersist  # We want this imported

setID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
if __name__=='__main__': #imports that aren't just definitions
    from uiModules import MagnitudeParameter #@UnusedImport
    from mylogging.ExceptionLogButton import ExceptionLogButton, LogButton
    from mylogging import LoggingSetup  #@UnusedImport #This runs the logging setup code
    from mylogging.LoggingSetup import qtWarningButtonHandler
    from mylogging.LoggerLevelsUi import LoggerLevelsUi

WidgetContainerForm, WidgetContainerBase = PyQt5.uic.loadUiType(r'ui\Experiment.ui')


class ConfigException(Exception):
    pass


def checkFileValid( filename, typeName, FPGAName ):
    if not filename:
        raise ConfigException("No {0} specified".format(typeName))
    elif not isinstance(filename, str):
        raise ConfigException("{0} '{1}' specified in '{2}' config is not a string".format(typeName, filename, FPGAName))
    elif not os.path.exists(filename):
        raise ConfigException("Unable to open {0} '{1}' specified in '{2}' config: Invalid {0} path".format(typeName, filename, FPGAName))


class ExperimentUi(WidgetContainerBase,WidgetContainerForm):
    levelNameList = ["debug", "info", "warning", "error", "critical"]
    levelValueList = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]

    def __init__(self, config, project):
        self.config = config
        self.project = project
        super(ExperimentUi, self).__init__()
        self.settings = FPGASettings()
        self.loggingLevel = config.get('Settings.loggingLevel',logging.INFO)
        self.consoleMaximumLines = config.get('Settings.consoleMaximumLinesNew',100)
        self.consoleEnable = config.get('Settings.consoleEnable',False)
        self.shutterNameDict = config.get('Settings.ShutterNameDict', ChannelNameDict())
        if self.shutterNameDict.__class__.__name__ == 'ChannelNameMap':
            self.shutterNameDict = ChannelNameDict( self.shutterNameDict.names )
        if self.shutterNameDict.customDict.__class__.__name__ == 'ChannelNameMap':
            self.shutterNameDict = ChannelNameDict(self.shutterNameDict.customDict._fwd, self.shutterNameDict.defaultDict )

        self.shutterNameSignal = DataChanged()
        self.triggerNameDict = config.get('Settings.TriggerNameDict', ChannelNameDict())
        if self.triggerNameDict.__class__.__name__ == 'ChannelNameMap':
            self.triggerNameDict = ChannelNameDict( self.triggerNameDict.names )
        self.triggerNameSignal = DataChanged()
        if self.loggingLevel not in self.levelValueList: self.loggingLevel = logging.INFO
        self.dbConnection = project.dbConnection
        self.objectListToSaveContext = list()
        self.voltageControlWindow = None
        self.profilingEnabled = False

        localpath = getProject().configDir+'/UserFunctions/'
        userFuncLoader(localpath)

    def __enter__(self):
        self.pulser = PulserHardware()
        return self
    
    def __exit__(self, excepttype, value, traceback):
        self.pulser.shutdown()
        return False
    
    def setupUi(self, parent):
        super(ExperimentUi,self).setupUi(parent)
        self.dockWidgetConsole.hide()
        self.loggerUi = LoggerLevelsUi(self.config)
        self.loggerUi.setupUi(self.loggerUi)
        self.loggerDock = QtWidgets.QDockWidget("Logging")
        self.loggerDock.setWidget(self.loggerUi)
        self.loggerDock.setObjectName("_LoggerDock")
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.loggerDock)
        self.loggerDock.hide()

        logger = logging.getLogger()
        self.exceptionToolBar.addWidget(ExceptionLogButton())

        self.warningLogButton = LogButton(messageIcon=":/petersIcons/icons/Warning.png", messageName="warnings")
        self.exceptionToolBar.addWidget(self.warningLogButton)
        qtWarningButtonHandler.textWritten.connect(self.warningLogButton.addMessage)

        # Setup Console Dockwidget
        self.levelComboBox.addItems(self.levelNameList)
        self.levelComboBox.currentIndexChanged[int].connect( self.setLoggingLevel )
        self.levelComboBox.setCurrentIndex( self.levelValueList.index(self.loggingLevel) )
        self.consoleClearButton.clicked.connect( self.onClearConsole )
        self.linesSpinBox.valueChanged.connect( self.onConsoleMaximumLinesChanged )
        self.linesSpinBox.setValue( self.consoleMaximumLines )
        self.checkBoxEnableConsole.stateChanged.connect( self.onEnableConsole )
        self.checkBoxEnableConsole.setChecked( self.consoleEnable )

        self.parent = parent
        self.tabDict = SequenceDict()

        if self.project.isEnabled('software', 'Memory Profiler'):
            self.memoryProfiler = MemoryProfiler(self)

        #determine if Voltages software is enabled and import class if it is
        self.voltagesEnabled = self.project.isEnabled('software', 'Voltages')
        if self.voltagesEnabled:
            from voltageControl.VoltageControl import VoltageControl

        #setup external parameters; import specific libraries if they are needed, popup warnings if selected hardware import fail
        import externalParameter.StandardExternalParameter
        import externalParameter.InterProcessParameters
        if self.project.isEnabled('hardware', 'Conex Motion'):
            try:
                import externalParameter.MotionParameter #@UnusedImport
            except ImportError: #popup on failed import
                importErrorPopup('Conex Motion')
        if self.project.isEnabled('hardware', 'APT Motion'):
            try:
                import externalParameter.APTInstruments  # @UnusedImport
                externalParameter.APTInstruments.loadDll(
                    list(self.project.hardware['APT Motion'].values())[0]['dllPath'])
            except Exception as e:  # popup on failed import
                importErrorPopup('APT Motion error {0}'.format(e))
        if self.project.isEnabled('hardware', 'Lab Brick'):
            try:
                import externalParameter.LabBrick  # @UnusedImport
                externalParameter.LabBrick.loadDll(
                    list(self.project.hardware['Lab Brick'].values())[0]['dllPath'])
            except Exception as e:  # popup on failed import
                importErrorPopup('Lab Brick error {0}'.format(e))
        if self.project.isEnabled('hardware', 'Remote Lab Brick'):
            try:
                from externalParameter import RemoteLabBrick  # @UnusedImport
                for name, e in self.project.hardware['Remote Lab Brick'].items():
                    serverConfig = RemoteLabBrick.RemoteLabBrickConfig(name, e['serverUrl'], e['auth'], e['clientKey'], e['clientCertificate'], e['rootCertificates'])
                    RemoteLabBrick.Servers[name] = serverConfig
            except Exception as e:  # popup on failed import
                importErrorPopup('Remote Lab Brick error {0}'.format(e))
        from externalParameter.ExternalParameterBase import InstrumentDict

        # setup FPGAs
        self.setupFPGAs()

        # initialize PulseProgramUi
        pulserConfig = self.pulser.pulserConfiguration()
        self.shutterNameDict.defaultDict = pulserConfig.shutterBits if pulserConfig else dict()
        self.triggerNameDict.defaultDict = pulserConfig.triggerBits if pulserConfig else dict()
        self.counterNameDict = pulserConfig.counterBits if pulserConfig else dict()
        self.channelNameData = (self.shutterNameDict, self.shutterNameSignal, self.triggerNameDict, self.triggerNameSignal, self.counterNameDict )
        self.pulseProgramDialog = PulseProgramUi.PulseProgramSetUi(self.config,  self.channelNameData, pulser=self.pulser)
        self.pulseProgramDialog.setupUi(self.pulseProgramDialog)

        # Wavemeter Interlock
        self.wavemeterInterlock = None
        wmSetup = self.project.hardware.get('HighFinesse Wavemeter')
        if wmSetup:
            wavemeters = {name: v.get("uri") for name, v in wmSetup.items() if v.get('enabled')}
            if wavemeters:
                self.wavemeterInterlock = Interlock(wavemeters=wavemeters, config=self.config)
                self.wavemeterInterlockUi = WavemeterInterlockUi(wavemeterNames=list(wavemeters.keys()),
                                                                 channels=self.wavemeterInterlock.channels,
                                                                 contexts=self.wavemeterInterlock.contexts)
                self.wavemeterInterlockUi.setupUi(self.wavemeterInterlockUi)
                self.interlockDock = QtWidgets.QDockWidget("Wavemeter Interlock")
                self.interlockDock.setObjectName("Wavemeter Interlock")
                self.interlockDock.setWidget(self.wavemeterInterlockUi)
                self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.interlockDock)

        # Global Variables
        self.globalVariablesUi = GlobalVariablesUi(self.config)
        self.globalVariablesUi.setupUi(self.globalVariablesUi)
        self.globalVariablesDock = QtWidgets.QDockWidget("Global Variables")
        self.globalVariablesDock.setObjectName("Global Variables")
        self.globalVariablesDock.setWidget( self.globalVariablesUi )
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea , self.globalVariablesDock)

        self.measurementLog = MeasurementLogUi(self.config, self.dbConnection)
        self.measurementLog.setupUi(self.measurementLog)
        #self.measurementLogDock = QtWidgets.QDockWidget("Measurement Log")
        #self.measurementLogDock.setWidget( self.measurementLog )
        #self.measurementLogDock.setObjectName('_MeasurementLog')
        #self.addDockWidget( QtCore.Qt.BottomDockWidgetArea, self.measurementLogDock )

        self.preferencesUi = PreferencesUi(config, self)
        self.preferencesUi.setupUi(self.preferencesUi)
        self.preferencesUiDock = QtGui.QDockWidget("Print Preferences")
        self.preferencesUiDock.setWidget(self.preferencesUi)
        self.preferencesUiDock.setObjectName("_preferencesUi")
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.preferencesUiDock)

        for widget, name in [(ScanExperiment.ScanExperiment(self.settings, self.pulser, self.globalVariablesUi,
                                                            "ScanExperiment", toolBar=self.experimentToolBar,
                                                            measurementLog=self.measurementLog,
                                                            callWhenDoneAdjusting=self.callWhenDoneAdjusting,
                                                            interlock=self.wavemeterInterlock,
                                                            preferences=self.preferencesUi.preferences().printPreferences),
                              "Scan")
                             ]:
            widget.setupUi(widget, self.config)
            if hasattr(widget, 'setPulseProgramUi'):
                widget.setPulseProgramUi(self.pulseProgramDialog)
            if hasattr(widget, 'plotsChanged'):
                widget.plotsChanged.connect(self.initMenu)
            self.tabWidget.addTab(widget, name)
            self.tabDict[name] = widget
            widget.ClearStatusMessage.connect(self.statusbar.clearMessage)
            widget.StatusMessage.connect(self.statusbar.showMessage)
            widget.stashChanged.connect(self.onStashChanged)

        self.scanExperiment = self.tabDict["Scan"]
        self.scanExperiment.updateScanTarget('Global', self.globalVariablesUi.globalDict.outputChannels())

        self.shutterUi, self.shutterDockWidget = self.instantiateShutterUi(self.pulser, 'Shutters', "ShutterUi", self.config, self.globalVariablesUi.globalDict, self.shutterNameDict, self.shutterNameSignal)

        self.triggerUi = ShutterUi.TriggerUi(self.pulser, 'ShutterUi', 'trigger', self.config, (self.triggerNameDict, self.triggerNameSignal) )
        self.triggerUi.offColor =  QtGui.QColor(QtCore.Qt.white)
        self.triggerUi.setupUi(self.triggerUi)
        self.pulser.ppActiveChanged.connect( self.triggerUi.setDisabled )
        self.triggerDockWidget.setWidget( self.triggerUi )

        #AWGs
        enabledAWGDict = {displayName:className for displayName,className in AWGDevices.AWGDeviceDict.items()
                          if self.project.isEnabled('hardware', displayName)}
        self.AWGUiDict = dict()
        if enabledAWGDict:
            AWGIcon = QtGui.QIcon()
            AWGPixmap = QtGui.QPixmap(":/other/icons/AWG.png")
            AWGIcon.addPixmap(AWGPixmap)
            AWGButton = QtWidgets.QToolButton()
            AWGButton.setIcon(AWGIcon)
            self.toolBar.addWidget(AWGButton)
            if len(enabledAWGDict) > 1:
                menu = QtWidgets.QMenu("AWG")
                AWGButton.setMenu(menu)
                AWGButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
                menu.setIcon(AWGIcon)
                self.menuWindows.addMenu(menu)
            for displayName, className in enabledAWGDict.items():
                awgUi = AWGUi(getattr(AWGDevices, className), self.config, self.globalVariablesUi.globalDict, self.scanExperiment.pulseProgramUi)
                self.AWGUiDict[displayName] = awgUi
                awgUi.setupUi(awgUi)
                awgUi.varDictChanged.connect( partial(self.scanExperiment.updateScanTarget, displayName) )
                self.scanExperiment.updateScanTarget( displayName, awgUi.varAsOutputChannelDict )
                self.globalVariablesUi.valueChanged.connect( awgUi.evaluate )
                action = QtWidgets.QAction(AWGIcon, displayName, self)
                action.triggered.connect(partial(self.onAWG, displayName))
                if len(enabledAWGDict) > 1:
                    menu.addAction(action)
                else:
                    self.menuWindows.addAction(action)
                    AWGButton.clicked.connect(action.trigger)

        ParameterUi, self.pulserParameterUiDock = self.instantiateParametersUi(self.pulser, "Pulser Parameters", "PulserParameterUi", self.config, self.globalVariablesUi.globalDict)
        self.objectListToSaveContext.append(ParameterUi)

        self.DDSUi, self.DDSDockWidget = self.instantiateDDSUi(self.pulser, "DDS", "DDSUi", self.config, self.globalVariablesUi.globalDict)
        self.objectListToSaveContext.append(self.DDSUi)

        self.DACUi, self.DACDockWidget = self.instantiateDACUi(self.pulser, "DAC", "dacUi", self.config, self.globalVariablesUi.globalDict)
        self.objectListToSaveContext.append(self.DACUi)

#         self.DDSUi9910 = DDSUi9910.DDSUi(self.config, self.pulser )
#         self.DDSUi9910.setupUi(self.DDSUi9910)
#         self.DDS9910DockWidget.setWidget( self.DDSUi9910 )
#        self.pulser.ppActiveChanged.connect( self.DDSUi9910.setDisabled )
        #self.tabDict['Scan'].NeedsDDSRewrite.connect( self.DDSUi9910.onWriteAll )
        self.instantiateAuxiliaryPulsers()

        self.valueHistoryUi = ValueHistoryUi(self.config, self.dbConnection, globaldict=self.globalVariablesUi.globalDict)
        self.valueHistoryUi.setupUi( self.valueHistoryUi )
        self.valueHistoryDock = QtWidgets.QDockWidget("Value History")
        self.valueHistoryDock.setWidget( self.valueHistoryUi )
        self.valueHistoryDock.setObjectName("_valueHistory")
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.valueHistoryDock )
        
        # tabify the dock widgets
        self.tabifyDockWidget( self.pulserParameterUiDock, self.preferencesUiDock)
        self.tabifyDockWidget( self.preferencesUiDock, self.triggerDockWidget )
        self.tabifyDockWidget( self.triggerDockWidget, self.shutterDockWidget)
        self.tabifyDockWidget( self.shutterDockWidget, self.DDSDockWidget )
        self.tabifyDockWidget( self.DDSDockWidget, self.DACDockWidget )
#        self.tabifyDockWidget( self.DDSDockWidget, self.DDS9910DockWidget )
#        self.tabifyDockWidget( self.DDS9910DockWidget, self.globalVariablesDock )
        self.tabifyDockWidget( self.DACDockWidget, self.globalVariablesDock )
        self.tabifyDockWidget( self.globalVariablesDock, self.valueHistoryDock )
        self.triggerDockWidget.hide()
        self.preferencesUiDock.hide()

        self.ExternalParametersSelectionUi = ExternalParameterSelection.SelectionUi(self.config, self.globalVariablesUi.globalDict, classdict=InstrumentDict)
        self.ExternalParametersSelectionUi.setupUi( self.ExternalParametersSelectionUi )
        self.ExternalParameterSelectionDock = QtWidgets.QDockWidget("Params Selection")
        self.ExternalParameterSelectionDock.setObjectName("_ExternalParameterSelectionDock")
        self.ExternalParameterSelectionDock.setWidget(self.ExternalParametersSelectionUi)
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.ExternalParameterSelectionDock)

        self.ExternalParametersUi = ExternalParameterUi.ControlUi(self.config, self.globalVariablesUi.globalDict)
        self.ExternalParametersUi.setupUi(self.ExternalParametersSelectionUi.outputChannels())

        self.ExternalParameterDock = QtWidgets.QDockWidget("Params Control")
        self.ExternalParameterDock.setWidget(self.ExternalParametersUi)
        self.ExternalParameterDock.setObjectName("_ExternalParameterDock")
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.ExternalParameterDock)
        self.ExternalParametersSelectionUi.outputChannelsChanged.connect( self.ExternalParametersUi.setupParameters )

        self.instrumentLoggingDisplay = InstrumentLoggingDisplay(self.config)
        self.instrumentLoggingDisplay.setupUi( self.ExternalParametersSelectionUi.inputChannels(), self.instrumentLoggingDisplay )
        self.instrumentLoggingDisplayDock = QtWidgets.QDockWidget("Params Reading")
        self.instrumentLoggingDisplayDock.setObjectName("_ExternalParameterDisplayDock")
        self.instrumentLoggingDisplayDock.setWidget(self.instrumentLoggingDisplay)
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.instrumentLoggingDisplayDock)
        self.ExternalParametersSelectionUi.inputChannelsChanged.connect( self.instrumentLoggingDisplay.setupParameters )
               
        self.ExternalParametersSelectionUi.outputChannelsChanged.connect( partial(self.scanExperiment.updateScanTarget, 'External') )               
        self.scanExperiment.updateScanTarget( 'External', self.ExternalParametersSelectionUi.outputChannels() )

        # initialize ScriptingUi
        self.scriptingWindow = ScriptingUi(self)
        self.scriptingWindow.setupUi(self.scriptingWindow)

        self.todoList = TodoList(self.tabDict, self.config, self.getCurrentTab, self.switchTab, self.globalVariablesUi, self.scriptingWindow)
        self.todoList.setupUi()
        self.todoListDock = QtWidgets.QDockWidget("Todo List")
        self.todoListDock.setWidget(self.todoList)
        self.todoListDock.setObjectName("_todoList")
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.todoListDock)
        self.tabifyDockWidget(self.valueHistoryDock, self.todoListDock)

        for name, widget in self.tabDict.items():
            if hasattr( widget, 'scanConfigurationListChanged' ) and widget.scanConfigurationListChanged is not None:
                widget.scanConfigurationListChanged.connect( partial( self.todoList.populateMeasurementsItem, name)  )
            if hasattr( widget, 'evaluationConfigurationChanged' ) and widget.evaluationConfigurationChanged is not None:
                widget.evaluationConfigurationChanged.connect( partial( self.todoList.populateEvaluationItem, name)  )
            if hasattr( widget, 'analysisConfigurationChanged' ) and widget.analysisConfigurationChanged is not None:
                widget.analysisConfigurationChanged.connect( partial( self.todoList.populateAnalysisItem, name)  )
       
        #tabify external parameters controls
        self.tabifyDockWidget(self.ExternalParameterSelectionDock, self.ExternalParameterDock)
        self.tabifyDockWidget(self.ExternalParameterDock, self.instrumentLoggingDisplayDock)
        
        self.tabWidget.currentChanged.connect(self.onCurrentChanged)
        self.actionClear.triggered.connect(self.onClear)
        self.actionPause.triggered.connect(self.onPause)

        #Save and load actions
        self.actionSave_GUI.triggered.connect(self.onSaveGUI)
        self.actionSave_GUI_Yaml.triggered.connect(self.onSaveGUIYaml)

        self.actionProfiling.triggered.connect(self.setProfiling)
        self.actionStart.triggered.connect(self.onStart)
        self.actionStop.triggered.connect(self.onStop)
        self.actionAbort.triggered.connect(self.onAbort)
        self.actionExit.triggered.connect(self.onClose)
        self.actionContinue.triggered.connect(self.onContinue)
        self.actionPulses.triggered.connect(self.onPulses)
        self.actionReload.triggered.connect(self.onReload)
        self.actionProject.triggered.connect( self.onProjectSelection)
        self.actionDocumentation.triggered.connect(self.onShowDocumentation)
        if self.voltagesEnabled:
            self.actionVoltageControl.triggered.connect(self.onVoltageControl)
        else:
            self.actionVoltageControl.setDisabled(True)
            self.actionVoltageControl.setVisible(False)
        self.actionScripting.triggered.connect(self.onScripting)
        self.actionUserFunctions.triggered.connect(self.onUserFunctionsEditor)
        self.actionMeasurementLog.triggered.connect(self.onMeasurementLog)
        self.actionDedicatedCounters.triggered.connect(self.showDedicatedCounters)
        self.actionLogic.triggered.connect(self.showLogicAnalyzer)
        self.currentTab = self.tabDict.at( min(len(self.tabDict)-1, self.config.get('MainWindow.currentIndex',0) ) )
        self.tabWidget.setCurrentIndex( self.config.get('MainWindow.currentIndex',0) )
        self.currentTab.activate()
        self.actionForceDock.triggered.connect(self.onForceDock)
        if hasattr( self.currentTab, 'stateChanged' ):
            self.currentTab.stateChanged.connect( self.todoList.onStateChanged )
        if 'MainWindow.State' in self.config:
            self.parent.restoreState(self.config['MainWindow.State'])
        self.initMenu()
        self.actionResume.setEnabled(False)
        if 'MainWindow.pos' in self.config:
            self.move(self.config['MainWindow.pos'])
        if 'MainWindow.size' in self.config:
            self.resize(self.config['MainWindow.size'])
        if 'MainWindow.isMaximized' in self.config:
            if self.config['MainWindow.isMaximized']:
                self.showMaximized()
        else:
            self.showMaximized()
            
        self.dedicatedCountersWindow = DedicatedCounters(self.config, self.dbConnection, self.pulser,
                                                         self.globalVariablesUi, self.shutterUi,
                                                         self.ExternalParametersUi.callWhenDoneAdjusting,
                                                         self.wavemeterInterlock,
                                                         remoteRender=self.project.isEnabled('software', 'Remote render'))
        self.dedicatedCountersWindow.setupUi(self.dedicatedCountersWindow)
        
        self.logicAnalyzerWindow = LogicAnalyzer(self.config, self.pulser, self.channelNameData )
        self.logicAnalyzerWindow.setupUi(self.logicAnalyzerWindow)

        if self.voltagesEnabled:
            try:
                self.voltageControlWindow = VoltageControl(self.config, self.globalVariablesUi.globalDict, self.dac)
                self.voltageControlWindow.setupUi(self.voltageControlWindow)
                self.voltageControlWindow.globalAdjustUi.outputChannelsChanged.connect( partial(self.scanExperiment.updateScanTarget, 'Voltage') )
                self.voltageControlWindow.localAdjustUi.outputChannelsChanged.connect( partial(self.scanExperiment.updateScanTarget, 'Voltage Local Adjust') )
                self.scanExperiment.updateScanTarget('Voltage', self.voltageControlWindow.globalAdjustUi.outputChannels())
                self.scanExperiment.updateScanTarget('Voltage Local Adjust', self.voltageControlWindow.localAdjustUi.outputChannels())
            except MyException.MissingFile as e:
                self.voltageControlWindow = None
                self.actionVoltageControl.setDisabled( True )
                logger.warning("Missing file - voltage subsystem disabled: {0}".format(str(e)))
            if self.voltageControlWindow:
                self.tabDict["Scan"].ppStartSignal.connect( self.voltageControlWindow.synchronize )   # upload shuttling data before running pule program
                self.dedicatedCountersWindow.autoLoad.setVoltageControl( self.voltageControlWindow )

        self.setWindowTitle("Experimental Control ({0})".format(self.project) )

        
        QtCore.QTimer.singleShot(60000, self.onCommitConfig )
        traceFilename, _ = DataDirectory.DataDirectory().sequencefile("Trace.log")
        LoggingSetup.setTraceFilename( traceFilename )
        errorFilename, _ = DataDirectory.DataDirectory().sequencefile("Error.log")
        LoggingSetup.setErrorFilename( errorFilename )
        
        # connect signals and slots for todolist and auto resume
        for name, widget in self.tabDict.items():
            if hasattr(widget,'onContinue'):
                self.dedicatedCountersWindow.autoLoad.ionReappeared.connect( widget.onContinue )
                
        # add PushDestinations
        for widget in self.tabDict.values():
            if hasattr(widget, 'addPushDestination'):
                widget.addPushDestination( 'External', self.ExternalParametersUi )
                
        ## initialize ScriptingUi
        #self.scriptingWindow = ScriptingUi(self)
        #self.scriptingWindow.setupUi(self.scriptingWindow)

        # this is redundant in __init__ but this resolves issues with user-defined functions that reference NamedTraces
        localpath = getProject().configDir+'/UserFunctions/'
        userFuncLoader(localpath)

        # initialize NamedTraceUi
        self.userFunctionsEditor = UserFunctionsEditor(self, self.globalVariablesUi.globalDict)
        self.userFunctionsEditor.setupUi(self.userFunctionsEditor)

        # initialize StashButton
        self.actionStash.triggered.connect(self.onStash)
        self.actionResume.triggered.connect(self.onResume)
        self.stashButton = StashButtonControl(self.actionResume)
        self.stashButton.resume.connect(self.onResume)

    def instantiateParametersUi(self, pulser, windowName, configName, config, globalDict):
        ui = PulserParameterUi(pulser, config, configName, globalDict)
        ui.setupUi()
        uiDock = QtWidgets.QDockWidget(windowName)
        uiDock.setWidget(ui)
        uiDock.setObjectName(windowName)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, uiDock)
        self.tabDict['Scan'].NeedsDDSRewrite.connect(ui.onWriteAll)
        return ui, uiDock

    def instantiateDDSUi(self, pulser, windowName, configName, config, globalDict):
        ui = DDSUi.DDSUi(pulser, config, configName, globalDict)
        ui.setupUi(ui)
        uiDock = QtWidgets.QDockWidget(windowName)
        uiDock.setWidget(ui)
        uiDock.setObjectName(windowName)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, uiDock)
        self.globalVariablesUi.valueChanged.connect(ui.evaluate)
        pulser.ppActiveChanged.connect(ui.setDisabled)
        self.tabDict['Scan'].NeedsDDSRewrite.connect(ui.onWriteAll)
        return ui, uiDock

    def instantiateDACUi(self, pulser, windowName, configName, config, globalDict):
        ui = DACUi(pulser, config, configName, globalDict)
        ui.setupUi(ui)
        uiDock = QtWidgets.QDockWidget(windowName)
        uiDock.setObjectName(windowName)
        uiDock.setWidget(ui)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, uiDock)
        pulser.ppActiveChanged.connect(ui.setDisabled)
        self.tabDict['Scan'].NeedsDDSRewrite.connect(ui.onWriteAll)
        return ui, uiDock

    def instantiateShutterUi(self, pulser, windowName, configName, config, globalDict, nameDict, nameSignal):
        ui = ShutterUi.ShutterUi(pulser, configName, 'shutter', self.config, (nameDict, nameSignal), size=49)
        ui.setupUi(ui, True)
        uiDock = QtWidgets.QDockWidget(windowName)
        uiDock.setObjectName(windowName)
        uiDock.setWidget(ui)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, uiDock)
        pulser.ppActiveChanged.connect(ui.setDisabled)
        logger.debug("ShutterUi representation:" + repr(ui))
        return ui, uiDock

    def callWhenDoneAdjusting(self, callback):
        self.ExternalParametersUi.callWhenDoneAdjusting(callback)

    def onEnableConsole(self, state):
        self.consoleEnable = state==QtCore.Qt.Checked

    def onClearConsole(self):
        self.textEditConsole.clear()
        
    def onConsoleMaximumLinesChanged(self, maxlines):
        self.consoleMaximumLines = maxlines
        self.textEditConsole.document().setMaximumBlockCount(maxlines)
        
    def setLoggingLevel(self, index):
        self.loggingLevel = self.levelValueList[index]

    def showDedicatedCounters(self):
        self.dedicatedCountersWindow.show()
        self.dedicatedCountersWindow.setWindowState(QtCore.Qt.WindowActive)
        self.dedicatedCountersWindow.raise_()
        self.dedicatedCountersWindow.onEnableDataTaking(True) #Start displaying data immediately
        self.dedicatedCountersWindow.onEnableDataPlotting(True)

    def showLogicAnalyzer(self):
        self.logicAnalyzerWindow.show()
        self.logicAnalyzerWindow.setWindowState(QtCore.Qt.WindowActive)
        self.logicAnalyzerWindow.raise_()

    def onVoltageControl(self):
        self.voltageControlWindow.show()
        self.voltageControlWindow.setWindowState(QtCore.Qt.WindowActive)
        self.voltageControlWindow.raise_()

    def onScripting(self):
        self.scriptingWindow.show()
        self.scriptingWindow.setWindowState(QtCore.Qt.WindowActive)
        self.scriptingWindow.raise_()

    def onUserFunctionsEditor(self):
        self.userFunctionsEditor.show()
        self.userFunctionsEditor.setWindowState(QtCore.Qt.WindowActive)
        self.userFunctionsEditor.raise_()

    def onAWG(self, displayName):
        awgUi = self.AWGUiDict[displayName]
        awgUi.show()
        awgUi.setWindowState(QtCore.Qt.WindowActive)
        awgUi.raise_()

    def onMeasurementLog(self):
        self.measurementLog.show()
        self.measurementLog.setWindowState(QtCore.Qt.WindowActive)
        self.measurementLog.raise_()
        
    def onClear(self):
        self.currentTab.onClear()
    
    def onSaveGUI(self, _):
        logger = logging.getLogger(__name__)
        self.currentTab.onSave()
        filename, _ = DataDirectory.DataDirectory().sequencefile("configuration.db")
        logger.info( "Saving config to "+filename )
        self.saveConfig()
        self.config.saveConfig(filename)

    def onSaveGUIYaml(self, _):
        self.currentTab.onSave()
        logger.info("Saving config")
        yamlfilename, _ = DataDirectory.DataDirectory().sequencefile("configuration.yaml")
        self.saveConfig()
        self.config.saveConfig(yamlfile=yamlfilename)

    def onCommitConfig(self):
        logger = logging.getLogger(__name__)
        self.currentTab.onSave()
        logger.debug( "Committing config" )
        self.saveConfig()
        self.config.commitToDatabase()
        QtCore.QTimer.singleShot(60000, self.onCommitConfig )      
            
    def onStart(self, checked=False, globalOverrides=list()):
        self.currentTab.onStart(globalOverrides)

    def setProfiling(self, checked=False):
        if checked:
            self.profile = cProfile.Profile()
            self.profile.enable()
            self.profilingEnabled = True
            self.profilingStartTime = time.time()
        else:
            self.profile.disable()
            self.profilingEnabled = False
            sortby = 'tottime'
            ps = pstats.Stats(self.profile).sort_stats(sortby)
            ps.print_stats()
            timestr = time.strftime("%Y%m%d_%H%M", time.localtime())
            duration = int(time.time() - self.profilingStartTime)
            filename = "profile_{}_{}.pkl".format(timestr, duration)
            ps.dump_stats(filename)

    def onStash(self):
        if hasattr(self.currentTab, 'onStash'):
            self.currentTab.onStash()

    def onStashChanged(self, stash):
        self.actionResume.setEnabled(len(stash)>0)
        self.stashButton.onStashChanged(stash)

    def onResume(self, index=-1):
        if hasattr(self.currentTab, 'onResume'):
            self.currentTab.onResume(index)

    def onPause(self):
        self.currentTab.onPause()
    
    def onStop(self):
        self.currentTab.onStop()
        
    def onAbort(self):
        self.currentTab.onStop(reason='aborted')
        
    def onContinue(self):
        if hasattr(self.currentTab,'onContinue'):
            self.currentTab.onStop()
        else:
            self.statusbar.showMessage("continue not implemented")    
            
    def onReload(self):
        logger = logging.getLogger(__name__)
        logger.debug( "OnReload" )
        self.currentTab.onReload()
    
    def switchTab(self, name):
        self.tabWidget.setCurrentWidget( self.tabDict[name] )
        self.onCurrentChanged(self.tabDict.index(name))  # this gets called later, but we need it to run now in order to switch scans from the todolist
    
    def onCurrentChanged(self, index):
        if self.tabDict.at(index)!=self.currentTab:
            self.currentTab.deactivate()
            if hasattr( self.currentTab, 'stateChanged' ):
                try:
                    self.currentTab.stateChanged.disconnect()
                except TypeError:
                    pass
            self.currentTab = self.tabDict.at(index)
            self.currentTab.activate()
            if hasattr( self.currentTab, 'stateChanged' ):
                self.currentTab.stateChanged.connect( self.todoList.onStateChanged )
            self.initMenu()
            self.actionResume.setEnabled(self.currentTab.stashSize())

    def onForceDock(self, *args):
        self.todoListDock.setFloating(not self.todoListDock.isFloating())

    def initMenu(self):
        """setup print and view menus"""
        #view menu
        self.menuView.clear()
        if hasattr(self.currentTab,'viewActions'):
            self.menuView.addActions(self.currentTab.viewActions())
        dockList = self.findChildren(QtWidgets.QDockWidget)
        for dock in dockList:
            self.menuView.addAction(dock.toggleViewAction())

        #print menu
        self.menuPrint.clear()
        if hasattr(self.currentTab,'printTargets'):
            for plot in self.currentTab.printTargets():
                action = self.menuPrint.addAction( plot )
                action.triggered.connect( partial(self.onPrint, plot ))
        self.menuPrint.addSeparator()
        action = self.menuPrint.addAction("Print Preferences")
        action.triggered.connect(self.preferencesUiDock.show)
        action.triggered.connect(self.preferencesUiDock.raise_)

    def onPulses(self):
        self.pulseProgramDialog.show()
        self.pulseProgramDialog.setWindowState(QtCore.Qt.WindowActive)
        self.pulseProgramDialog.raise_()
        if hasattr(self.currentTab,'experimentName'):
            self.pulseProgramDialog.setCurrentTab(self.currentTab.experimentName)
                  
    def onClose(self):
        self.parent.close()
        
    def onMessageWrite(self,message,level=logging.DEBUG):
        if self.consoleEnable and level>= self.loggingLevel:
            cursor = self.textEditConsole.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            if level < logging.ERROR:
                self.textEditConsole.setTextColor(QtCore.Qt.black)
            else:
                self.textEditConsole.setTextColor(QtCore.Qt.red)
            cursor.insertText(message)
            self.textEditConsole.setTextCursor(cursor)
            self.textEditConsole.ensureCursorVisible()
        
    def closeEvent(self,e):
        logger = logging.getLogger("")
        logger.debug( "Saving Configuration" )
        self.saveConfig()
        self.config.commitToDatabase()
        for tab in self.tabDict.values():
            tab.onClose()
        self.currentTab.deactivate()
        self.pulseProgramDialog.done(0)
        self.ExternalParametersSelectionUi.onClose()
        self.dedicatedCountersWindow.close()
        self.pulseProgramDialog.onClose()
        self.scriptingWindow.onClose()
        self.userFunctionsEditor.onClose()
        self.logicAnalyzerWindow.close()
        self.measurementLog.close()
        if self.voltagesEnabled:
            self.voltageControlWindow.close()
        for awgUi in self.AWGUiDict.values():
            awgUi.close()
        numTempAreas = len(self.scanExperiment.area.tempAreas)
        for i in range(numTempAreas):
            if len(self.scanExperiment.area.tempAreas) > 0:
                self.scanExperiment.area.tempAreas[0].win.close()
        # close auxiliary pulsers
        #map(lambda x: x.shutdown(), self.auxiliaryPulsers)
        for p in self.auxiliaryPulsers:
            p.shutdown()
        self.dac.shutdown()

    def saveConfig(self):
        self.config['MainWindow.State'] = self.parent.saveState()
        for tab in self.tabDict.values():
            tab.saveConfig()
        self.config['MainWindow.currentIndex'] = self.tabWidget.currentIndex()
        self.config['MainWindow.pos'] = self.pos()
        self.config['MainWindow.size'] = self.size()
        self.config['MainWindow.isMaximized'] = self.isMaximized()
        self.config['Settings.loggingLevel'] = self.loggingLevel
        self.config['Settings.consoleMaximumLinesNew'] = self.consoleMaximumLines
        self.config['Settings.ShutterNameDict'] = self.shutterNameDict 
        self.config['SettingsTriggerNameDict'] = self.triggerNameDict 
        self.config['Settings.consoleEnable'] = self.consoleEnable 
        self.pulseProgramDialog.saveConfig()
        self.scriptingWindow.saveConfig()
        self.userFunctionsEditor.saveConfig()
        self.shutterUi.saveConfig()
        self.triggerUi.saveConfig()
        self.dedicatedCountersWindow.saveConfig()
        self.logicAnalyzerWindow.saveConfig()
        if self.voltagesEnabled:
            if self.voltageControlWindow:
                self.voltageControlWindow.saveConfig()
        self.ExternalParametersSelectionUi.saveConfig()
        self.globalVariablesUi.saveConfig()
        self.loggerUi.saveConfig()
        self.todoList.saveConfig()
        self.preferencesUi.saveConfig()
        self.measurementLog.saveConfig()
        self.valueHistoryUi.saveConfig()
        self.ExternalParametersUi.saveConfig()
        list(map(lambda x: x.saveConfig(), self.objectListToSaveContext))  # call saveConfig() for each element in the list
        for awgUi in self.AWGUiDict.values():
            awgUi.saveConfig()
        if self.wavemeterInterlock is not None:
            self.wavemeterInterlock.saveConfig()
        
    def onProjectSelection(self):
        ui = ProjectInfoUi(self.project)
        ui.show()
        ui.exec_()
        
    def getCurrentTab(self):
        index = self.tabWidget.currentIndex()
        return self.tabDict.keyAt(index), self.tabDict.at(index)
    
    def setCurrentTab(self, name):
        self.onCurrentChanged(self.tabDict.index(name))

    def onPrint(self, target):
        """Print action is triggered on 'target', which is a plot name"""
        if hasattr( self.currentTab, 'onPrint' ):
            printer = QtPrintSupport.QPrinter(mode=QtPrintSupport.QPrinter.ScreenResolution)
            if self.preferencesUi.preferences().printPreferences.doPrint:
                dialog = QtPrintSupport.QPrintDialog(printer, self)
                dialog.setWindowTitle("Print Document")
                if dialog.exec_() != QtWidgets.QDialog.Accepted:
                    return
            printer.setResolution(self.preferencesUi.preferences().printPreferences.printResolution)
    
            pdfPrinter = QtPrintSupport.QPrinter()
            pdfPrinter.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
            pdfPrinter.setOutputFileName(DataDirectory.DataDirectory().sequencefile(target+".pdf")[0])
            self.currentTab.onPrint(target, printer, pdfPrinter, self.preferencesUi.preferences().printPreferences)

    def onShowDocumentation(self):
        url = "file://" + os.path.join(os.path.dirname(os.path.abspath(__file__)),"docs/_build/html/index.html")
        webbrowser.open(url, new=2)

    def show(self):
        """show ExperimentUi, and any of the other main windows which were previously visible"""
        super(ExperimentUi, self).show()

        # restore dock state of ScanExperiment. Because ScanExperiment is a child QMainWindow of ExperimentUi
        # (rather than an independent window), restoreState must be called after show() is called on the parent
        # widget in order to work properly.
        for tab in self.tabDict.values():
            tabStateName = tab.experimentName+'.MainWindow.State'
            if tabStateName in self.config:
                tab.restoreState(self.config[tabStateName])

        pulseProgramVisible = self.config.get(self.pulseProgramDialog.configname+'.isVisible', True) #pulse program defaults to visible
        if pulseProgramVisible: self.pulseProgramDialog.show()
        else: self.pulseProgramDialog.hide()

        scriptingWindowVisible = self.config.get(self.scriptingWindow.configname+'.isVisible', False)
        if scriptingWindowVisible: self.scriptingWindow.show()
        else: self.scriptingWindow.hide()

        userFunctionsEditorVisible = self.config.get(self.userFunctionsEditor.configname+'.isVisible', False)
        if userFunctionsEditorVisible: self.userFunctionsEditor.show()
        else: self.userFunctionsEditor.hide()

        if self.voltagesEnabled:
            voltageControlWindowVisible = getattr(self.voltageControlWindow.settings, 'isVisible', False)
            if voltageControlWindowVisible: self.voltageControlWindow.show()
            else: self.voltageControlWindow.hide()

        if self.AWGUiDict:
            for awgUi in self.AWGUiDict.values():
                awgUiVisible = self.config.get(awgUi.configname+'.isVisible', False)
                if awgUiVisible: awgUi.show()
                else: awgUi.hide()

        self.setFocus(True)

    def setupFPGAs(self):
        """Setup all Opal Kelly FPGAs"""
        self.dac = DACController() #100 channel DAC board

        #determine name of FPGA used for Pulser, if any
        pulserName=None
        pulserSoftwareEnabled = self.project.isEnabled('software', 'Pulser')
        if pulserSoftwareEnabled:
            pulserHardware = next(iter(pulserSoftwareEnabled.values()))['hardware']
            hardwareObjName, hardwareName = project.fromFullName(pulserHardware)
            if hardwareObjName=='Opal Kelly FPGA':
                pulserName=hardwareName
        self.settings = FPGASettings() #settings for pulser specifically

        #determine name of FPGA used for DAC, if any
        dacName=None
        voltageSoftwareEnabled = self.project.isEnabled('software', 'Voltages')
        if voltageSoftwareEnabled:
            voltageHardware = next(iter(voltageSoftwareEnabled.values()))['hardware']
            hardwareObjName, hardwareName = project.fromFullName(voltageHardware)
            if hardwareObjName=='Opal Kelly FPGA':
                dacName=hardwareName

        self.OK_FPGA_Dict = self.pulser.listBoards() #list all connected Opal Kelly FPGA boards
        logger.info( "Opal Kelly Devices found: {0}".format({k:v.modelName for k,v in self.OK_FPGA_Dict.items()}) )

        enabledFPGAs = self.project.isEnabled('hardware', 'Opal Kelly FPGA') #Dict of enabled FPGAs
        for FPGAName, FPGAConfig in enabledFPGAs.items():
            FPGA = self.pulser if FPGAName==pulserName else (self.dac if FPGAName==dacName else OKBase())
            deviceName=FPGAConfig.get('device') #The 'device' field of an FPGA should be the identifier of the FPGA.
            if not deviceName:
                logger.error("No FPGA specified: 'device' field missing in Opal Kelly FPGA: '{0}' config".format(FPGAName))
            elif deviceName not in self.OK_FPGA_Dict:
                logger.error("FPGA device {0} specified in Opal Kelly FPGA: '{1}' config cannot be found".format(deviceName, FPGAName))
            else:
                device=self.OK_FPGA_Dict[deviceName]
                FPGA.openBySerial(device.serial)
                bitFile=FPGAConfig.get('bitFile')
                checkFileValid(bitFile, 'bitfile', FPGAName)
                if FPGAName==pulserName:
                    configFile = os.path.splitext(bitFile)[0] + '.xml'
                    checkFileValid(configFile, 'config file', FPGAName)
                if FPGAConfig.get('uploadOnStartup'):
                    FPGA.uploadBitfile(bitFile)
                    logger.info("Uploaded file '{0}' to {1} (model {2}) in Opal Kelly FPGA: '{3}' config".format(bitFile, deviceName, device.modelName, FPGAName))
                if FPGAName==pulserName:   # check and make sure correct hardware is loaded
                    try:
                        FPGA.pulserConfiguration(configFile)
                    except PulserHardwareException:
                        logger.exception('PulserHardwareException occurred, likely because firmware must be uploaded. Please restart the program and upload the firmware.')
                        if not self.project.exptConfig['showGui']: #force the GUI to be shown next time
                            self.project.exptConfig['showGui'] = True
                            with open(self.project.exptConfigFilename, 'w') as f:
                                yaml.dump(self.project.exptConfig, f, default_flow_style=False)
                        sys.exit("Please restart program and upload firmware (config GUI will be shown)")
                if FPGA==self.pulser:
                    self.settings.deviceSerial = device.serial
                    self.settings.deviceDescription = device.identifier
                    self.settings.deviceInfo = device
        pulserHardwareId = self.pulser.hardwareConfigurationId()
        if pulserHardwareId:
            logger.info("Pulser Configuration {0:x}".format(pulserHardwareId))
        else:
            logger.error("No pulser available")

    def instantiateAuxiliaryPulsers(self):
        self.auxiliaryPulsers = list()
        for FPGAName, FPGAConfig in self.project.isEnabled('hardware', 'Auxiliary Pulser').items():
            FPGA = PulserHardware()
            deviceName=FPGAConfig.get('device') #The 'device' field of an FPGA should be the identifier of the FPGA.
            if not deviceName:
                logger.error("No FPGA specified: 'device' field missing in Auxiliary Opal Kelly FPGA: '{0}' config".format(FPGAName))
            elif deviceName not in self.OK_FPGA_Dict:
                logger.error("FPGA device {0} specified in Auxiliary Opal Kelly FPGA: '{1}' config cannot be found".format(deviceName, FPGAName))
            else:
                device=self.OK_FPGA_Dict[deviceName]
                FPGA.openBySerial(device.serial)
                bitFile=FPGAConfig.get('bitFile')
                checkFileValid(bitFile, 'bitfile', FPGAName)
                configFile = os.path.splitext(bitFile)[0] + '.xml'
                checkFileValid(configFile, 'config file', FPGAName)
                if FPGAConfig.get('uploadOnStartup'):
                    FPGA.uploadBitfile(bitFile)
                    logger.info("Uploaded file '{0}' to {1} (model {2}) in Opal Kelly FPGA: '{3}' config".format(bitFile, deviceName, device.modelName, FPGAName))
                FPGA.pulserConfiguration(configFile)
                pulserHardwareId = self.pulser.hardwareConfigurationId()
                if pulserHardwareId:
                    logger.info("Auxiliary Pulser {1} Configuration {0:x}".format(pulserHardwareId, FPGAName))
                else:
                    logger.error("No pulser available")
                if FPGAConfig.get('PulserParameters'):
                    ui, _ = self.instantiateParametersUi(FPGA, "{0} Pulser Config".format(FPGAName),
                                                 "{0}.PulserParameterUi".format(FPGAName), self.config, self.globalVariablesUi.globalDict)
                    self.objectListToSaveContext.append(ui)
                if FPGAConfig.get('DDS'):
                    ui, _ = self.instantiateDDSUi(FPGA, "{0} DDS".format(FPGAName), "{0}.DDSUi".format(FPGAName), self.config, self.globalVariablesUi.globalDict)
                    self.objectListToSaveContext.append(ui)
                if FPGAConfig.get('DAC'):
                    ui, _ = self.instantiateDACUi(FPGA, "{0} DAC".format(FPGAName), "{0}.dacUi".format(FPGAName), self.config, self.globalVariablesUi.globalDict)
                    self.objectListToSaveContext.append(ui)
                if FPGAConfig.get('Shutters'):
                    ui, _ = self.instantiateShutterUi(FPGA, "{0} Shutter".format(FPGAName), "{0}.ShutterUi".format(FPGAName), self.config, self.globalVariablesUi.globalDict, None, None)
                    self.objectListToSaveContext.append(ui)
                self.auxiliaryPulsers.append(FPGA)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    project = Project() #loads in the project through the config files/config GUIs
    logger = logging.getLogger("")
    setID('TrappedIons.FPGAControlProgram') #Makes the icon in the Windows taskbar match the icon set in Qt Designer

    overrideConfigFile = project.projectConfig.get('configurationFile')
    overrideFileType = {'.yml': 'yaml', '.yaml': 'yaml', '.db': 'sqlite'}.get(os.path.splitext(overrideConfigFile)[1], 'sqlite') if overrideConfigFile else None
    loadFromDate = project.projectConfig.get('configurationFile')
    with configshelve.configshelve(project.dbConnection, loadFromDate=project.projectConfig.get('loadFromDateTime', None),
                                   filename=overrideConfigFile, filetype=overrideFileType) as config:
        with ExperimentUi(config, project) as ui:
            ui.setupUi(ui)
            LoggingSetup.qtHandler.textWritten.connect(ui.onMessageWrite)
            ui.show()
            sys.exit(app.exec_())
