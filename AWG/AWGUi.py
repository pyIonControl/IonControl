import copy
import logging
import os
import itertools
import yaml
from collections import OrderedDict

import PyQt5.uic
from PyQt5 import QtGui, QtCore, QtWidgets
from pyqtgraph.dockarea import DockArea, Dock

from AWG.AWGChannelUi import AWGChannelUi
from AWG.AWGTableModel import AWGTableModel
from AWG.AWGSegmentModel import AWGSegmentNode, AWGSegment, AWGSegmentSet, nodeTypes
from AWG.VarAsOutputChannel import VarAsOutputChannel
from modules.PyqtUtility import BlockSignals
from modules.SequenceDict import SequenceDict
from modules.quantity import Q
from modules.GuiAppearance import saveGuiState, restoreGuiState
from modules.enum import enum
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from ProjectConfig.Project import getProject

AWGuipath = os.path.join(os.path.dirname(__file__), '..', 'ui/AWG.ui')
AWGForm, AWGBase = PyQt5.uic.loadUiType(AWGuipath)

class Settings(object):
    """Settings associated with AWGUi. Each entry in the settings menu has a corresponding Settings object.

    Attributes:
       deviceSettings(dict): dynamic settings of the device, controlled by the parameterTable. Elements are defined
          in the device's 'parameters' method
       channelSettingsList (list of dicts): each element corresponds to a channel of the AWG. Each element is a dict,
          with keys that determine the channel's setting (e.g. 'plotEnabled', etc.)
       filename (str): the filename from which to save/load AWG segment data
       varDict (SequenceDict): the list of variables which determine the AWG waveform
       saveIfNecessary (function): the AWGUi's function that save's the settings
       replot (function): the AWGUi's function that replots all waveforms

    Note that "deviceProperties" are fixed settings of an AWG device, while "deviceSettings" are settings that can be
    changed on the fly.
    """
    plotStyles = enum('lines', 'points', 'linespoints')
    saveIfNecessary = None
    replot = None
    deviceProperties = dict()
    stateFields = {'channelSettingsList':list(),
                   'deviceSettings':dict(),
                   'filename':'',
                   'varDict':SequenceDict(),
                   'cacheDepth':0
                   }
    def __init__(self):
        [setattr(self, field, copy.copy(fieldDefault)) for field, fieldDefault in list(self.stateFields.items())]

    def __setstate__(self, state):
        self.__dict__ = state

    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field, None) for field in list(self.stateFields.keys()))==tuple(getattr(other, field, None) for field in list(self.stateFields.keys()))

    def __ne__(self, other):
        return not self == other

    def update(self, other):
        [setattr(self, field, getattr(other, field)) for field in list(self.stateFields.keys()) if hasattr(other, field)]


class AWGUi(AWGForm, AWGBase):
    varDictChanged = QtCore.pyqtSignal(object)
    def __init__(self, deviceClass, config, globalDict, parent=None):
        AWGBase.__init__(self, parent)
        AWGForm.__init__(self)
        self.config = config
        self.configname = 'AWGUi.' + deviceClass.displayName
        self.globalDict = globalDict
        self.autoSave = self.config.get(self.configname+'.autoSave', True)
        self.waveformCache = OrderedDict()
        self.settingsDict = self.config.get(self.configname+'.settingsDict', dict())
        self.settingsName = self.config.get(self.configname+'.settingsName', '')
        # self.settingsDict=dict()
        # self.settingsName=''
        self.recentFiles = self.config.get(self.configname+'.recentFiles', dict()) #dict of form {basename: filename}, where filename has path and basename doesn't
        self.lastDir = self.config.get(self.configname+'.lastDir', getProject().configDir)
        Settings.deviceProperties = deviceClass.deviceProperties
        Settings.saveIfNecessary = self.saveIfNecessary
        Settings.replot = self.replot
        for settings in list(self.settingsDict.values()): #make sure all pickled settings are consistent with device, in case it changed
            for channel in range(deviceClass.deviceProperties['numChannels']):
                if channel >= len(settings.channelSettingsList): #create new channels if it's necessary
                    settings.channelSettingsList.append({
                        'segmentDataRoot':AWGSegmentNode(None),
                        'segmentTreeState':None,
                        'plotEnabled':True,
                        'plotStyle':Settings.plotStyles.lines})
                else:
                    settings.channelSettingsList[channel].setdefault('segmentDataRoot', AWGSegmentNode(None))
                    settings.channelSettingsList[channel].setdefault('segmentTreeState', None)
                    settings.channelSettingsList[channel].setdefault('plotEnabled', True)
                    settings.channelSettingsList[channel].setdefault('plotStyle', Settings.plotStyles.lines)
        self.settings = Settings() #we always run settings through the constructor
        if self.settingsName in self.settingsDict:
            self.settings.update(self.settingsDict[self.settingsName])
        self.device = deviceClass(self.settings)

    def setupUi(self, parent):
        logger = logging.getLogger(__name__)
        AWGForm.setupUi(self, parent)
        self.setWindowTitle(self.device.displayName)

        self._varAsOutputChannelDict = dict()
        self.area = DockArea()
        self.splitter.insertWidget(0, self.area)
        self.awgChannelUiList = []
        for channel in range(self.device.deviceProperties['numChannels']):
            awgChannelUi = AWGChannelUi(channel, self.settings, self.globalDict, self.waveformCache, parent=self)
            awgChannelUi.setupUi(awgChannelUi)
            awgChannelUi.dependenciesChanged.connect(self.onDependenciesChanged)
            self.awgChannelUiList.append(awgChannelUi)
            dock = Dock("AWG Channel {0}".format(channel))
            dock.addWidget(awgChannelUi)
            self.area.addDock(dock, 'right')
            self.device.waveforms[channel] = awgChannelUi.waveform
        self.refreshVarDict()

        # Settings control
        self.saveButton.clicked.connect( self.onSave )
        self.removeButton.clicked.connect( self.onRemove )
        self.reloadButton.clicked.connect( self.onReload )
        self.settingsModel = QtCore.QStringListModel()
        self.settingsComboBox.setModel(self.settingsModel)
        self.settingsModel.setStringList( sorted(self.settingsDict.keys()) )
        self.settingsComboBox.setCurrentIndex( self.settingsComboBox.findText(self.settingsName) )
        self.settingsComboBox.currentIndexChanged[str].connect( self.onLoad )
        self.settingsComboBox.lineEdit().editingFinished.connect( self.onComboBoxEditingFinished )
        self.autoSaveCheckBox.setChecked(self.autoSave)
        self.saveButton.setEnabled( not self.autoSave )
        self.saveButton.setVisible( not self.autoSave )
        self.reloadButton.setEnabled( not self.autoSave )
        self.reloadButton.setVisible( not self.autoSave )
        self.autoSaveCheckBox.stateChanged.connect(self.onAutoSave)

        #programming options table
        self.programmingOptionsTable.setupUi(globalDict=self.globalDict, parameterDict=self.device.parameters())
        self.programmingOptionsTable.valueChanged.connect( self.device.update )

        # Table
        self.tableModel = AWGTableModel(self.settings, self.globalDict)
        self.tableView.setModel(self.tableModel)
        self.tableModel.valueChanged.connect(self.onValue)
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(self.tableModel.column.value, self.delegate)

        #File
        self.filenameModel = QtCore.QStringListModel()
        self.filenameComboBox.setModel(self.filenameModel)
        self.filenameModel.setStringList( [basename for basename, filename in list(self.recentFiles.items()) if os.path.exists(filename)] )
        self.filenameComboBox.setCurrentIndex(self.filenameComboBox.findText(os.path.basename(self.settings.filename)))
        self.filenameComboBox.currentIndexChanged[str].connect(self.onFilename)
        self.removeFileButton.clicked.connect(self.onRemoveFile)
        self.newFileButton.clicked.connect(self.onNewFile)
        self.openFileButton.clicked.connect(self.onOpenFile)
        self.saveFileButton.clicked.connect(self.onSaveFile)
        self.reloadFileButton.clicked.connect(self.onReloadFile)

        #cache
        self.cacheDepthSpinBox.setValue(self.settings.cacheDepth)
        self.cacheDepthSpinBox.valueChanged.connect(self.onCacheDepth)
        self.clearCacheButton.clicked.connect(self.onClearCache)

        #status bar
        self.label = QtGui.QLabel('Sample Rate: {0}'.format(self.settings.deviceProperties['sampleRate']))
        self.statusbar.addWidget(self.label)

        #Restore GUI state
        state = self.config.get(self.configname+'.state')
        pos = self.config.get(self.configname+'.pos')
        size = self.config.get(self.configname+'.size')
        isMaximized = self.config.get(self.configname+'.isMaximized')
        dockAreaState = self.config.get(self.configname+'.dockAreaState')
        guiState = self.config.get(self.configname+".guiState")
        restoreGuiState(self, guiState)
        try:
            if pos:
                self.move(pos)
            if size:
                self.resize(size)
            if isMaximized:
                self.showMaximized()
            if state:
                self.restoreState(state)
            for awgChannelUi in self.awgChannelUiList:
                channelGuiState = self.config[self.configname+"channel{0}.guiState".format(awgChannelUi.channel)]
                restoreGuiState(awgChannelUi, channelGuiState)
        except Exception as e:
            logger.warning("Error on restoring state in AWGUi {0}. Exception occurred: {1}".format(self.device.displayName, e))
        try:
            if dockAreaState:
                self.area.restoreState(dockAreaState)
        except Exception as e:
            logger.warning("Cannot restore dock state in AWGUi {0}. Exception occurred: {1}".format(self.device.displayName, e))
            self.area.deleteLater()
            self.area = DockArea()
            self.splitter.insertWidget(0, self.area)
            for channelUi in self.awgChannelUiList:
                dock = Dock("AWG Channel {0}".format(channel))
                dock.addWidget(channelUi)
                self.area.addDock(dock, 'right')
        self.saveIfNecessary()

    def onCacheDepth(self, newVal):
        self.settings.cacheDepth = newVal
        self.saveIfNecessary()

    def onClearCache(self):
        self.waveformCache.clear()

    def onComboBoxEditingFinished(self):
        """a settings name is typed into the combo box"""
        currentText = str(self.settingsComboBox.currentText())
        if self.settingsName != currentText:
            self.settingsName = currentText
            if self.settingsName not in self.settingsDict:
                self.settingsDict[self.settingsName] = copy.deepcopy(self.settings)
            self.onLoad(self.settingsName)

    def saveIfNecessary(self):
        """save the current settings if autosave is on and something has changed"""
        currentText = str(self.settingsComboBox.currentText())
        if self.settingsDict.get(self.settingsName)!=self.settings or currentText!=self.settingsName:
            if self.autoSave:
                self.onSave()
            else:
                self.saveButton.setEnabled(True)

    def replot(self):
        """plot all channels"""
        for channelUi in self.awgChannelUiList:
            channelUi.replot()

    def onSave(self):
        """save current settings"""
        self.settingsName = str(self.settingsComboBox.currentText())
        self.settingsDict[self.settingsName] = copy.deepcopy(self.settings)
        with BlockSignals(self.settingsComboBox) as w:
            self.settingsModel.setStringList( sorted(self.settingsDict.keys()) )
            w.setCurrentIndex(w.findText(self.settingsName))
        self.saveButton.setEnabled(False)

    def saveConfig(self):
        """save GUI configuration to config"""
        self.config[self.configname+".guiState"] = saveGuiState(self)
        for awgChannelUi in self.awgChannelUiList:
            self.config[self.configname+"channel{0}.guiState".format(awgChannelUi.channel)] = saveGuiState(awgChannelUi)
            self.settings.channelSettingsList[awgChannelUi.channel]['segmentTreeState'] = awgChannelUi.segmentView.saveTreeState()
        self.config[self.configname+'.state'] = self.saveState()
        self.config[self.configname+'.pos'] = self.pos()
        self.config[self.configname+'.size'] = self.size()
        self.config[self.configname+'.isMaximized'] = self.isMaximized()
        self.config[self.configname+'.isVisible'] = self.isVisible()
        self.config[self.configname+'.dockAreaState'] = self.area.saveState()
        self.config[self.configname+'.settingsDict'] = self.settingsDict
        self.config[self.configname+'.settingsName'] = self.settingsName
        self.config[self.configname+'.autoSave'] = self.autoSave
        self.config[self.configname+'.recentFiles'] = self.recentFiles
        self.config[self.configname+'.lastDir'] = self.lastDir

    def onRemove(self):
        """Remove current settings from combo box"""
        name = str(self.settingsComboBox.currentText())
        if name in self.settingsDict:
            self.settingsDict.pop(name)
            self.settingsName = list(self.settingsDict.keys())[0] if self.settingsDict else ''
            with BlockSignals(self.settingsComboBox) as w:
                self.settingsModel.setStringList( sorted(self.settingsDict.keys()) )
                w.setCurrentIndex(w.findText(self.settingsName))
            self.onLoad(self.settingsName)

    def onReload(self):
        """Reload settings"""
        name = str(self.settingsComboBox.currentText())
        self.onLoad(name)

    def loadSetting(self, name):
        if name and self.settingsComboBox.findText(name)>=0:
            self.settingsComboBox.setCurrentIndex( self.settingsComboBox.findText(name) )
            self.onLoad(name)
       
    def onLoad(self, name):
        """load settings"""
        for channelUi in self.awgChannelUiList:
            self.settings.channelSettingsList[channelUi.channel]['segmentTreeState'] = channelUi.segmentView.saveTreeState()
        name = str(name)
        if name in self.settingsDict:
            self.settingsName = name
            self.tableModel.beginResetModel()
            [channelUi.segmentModel.beginResetModel() for channelUi in self.awgChannelUiList]
            self.settings.update(self.settingsDict[self.settingsName])
            self.programmingOptionsTable.setParameters( self.device.parameters() )
            self.saveButton.setEnabled(False)
            with BlockSignals(self.filenameComboBox) as w:
                w.setCurrentIndex(w.findText(os.path.basename(self.settings.filename)))
            with BlockSignals(self.cacheDepthSpinBox) as w:
                w.setValue(self.settings.cacheDepth)
            for channelUi in self.awgChannelUiList:
                channelUi.waveform.updateDependencies()
                channelUi.plotCheckbox.setChecked(self.settings.channelSettingsList[channelUi.channel]['plotEnabled'])
                with BlockSignals(channelUi.styleComboBox) as w:
                    w.setCurrentIndex(self.settings.channelSettingsList[channelUi.channel]['plotStyle'])
                channelUi.segmentModel.root = self.settings.channelSettingsList[channelUi.channel]['segmentDataRoot']
                channelUi.replot()
            self.onDependenciesChanged()
            self.saveButton.setEnabled(False)
            self.tableModel.endResetModel()
            [channelUi.segmentModel.endResetModel() for channelUi in self.awgChannelUiList]
            for channelUi in self.awgChannelUiList:
                channelUi.segmentView.restoreTreeState(self.settings.channelSettingsList[channelUi.channel]['segmentTreeState'])

    def onAutoSave(self, checked):
        """autosave is changed"""
        self.autoSave = checked
        self.saveButton.setEnabled( not checked )
        self.saveButton.setVisible( not checked )
        self.reloadButton.setEnabled( not checked )
        self.reloadButton.setVisible( not checked )
        if checked:
            self.onSave()

    def onValue(self, var=None, value=None):
        """variable value is changed in the table"""
        self.saveIfNecessary()
        self.replot()

    def evaluate(self, name):
        """re-evaluate the text in the tableModel (happens when a global changes)"""
        self.tableModel.evaluate(name)
        self.programmingOptionsTable.evaluate(name)

    def refreshVarDict(self):
        """refresh the variable dictionary by checking all waveform dependencies"""
        allDependencies = set()
        [channelUi.waveform.updateDependencies() for channelUi in self.awgChannelUiList]
        [allDependencies.update(channelUi.waveform.dependencies) for channelUi in self.awgChannelUiList]
        default = lambda varname:{'value':Q(1, 'us'), 'text':None} if varname.startswith('T0') else {'value':Q(0), 'text':None}
        deletions = [varname for varname in self.settings.varDict if varname not in allDependencies]
        [self.settings.varDict.pop(varname) for varname in deletions] #remove all values that aren't dependencies anymore
        [self.settings.varDict.setdefault(varname, default(varname)) for varname in allDependencies] #add missing values
        self.settings.varDict.sort(key = lambda val: -1 if val[0].startswith('Duration') else ord( str(val[0])[0] ))
        self.varDictChanged.emit(self.varAsOutputChannelDict)
        for channelUi in self.awgChannelUiList:
            channelUi.replot()

    def onDependenciesChanged(self, channel=None):
        """When dependencies change, refresh all variables"""
        self.tableModel.beginResetModel()
        self.refreshVarDict()
        self.tableModel.endResetModel()
        self.saveIfNecessary()

    def onFilename(self, basename):
        """filename combo box is changed. Open selected file"""
        basename = str(basename)
        filename = self.recentFiles[basename]
        if os.path.isfile(filename) and filename!=self.settings.filename:
            self.openFile(filename)

    def onRemoveFile(self):
        """Remove file button is clicked. Remove filename from combo box."""
        text = str(self.filenameComboBox.currentText())
        index = self.filenameComboBox.findText(text)
        if text in self.recentFiles:
            self.recentFiles.pop(text)
        with BlockSignals(self.filenameComboBox) as w:
            self.filenameModel.setStringList(list(self.recentFiles.keys()))
            w.setCurrentIndex(-1)
            self.onFilename(w.currentText())

    def onNewFile(self):
        """New button is clicked. Pop up dialog asking for new name, and create file."""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'New File', self.lastDir, 'YAML (*.yml)')
        if filename:
            self.lastDir, basename = os.path.split(filename)
            self.recentFiles[basename] = filename
            self.settings.filename = filename
            with BlockSignals(self.filenameComboBox) as w:
                self.filenameModel.setStringList(list(self.recentFiles.keys()))
                w.setCurrentIndex(w.findText(basename))
            self.onSaveFile()

    def onOpenFile(self):
        """Open file button is clicked. Pop up dialog asking for filename."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', self.lastDir, 'YAML (*.yml)')
        if filename:
            self.openFile(filename)

    def openFile(self, filename):
        """Open the file 'filename'"""
        if os.path.exists(filename):
            self.lastDir, basename = os.path.split(filename)
            self.recentFiles[basename] = filename
            self.settings.filename = filename
            with BlockSignals(self.filenameComboBox) as w:
                self.filenameModel.setStringList(list(self.recentFiles.keys()))
                w.setCurrentIndex(w.findText(basename))
            with open(filename, 'r') as f:
                yamldata = yaml.load(f)
            variables = yamldata.get('variables')
            channelData = yamldata.get('channelData')
            self.tableModel.beginResetModel()
            [channelUi.segmentModel.beginResetModel() for channelUi in self.awgChannelUiList]
            if channelData:
                for channelUi in self.awgChannelUiList:
                    if channelUi.channel < len(channelData):
                        self.settings.channelSettingsList[channelUi.channel]['segmentDataRoot'] = self.convertListToNodes(channelData[channelUi.channel], isRoot=True)
                        channelUi.segmentModel.root = self.settings.channelSettingsList[channelUi.channel]['segmentDataRoot']
            if variables:
                for varname, vardata in list(variables.items()):
                    self.settings.varDict.setdefault(varname, dict())
                    self.settings.varDict[varname]['value'] = Q(vardata['value'], vardata['unit'])
                    self.settings.varDict[varname]['text'] = vardata['text']
            for channelUi in self.awgChannelUiList:
                channelUi.waveform.updateDependencies()
                channelUi.replot()
            self.onDependenciesChanged()
            self.tableModel.endResetModel()
            [channelUi.segmentModel.endResetModel() for channelUi in self.awgChannelUiList]
            [channelUi.segmentView.expandAll() for channelUi in self.awgChannelUiList]
        else:
            logging.getLogger(__name__).warning("file '{0}' does not exist".format(filename))
            if filename in self.recentFiles:
                del self.recentFiles[filename]
                with BlockSignals(self.filenameComboBox) as w:
                    self.filenameModel.setStringList(list(self.recentFiles.keys()))
                    w.setCurrentIndex(-1)

    def convertNodeToList(self, node):
        nodeList = []
        for childNode in node.children:
            if childNode.nodeType==nodeTypes.segment:
                nodeList.append( {'equation':childNode.equation,
                                  'duration':childNode.duration,
                                  'enabled':childNode.enabled}
                                 )
            elif childNode.nodeType==nodeTypes.segmentSet:
                nodeList.append( {'repetitions':childNode.repetitions,
                                  'enabled':childNode.enabled,
                                  'segments':self.convertNodeToList(childNode)}
                                 )
        return nodeList

    def convertListToNodes(self, data, parent=None, enabled=True, repetitions=None, isRoot=False):
        node = AWGSegmentNode(parent=None) if isRoot else AWGSegmentSet(parent=parent, enabled=enabled, repetitions=repetitions)
        for segment in data:
            if 'duration' in segment:
                childNode = AWGSegment(parent=node,
                                       equation=segment['equation'],
                                       duration=segment['duration'],
                                       enabled=segment['enabled'])
                node.children.append(childNode)
            elif 'repetitions' in segment:
                segmentSet = self.convertListToNodes(segment['segments'], parent=node, enabled=segment['enabled'], repetitions=segment['repetitions'])
                node.children.append(segmentSet)
            else:
                logging.getLogger(__name__).error("Unable to convert list to nodes")
        return node

    def onSaveFile(self):
        """Save button is clicked. Save data to segment file"""
        channelData = []
        for channelSettings in self.settings.channelSettingsList:
            segmentData = self.convertNodeToList(channelSettings['segmentDataRoot'])
            channelData.append(segmentData)
        yamldata = {'channelData': channelData}
        variables={varname:
                             {'value':float(varValueTextDict['value'].toStringTuple()[0]),
                              'unit':varValueTextDict['value'].toStringTuple()[1],
                              'text':varValueTextDict['text']}
                         for varname, varValueTextDict in list(self.settings.varDict.items())}
        yamldata.update({'variables':variables})
        with open(self.settings.filename, 'w') as f:
            yaml.dump(yamldata, f, default_flow_style=False)

    def onReloadFile(self):
        self.openFile(self.settings.filename)

    @QtCore.pyqtProperty(dict)
    def varAsOutputChannelDict(self):
        """dict of output channels, for use in scans"""
        for varname in self.settings.varDict:
            if varname not in self._varAsOutputChannelDict:
                self._varAsOutputChannelDict[varname] = VarAsOutputChannel(self, varname, self.globalDict)
        deletions = [varname for varname in self._varAsOutputChannelDict if varname not in self.settings.varDict]
        [self._varAsOutputChannelDict.pop(varname) for varname in deletions] #remove all values that aren't dependencies anymore
        return self._varAsOutputChannelDict

    def close(self):
        self.saveConfig()
        numTempAreas = len(self.area.tempAreas)
        for i in range(numTempAreas):
            if len(self.area.tempAreas) > 0:
                self.area.tempAreas[0].win.close()
        super(AWGUi, self).close()

if __name__ == '__main__':
    from AWG.AWGDevices import DummyAWG
    import sys
    from ProjectConfig.Project import Project
    from persist import configshelve
    from GlobalVariables.GlobalVariable import GlobalVariablesLookup
    app = QtWidgets.QApplication(sys.argv)
    project = Project()
    guiConfigFile = os.path.join(project.projectDir, '.gui-config/ExperimentUi.config.db')
    with configshelve.configshelve(guiConfigFile) as config:
        globalDict = GlobalVariablesLookup(config.get('GlobalVariables', dict()))
        ui = AWGUi(DummyAWG, config, globalDict)
        ui.setupUi(ui)
        ui.show()
        sys.exit(app.exec_())