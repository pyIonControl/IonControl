# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


import os.path
import shutil
from functools import partial
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
from gui.UserFunctionsEditor import ensurePath, genFileTree

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/Scripting.ui')
ScriptingWidget, ScriptingBase = PyQt5.uic.loadUiType(uipath)

class ScriptingUi(ScriptingWidget, ScriptingBase):
    """Ui for the scripting interface."""
    def __init__(self, experimentUi):
        ScriptingWidget.__init__(self)
        ScriptingBase.__init__(self)
        self.config = experimentUi.config
        self.experimentUi = experimentUi
        self.recentFiles = dict() #dict of form {shortname: fullname}, where fullname has path and shortname doesn't
        self.script = Script() #encapsulates the script
        self.scriptHandler = ScriptHandler(self.script, experimentUi) #handles interface to the script
        self.revert = False
        self.initcode = ''
        self.defaultDir = getProject().configDir+'/Scripts'
        if not os.path.exists(self.defaultDir):
            defaultScriptsDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/Scripts')) #/IonControl/config/Scripts directory
            shutil.copytree(defaultScriptsDir, self.defaultDir) #Copy over all example scripts


    def setupUi(self, parent):
        super(ScriptingUi, self).setupUi(parent)
        self.configname = 'Scripting'
        
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

        #load file
        self.script.fullname = self.config.get( self.configname+'.script.fullname', '' )
        if self.script.fullname != '' and os.path.exists(self.script.fullname):
            with open(self.script.fullname, "r") as f:
                self.script.code = f.read()
        else:
            self.script.code = ''
        
        #setup filename combo box
        self.recentFiles = self.config.get( self.configname+'.recentFiles', dict() )
        self.recentFiles = {k: v for k,v in self.recentFiles.items() if os.path.exists(v)} #removes files from dict if file paths no longer exist
        self.filenameComboBox.addItems( [shortname for shortname, fullname in list(self.recentFiles.items()) if os.path.exists(fullname)] )
        self.filenameComboBox.currentIndexChanged[str].connect( self.onFilenameChange )
        self.removeCurrent.clicked.connect( self.onRemoveCurrent )
        self.filenameComboBox.setValidator( QtGui.QRegExpValidator() ) #verifies that files typed into combo box can be used
        self.updateValidator()

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

        self.loadFile(self.script.fullname)
        self.populateTree() #populates file explorer tree widget

        #Connect buttons for fileTreeWidget
        self.fileTreeWidget.itemDoubleClicked.connect(self.onDoubleClick)

        self.expandTree = QtWidgets.QAction("Expand All", self)
        self.collapseTree = QtWidgets.QAction("Collapse All", self)
        self.expandChild = QtWidgets.QAction("Expand Selected", self)
        self.collapseChild = QtWidgets.QAction("Collapse Selected", self)
        self.expandTree.triggered.connect(partial(self.onExpandOrCollapse, True, True))
        self.collapseTree.triggered.connect(partial(self.onExpandOrCollapse, True, False))
        self.expandChild.triggered.connect(partial(self.onExpandOrCollapse, False, True))
        self.collapseChild.triggered.connect(partial(self.onExpandOrCollapse, False, False))
        self.fileTreeWidget.addAction(self.expandTree)
        self.fileTreeWidget.addAction(self.collapseTree)
        self.fileTreeWidget.addAction(self.expandChild)
        self.fileTreeWidget.addAction(self.collapseChild)

        self.fileTreeWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.setWindowTitle(self.configname)
        self.setWindowIcon(QtGui.QIcon(":/other/icons/Terminal-icon.png"))
        self.statusLabel.setText("Idle")

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
        shortname, ok = QtWidgets.QInputDialog.getText(self, 'New script name', 'Please enter a new script name: ')
        if ok:
            shortname = str(shortname)
            shortname = shortname.replace(' ', '_') #Replace spaces with underscores
            shortname = shortname.split('.')[0] #Take only what's before the '.'
            ensurePath(self.defaultDir + '/' + shortname)
            shortname += '.py'
            fullname = self.defaultDir + '/' + shortname
            if not os.path.exists(fullname):
                try:
                    with open(fullname, 'w') as f:
                        newFileText = '#' + shortname + ' created ' + str(datetime.now()) + '\n'
                        f.write(newFileText)
                except Exception as e:
                    message = "Unable to create new file {0}: {1}".format(shortname, e)
                    logger.error(message)
                    self.onConsoleSignal(message, False)
                    return
            self.loadFile(fullname)
            self.populateTree()

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
    
    def onFilenameChange(self, shortname ):
        """A name is typed into the filename combo box."""
        shortname = str(shortname)
        logger = logging.getLogger(__name__)
        if not shortname:
            self.script.fullname=''
            self.textEdit.setPlainText('')
        elif shortname not in self.recentFiles:
            logger.info('Use "open" or "new" commands to access a file not in the drop down menu')
            self.loadFile(self.recentFiles[self.script.shortname])
        else:
            fullname = self.recentFiles[shortname]
            if os.path.isfile(fullname) and fullname != self.script.fullname:
                self.loadFile(fullname)
                if str(self.filenameComboBox.currentText())!=fullname:
                    with BlockSignals(self.filenameComboBox) as w:
                        w.setCurrentIndex( self.filenameComboBox.findText( shortname ))
    
    def onLoad(self):
        """The load button is clicked. Open file prompt for file."""
        fullname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Script', self.defaultDir, 'Python scripts (*.py *.pyw)')
        if fullname!="":
            self.loadFile(fullname)
           
    def loadFile(self, fullname):
        """Load in a file."""
        logger = logging.getLogger(__name__)
        if fullname:
            self.script.fullname = fullname
            with open(fullname, "r") as f:
                self.script.code = f.read()
            self.textEdit.setPlainText(self.script.code)
            if self.script.shortname not in self.recentFiles:
                self.recentFiles[self.script.shortname] = fullname
                self.filenameComboBox.addItem(self.script.shortname)
                self.updateValidator()
            with BlockSignals(self.filenameComboBox) as w:
                w.setCurrentIndex(w.findText(self.script.shortname))
            logger.info('{0} loaded'.format(self.script.fullname))
            self.initcode = copy.copy(self.script.code)

    def confirmLoad(self):
        """pop up window to confirm loss of unsaved changes when loading new file"""
        reply = QtWidgets.QMessageBox.question(self, 'Message',
            "Are you sure you want to discard changes?", QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            return True
        return False

    def onExpandOrCollapse(self, expglobal=True, expand=True):
        """For expanding/collapsing file tree, expglobal=True will expand/collapse everything and False will
           collapse/expand only selected nodes. expand=True will expand, False will collapse"""
        if expglobal:
            root = self.fileTreeWidget.invisibleRootItem()
            self.recurseExpand(root, expand)
        else:
            selected = self.fileTreeWidget.selectedItems()
            if selected:
                for child in selected:
                    child.setExpanded(expand)
                    self.recurseExpand(child, expand)

    def recurseExpand(self, node, expand=True):
        """recursively descends into tree structure below node to expand/collapse all subdirectories.
           expand=True will expand, False will collapse."""
        for childind in range(node.childCount()):
            node.child(childind).setExpanded(expand)
            self.recurseExpand(node.child(childind), expand)

    def onDoubleClick(self, *args):
        """open a file that is double clicked in file tree"""
        if self.script.code != str(self.textEdit.toPlainText()):
            if not self.confirmLoad():
               return False
        self.loadFile(args[0].path)

    def populateTree(self):
        """constructs the file tree viewer"""
        self.fileTreeWidget.setHeaderLabels(['Scripts'])
        localpath = getProject().configDir+'/Scripts/'
        self.fileTreeWidget.clear()
        genFileTree(self.fileTreeWidget.invisibleRootItem(), Path(localpath))

    def onReset(self):
        """Reset action. Reset file state saved on disk."""
        if self.script.fullname:
            self.loadFile(self.script.fullname)

    def onRemoveCurrent(self):
        """Remove current button is clicked. Remove file from combo box."""
        text = str(self.filenameComboBox.currentText())
        ind = self.filenameComboBox.findText(text)
        self.filenameComboBox.setCurrentIndex(ind)
        self.filenameComboBox.removeItem(ind)
        if text in self.recentFiles:
            self.recentFiles.pop(text)
        self.updateValidator()

    def onSave(self):
        """Save action. Save file to disk, and clear any highlighted errors."""
        logger = logging.getLogger(__name__)
        self.script.code = str(self.textEdit.toPlainText())
        self.textEdit.clearHighlightError()
        if self.script.code and self.script.fullname:
            with open(self.script.fullname, 'w') as f:
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
        self.config[self.configname+'.ScriptingUi.pos'] = self.pos()
        self.config[self.configname+'.ScriptingUi.size'] = self.size()
        self.config[self.configname+".splitterHorizontal"] = self.splitterHorizontal.saveState()
        self.config[self.configname+".splitterVertical"] = self.splitterVertical.saveState()
        self.config[self.configname+'.consoleMaximumLinesNew'] = self.consoleMaximumLines
        self.config[self.configname+'.consoleEnable'] = self.consoleEnable
       
    def show(self):
        pos = self.config.get(self.configname+'.ScriptingUi.pos')
        size = self.config.get(self.configname+'.ScriptingUi.size')
        splitterHorizontalState = self.config.get(self.configname+".splitterHorizontal")
        splitterVerticalState = self.config.get(self.configname+".splitterVertical")
        if pos:
            self.move(pos)
        if size:
            self.resize(size)
        if splitterHorizontalState:
            self.splitterHorizontal.restoreState(splitterHorizontalState)
        if splitterVerticalState:
            self.splitterVertical.restoreState(splitterVerticalState)
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
