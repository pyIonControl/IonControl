# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


import os.path
import shutil
import copy

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic
from PyQt5.Qsci import QsciScintilla
import logging
from datetime import datetime
from ProjectConfig.Project import getProject
from modules.PyqtUtility import BlockSignals
from .Script import Script, scriptFunctions, scriptDocs
from .ScriptHandler import ScriptHandler
from pulseProgram.PulseProgramSourceEdit import PulseProgramSourceEdit
from collections import OrderedDict
from pathlib import Path
from gui.FileTree import ensurePath, onExpandOrCollapse, FileTreeMixin, OrderedList, OptionsWindow

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/Scripting.ui')
ScriptingWidget, ScriptingBase = PyQt5.uic.loadUiType(uipath)

class ScriptingUi(FileTreeMixin, ScriptingWidget, ScriptingBase):
    """Ui for the scripting interface."""
    scriptFinishedSignal = QtCore.pyqtSignal()
    def __init__(self, experimentUi):
        ScriptingWidget.__init__(self)
        ScriptingBase.__init__(self)
        self.config = experimentUi.config
        self.experimentUi = experimentUi
        self.recentFiles = dict() #dict of form {shortname: fullname}, where fullname has path and shortname doesn't
        self.defaultDir = Path(getProject().configDir+'/Scripts')
        self.script = Script(homeDir=self.defaultDir) #encapsulates the script
        self.scriptHandler = ScriptHandler(self.script, experimentUi) #handles interface to the script
        self.revert = False
        self.allowFileViewerLoad = True
        self.initcode = ''
        if not self.defaultDir.exists():
            defaultScriptsDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/Scripts')) #/IonControl/config/Scripts directory
            shutil.copytree(defaultScriptsDir, str(self.defaultDir)) #Copy over all example scripts

    def setupUi(self, parent):
        super(ScriptingUi, self).setupUi(parent)
        self.configname = 'Scripting'


        #initialize default options
        self.optionsWindow = OptionsWindow(self.config, 'ScriptingEditorOptions')
        self.optionsWindow.setupUi(self.optionsWindow)
        self.actionOptions.triggered.connect(self.onOpenOptions)
        self.optionsWindow.OptionsChangedSignal.connect(self.updateOptions)
        self.updateOptions()
        if self.optionsWindow.defaultExpand:
            onExpandOrCollapse(self.fileTreeWidget, True, True)

        #setup console
        self.consoleMaximumLines = self.config.get(self.configname+'.consoleMaximumLinesNew', 100)
        self.consoleEnable = self.config.get(self.configname+'.consoleEnable', True)
        self.consoleClearButton.clicked.connect( self.onClearConsole )
        self.linesSpinBox.valueChanged.connect( self.onConsoleMaximumLinesChanged )
        self.linesSpinBox.setValue( self.consoleMaximumLines )
        self.checkBoxEnableConsole.stateChanged.connect( self.onEnableConsole )
        self.checkBoxEnableConsole.setChecked( self.consoleEnable )
        
        #setup editor
        self.textEdit = PulseProgramSourceEdit()
        self.textEdit.setupUi(self.textEdit, extraKeywords1=[], extraKeywords2=scriptFunctions)
        self.textEdit.textEdit.currentLineMarkerNum = 9
        self.textEdit.textEdit.markerDefine(QsciScintilla.Background, self.textEdit.textEdit.currentLineMarkerNum) #This is a marker that highlights the background
        self.textEdit.textEdit.setMarkerBackgroundColor(QtGui.QColor(0xd0, 0xff, 0xd0), self.textEdit.textEdit.currentLineMarkerNum)
        self.textEdit.setPlainText(self.script.code)
        self.splitterVertical.insertWidget(0, self.textEdit)
        
        #setup documentation list
        self.getDocs()
        self.docTreeWidget.setHeaderLabels(['Available Script Functions'])
        for funcDef, funcDesc in list(self.docDict.items()):
            itemDef  = QtWidgets.QTreeWidgetItem(self.docTreeWidget, [funcDef])
            self.docTreeWidget.addTopLevelItem(itemDef)
            QtWidgets.QTreeWidgetItem(itemDef, [funcDesc])
            self.docTreeWidget.setWordWrap(True)

        #load recent files, also checks if data was saved correctly and if files still exist
        savedfiles = self.config.get( self.configname+'.recentFiles', OrderedList())
        self.initRecentFiles(savedfiles)
        self.initComboBox()

        #load last opened file
        self.script.fullname = self.config.get( self.configname+'.script.fullname', '' )
        self.initLoad()

        #connect buttons
        self.script.repeat = self.config.get(self.configname+'.repeat',False)
        self.repeatButton.setChecked(self.script.repeat)
        self.repeatButton.clicked.connect( self.onRepeat )
        self.script.slow = self.config.get(self.configname+'.slow',False)
        self.slowButton.setChecked(self.script.slow)
        self.slowButton.clicked.connect( self.onSlow )
        self.revert = self.config.get(self.configname+'.revert',False)
        self.revertButton.setChecked(self.revert)
        self.revertButton.clicked.connect( self.onRevert )
        #File control actions
        self.actionOpen.triggered.connect( self.onLoad )
        self.actionSave.triggered.connect( self.onSave )
        self.actionReset.triggered.connect(self.onReset)
        self.actionNew.triggered.connect( self.onNew )
        #Script control actions
        self.actionStartScript.triggered.connect( self.onStartScript )
        self.actionPauseScript.triggered.connect( self.onPauseScript )
        self.actionStopScript.triggered.connect( self.onStopScript )
        self.actionPauseScriptAndScan.triggered.connect( self.onPauseScriptAndScan )
        self.actionStopScriptAndScan.triggered.connect( self.onStopScriptAndScan )
        #Script finished signal
        self.script.finished.connect( self.onFinished )

        self.setWindowTitle(self.configname)
        self.setWindowIcon(QtGui.QIcon(":/other/icons/Terminal-icon.png"))
        self.statusLabel.setText("Idle")
        windowState = self.config.get(self.configname+".guiState")
        if windowState:
            self.restoreState(windowState)
        self.setCorner(QtCore.Qt.BottomRightCorner,QtCore.Qt.RightDockWidgetArea)
        self.setCorner(QtCore.Qt.TopRightCorner,QtCore.Qt.RightDockWidgetArea)
        self.setCorner(QtCore.Qt.TopLeftCorner,QtCore.Qt.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.BottomLeftCorner,QtCore.Qt.LeftDockWidgetArea)

    def onOpenOptions(self):
        self.optionsWindow.show()
        self.optionsWindow.setWindowState(QtCore.Qt.WindowActive)
        self.optionsWindow.raise_()

    def updateOptions(self):
        self.filenameComboBox.setMaxCount(self.optionsWindow.lineno)
        self.displayFullPathNames = self.optionsWindow.displayPath
        self.script.dispfull = self.optionsWindow.displayPath
        self.defaultExpandAll = self.optionsWindow.defaultExpand
        self.updateFileComboBoxNames(self.displayFullPathNames)

    @QtCore.pyqtSlot()
    def onStartScript(self):
        """Start script button is clicked"""
        if not self.script.isRunning():
            logger = logging.getLogger(__name__)
            message = "script {0} started at {1}".format(self.script.fullname, str(datetime.now()))
            logger.info(message)
            self.writeToConsole(message, color='blue')
            self.onSave()
            self.enableScriptChange(False)
            self.actionPauseScript.setChecked(False)
            self.statusLabel.setText("Script running")
            if self.revert:
                self.savedState = True
                self.saveSettingsState()
            else:
                self.savedState = False
            self.scriptHandler.onStartScript()
            
    @QtCore.pyqtSlot(bool)
    def onPauseScript(self, paused):
        """Pause script button is clicked"""
        logger = logging.getLogger(__name__)
        message = "Script is paused" if paused else "Script is unpaused"
        markerColor = QtGui.QColor("#c0c0ff") if paused else QtGui.QColor(0xd0, 0xff, 0xd0)
        self.textEdit.textEdit.setMarkerBackgroundColor(markerColor, self.textEdit.textEdit.currentLineMarkerNum)
        logger.info(message)
        self.writeToConsole(message, color='blue')
        self.actionPauseScript.setChecked(paused)
        self.scriptHandler.onPauseScript(paused)
        
    @QtCore.pyqtSlot()
    def onStopScript(self):
        """Stop script button is clicked"""
        self.actionPauseScript.setChecked(False)
        self.repeatButton.setChecked(False)
        self.scriptHandler.onStopScript()

    @QtCore.pyqtSlot()
    def onPauseScriptAndScan(self):
        """Pause script and scan button is clicked"""
        logger = logging.getLogger(__name__)
        message = "Script is paused"
        markerColor = QtGui.QColor("#c0c0ff")
        self.textEdit.textEdit.setMarkerBackgroundColor(markerColor, self.textEdit.textEdit.currentLineMarkerNum)
        logger.info(message)
        self.writeToConsole(message, color='blue')
        self.actionPauseScript.setChecked(True)
        self.scriptHandler.onPauseScriptAndScan()
        
    @QtCore.pyqtSlot()
    def onStopScriptAndScan(self):
        """Stop script and scan button is clicked"""
        self.actionPauseScript.setChecked(False)
        self.repeatButton.setChecked(False)
        self.scriptHandler.onStopScriptAndScan()
        
    @QtCore.pyqtSlot()
    def onFinished(self):
        """Runs when script thread finishes. re-enables script GUI."""
        logger = logging.getLogger(__name__)
        self.statusLabel.setText("Idle")
        message = "script {0} finished at {1}".format(self.script.fullname, str(datetime.now()))
        logger.info(message)
        self.writeToConsole(message, color='blue')
        self.textEdit.textEdit.markerDeleteAll()
        self.enableScriptChange(True)
        if self.revert and self.savedState:
            self.restoreSettingsState()
        self.scriptFinishedSignal.emit() #used for running scans from todo list

    @QtCore.pyqtSlot()
    def onRepeat(self):
        """Repeat button is clicked."""
        logger = logging.getLogger(__name__)
        repeat = self.repeatButton.isChecked()
        message = "Repeat is on" if repeat else "Repeat is off"
        logger.debug(message)
        self.writeToConsole(message)
        self.scriptHandler.onRepeat(repeat)

    @QtCore.pyqtSlot()
    def onRevert(self):
        """Revert button is clicked."""
        self.revert = self.revertButton.isChecked()
        logging.getLogger(__name__).debug("Revert is on" if self.revert else "Revert is off")

    @QtCore.pyqtSlot()
    def onSlow(self):
        """Slow button is clicked."""
        logger = logging.getLogger(__name__)
        slow = self.slowButton.isChecked()
        message = "Slow is on" if slow else "Slow is off"
        logger.debug(message)
        self.writeToConsole(message)
        self.scriptHandler.onSlow(slow)

    @QtCore.pyqtSlot()
    def onNew(self):
        """New button is clicked. Pop up dialog asking for new name, and create file."""
        logger = logging.getLogger(__name__)
        shortname, ok = QtWidgets.QInputDialog.getText(self, 'New script name', 'Enter new file name (optional path specified by localpath/filename): ')
        if ok:
            shortname = str(shortname)
            shortname = shortname.replace(' ', '_') #Replace spaces with underscores
            if shortname[-1] == '/':
                fullname = self.defaultDir.joinpath(shortname)
                ensurePath(fullname)
            else:
                shortname = shortname.split('.')[0] + '.py'#Take only what's before the '.'
                fullname = self.defaultDir.joinpath(shortname)
                ensurePath(fullname.parent)
                if not fullname.exists():
                    try:
                        with fullname.open('w') as f:
                            newFileText = '#' + shortname + ' created ' + str(datetime.now()) + '\n\n'
                            f.write(newFileText)
                    except Exception as e:
                        message = "Unable to create new file {0}: {1}".format(shortname, e)
                        logger.error(message)
                        return
                self.loadFile(fullname)
            self.populateTree(fullname)

    def enableScriptChange(self, enabled):
        """Enable or disable any changes to script editor"""
        color = QtGui.QColor("#ffe4e4") if enabled else QtGui.QColor('white')
        self.textEdit.textEdit.setCaretLineVisible(enabled)
        self.textEdit.textEdit.setCaretLineBackgroundColor(color)
        self.textEdit.setReadOnly(not enabled)
        self.filenameComboBox.setDisabled(not enabled)
        self.removeCurrent.setDisabled(not enabled)
        self.actionOpen.setEnabled(enabled)
        self.actionSave.setEnabled(enabled)
        self.actionReset.setEnabled(enabled)
        self.actionNew.setEnabled(enabled)
        self.actionStartScript.setEnabled(enabled)
        self.actionPauseScript.setEnabled(not enabled)
        self.actionStopScript.setEnabled(not enabled)
        self.actionPauseScriptAndScan.setEnabled(not enabled)
        self.actionStopScriptAndScan.setEnabled(not enabled)
        self.allowFileViewerLoad = enabled

    def onComboIndexChange(self, ind):
        """A name is typed into the filename combo box."""
        if ind == 0:
            return False
        if self.script.code != str(self.textEdit.toPlainText()):
            if not self.confirmLoad():
                self.filenameComboBox.setCurrentIndex(0)
                return False
        self.loadFile(self.filenameComboBox.itemData(ind))

    def onLoad(self):
        """The load button is clicked. Open file prompt for file."""
        fullname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Script', str(self.defaultDir), 'Python scripts (*.py *.pyw)')
        if fullname != "":
            fullname = Path(fullname)
            self.loadFile(fullname)

    def loadFile(self, fullname):
        """Load in a file."""
        logger = logging.getLogger(__name__)
        if fullname:
            self.script.fullname = fullname
            with fullname.open("r") as f:
                self.script.code = f.read()
            self.textEdit.setPlainText(self.script.code)
            if self.script.fullname not in self.recentFiles:
                self.filenameComboBox.addItem(self.script.shortname)
            self.recentFiles.add(fullname)
            with BlockSignals(self.filenameComboBox) as w:
                ind = w.findText(str(self.script.shortname)) #having issues with findData Path object comparison
                w.removeItem(ind) #these two lines just push the loaded filename to the top of the combobox
                w.insertItem(0, str(self.script.shortname))
                w.setItemData(0, self.script.fullname)
                w.setCurrentIndex(0)
            logger.info('{0} loaded'.format(self.script.fullname))
            self.initcode = copy.copy(self.script.code)

    def onReset(self):
        """Reset action. Reset file state saved on disk."""
        if self.script.fullname:
            self.loadFile(self.script.fullname)

    def onRemoveCurrent(self):
        """Remove current button is clicked. Remove file from combo box."""
        path = self.filenameComboBox.currentData()
        if path in self.recentFiles:
            self.recentFiles.remove(path)
        self.filenameComboBox.removeItem(0)
        self.loadFile(self.filenameComboBox.currentData())

    def onSave(self):
        """Save action. Save file to disk, and clear any highlighted errors."""
        logger = logging.getLogger(__name__)
        self.script.code = str(self.textEdit.toPlainText())
        self.textEdit.clearHighlightError()
        if self.script.code and self.script.fullname:
            with self.script.fullname.open('w') as f:
                f.write(self.script.code)
                logger.info('{0} saved'.format(self.script.fullname))
    
    def saveConfig(self):
        """Save configuration."""
        self.config[self.configname+'.recentFiles'] = self.recentFiles
        self.config[self.configname+'.script.fullname'] = self.script.fullname
        self.config[self.configname+'.revert'] = self.revert
        self.config[self.configname+'.slow'] = self.script.slow
        self.config[self.configname+'.repeat'] = self.script.repeat
        self.config[self.configname+'.isVisible'] = self.isVisible()
        self.config[self.configname+'.consoleMaximumLinesNew'] = self.consoleMaximumLines
        self.config[self.configname+'.guiState'] = self.saveState()

    def show(self):
        QtWidgets.QDialog.show(self)

    def onClose(self):
        self.saveConfig()
        self.hide()
        
    def onClearConsole(self):
        self.textEditConsole.clear()

    def onConsoleMaximumLinesChanged(self, maxlines):
        self.consoleMaximumLines = maxlines
        self.textEditConsole.document().setMaximumBlockCount(maxlines)

    def onEnableConsole(self, state):
        self.consoleEnable = state==QtCore.Qt.Checked

    def markLocation(self, lines):
        """mark a specified location""" 
        if lines:
            self.textEdit.textEdit.markerDeleteAll()
            for line in lines:
                self.textEdit.textEdit.markerAdd(line-1, self.textEdit.textEdit.ARROW_MARKER_NUM)
                self.textEdit.textEdit.markerAdd(line-1, self.textEdit.textEdit.currentLineMarkerNum)

    def markError(self, lines, message):
        """mark error at specified lines, and show message"""
        if lines != []:
            for line in lines:
                self.textEdit.highlightError(message, line)

    def writeToConsole(self, message, error=False, color=''):
        if self.consoleEnable:
            message = str(message)
            cursor = self.textEditConsole.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            textColor = ('red' if error else 'black') if color=='' else color
            self.textEditConsole.setUpdatesEnabled(False)
            if textColor == 'black':
                self.textEditConsole.insertPlainText(message+'\n')
            else:
                self.textEditConsole.insertHtml(str('<p><font color='+textColor+'>'+message+'</font><br></p>'))
            self.textEditConsole.setUpdatesEnabled(True)
            self.textEditConsole.setTextCursor(cursor)
            self.textEditConsole.ensureCursorVisible()

    def getDocs(self):
        """Assemble the script function documentation into a dictionary"""
        self.docDict = OrderedDict()
        for doc in scriptDocs:
            docsplit = doc.splitlines() 
            defLine = docsplit.pop(0)
            docsplit = [line.strip() for line in docsplit]
            docsplit = '\n'.join(docsplit)
            self.docDict[defLine] = docsplit

    def updateValidator(self):
        """Make the validator match the recentFiles list. Uses regExp \\b(f1|f2|f3...)\\b, where fn are filenames."""
        regExp = '\\b('
        for shortname in self.recentFiles:
            if shortname:
                regExp += shortname + '|'
        regExp = regExp[:-1] #drop last pipe symbol
        regExp += ')\\b'
        self.filenameComboBox.validator().setRegExp(QtCore.QRegExp(regExp))

    def saveSettingsState(self):
        """Save the state of the scan, evaluation, and analysis"""
        self.originalState = dict()
        self.originalState['scan'] = self.experimentUi.tabDict['Scan'].scanControlWidget.settingsName
        self.originalState['evaluation'] = self.experimentUi.tabDict['Scan'].evaluationControlWidget.settingsName
        self.originalState['analysis'] = self.experimentUi.tabDict['Scan'].analysisControlWidget.currentAnalysisName

    def restoreSettingsState(self):
        """Restore the settings to their original values"""
        for name, value in self.scriptHandler.globalVariablesRevertDict.items():
            self.experimentUi.globalVariablesUi.model.update([('Global', name, value)])
        self.experimentUi.tabDict['Scan'].scanControlWidget.loadSetting(self.originalState['scan'])
        self.experimentUi.tabDict['Scan'].evaluationControlWidget.loadSetting(self.originalState['evaluation'])
        self.experimentUi.tabDict['Scan'].analysisControlWidget.onLoadAnalysisConfiguration(self.originalState['analysis'])
