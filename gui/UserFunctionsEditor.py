# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os.path
import shutil
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic
from PyQt5.Qsci import QsciScintilla
import logging
from datetime import datetime
from ProjectConfig.Project import getProject
from modules.PyqtUtility import BlockSignals
from uiModules.KeyboardFilter import KeyListFilter
from pulseProgram.PulseProgramSourceEdit import PulseProgramSourceEdit
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from expressionFunctions.ExprFuncDecorator import ExprFunUpdate
from inspect import isfunction
import importlib
from pathlib import Path
from gui.ExpressionValue import ExpressionValue
import copy
from modules.Utility import unique
from collections import OrderedDict

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/UserFunctionsEditor.ui')
uipathOptions = os.path.join(os.path.dirname(__file__), '..', 'ui/UserFunctionsOptions.ui')
EditorWidget, EditorBase = PyQt5.uic.loadUiType(uipath)
OptionsWidget, OptionsBase = PyQt5.uic.loadUiType(uipathOptions)

class OptionsWindow(OptionsWidget, OptionsBase):
    OptionsChangedSignal = QtCore.pyqtSignal()
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.lineno = 15
        self.displayPath = False
        self.defaultExpand = False

    def setupUi(self, parent):
        super(OptionsWindow, self).setupUi(parent)
        self.configname = 'UserFunctionsEditorOptions'

        self.loadConfig()
        self.spinBox.setValue(self.lineno)
        self.radioButton.setChecked(not self.displayPath)
        self.checkBox.setChecked(self.defaultExpand)
        self.applyButton.clicked.connect(self.saveAndClose)
        self.cancelButton.clicked.connect(self.cancelAndClose)
        self.radioButton.toggled.connect(lambda: self.btnstate(self.radioButton, True))
        #self.radioButton_2.toggled.connect(lambda: self.btnstate(self.radioButton_2, False))

    def btnstate(self, b, buttonFlag):
        self.displayPath = b.isChecked() ^ buttonFlag
        print(self.displayPath)

    def loadConfig(self):
        """Save configuration."""
        self.lineno = self.config.get(self.configname+'.lineno', 15)
        self.displayPath = self.config.get(self.configname+'.displayPath', False)
        self.defaultExpand = self.config.get(self.configname+'.defaultExpand', False)

    def saveConfig(self):
        """Save configuration."""
        self.config[self.configname+'.lineno'] = self.lineno
        self.config[self.configname+'.displayPath'] = self.displayPath
        self.config[self.configname+'.defaultExpand'] = self.defaultExpand

    def saveAndClose(self):
        self.lineno = self.spinBox.value()
        self.defaultExpand = self.checkBox.isChecked()
        self.saveConfig()
        self.OptionsChangedSignal.emit()
        self.hide()

    def cancelAndClose(self):
        self.loadConfig()
        self.spinBox.setValue(self.lineno)
        self.radioButton.setChecked(not self.displayPath)
        self.checkBox.setChecked(self.defaultExpand)
        self.hide()

def ensurePath(path):
    """check if path exists, if not add the path"""
    pathlist = path.replace('\\','/').split('/')
    newpath = ''
    for dir in pathlist[:-1]:
        newpath += dir + '/'
        if not os.path.exists(newpath):
            os.mkdir(newpath)

class TreeItem(QtWidgets.QTreeWidgetItem):
    """a custom TreeWidgetItem that keeps track of full paths for loading files"""
    def __init__(self):
        super().__init__()
        self.path = ''
        self.isdir = True

def genFileTree(widget, pathobj, expandAbovePathName=None):
    """
    Construct the file tree
    :param widget: Initial object is root TreeWidget
    :param pathobj: Root directory that contains files that show up in the file tree
    :param expandAbovePathName: Specifies path of a new file so directories can be expanded to reveal the file
    :return:
    """
    childrange = range(widget.childCount())
    for path in pathobj.iterdir():
        if str(path) in [widget.child(p).path for p in childrange]: #check if tree item already exists
            for childind in childrange:
                if widget.child(childind).path == str(path):
                    if path.is_dir():
                        genFileTree(widget.child(childind), path, expandAbovePathName)
        else: #otherwise make a new tree item.
            if path.parts[-1].split('.')[-1] == 'py':
                child = TreeItem()
                child.setText(0, str(path.parts[-1]))
                child.path = str(path)
                child.isdir = False
                widget.addChild(child)
                if not expandAbovePathName is None and path == Path(expandAbovePathName): # expand directories containing a new file
                    expandAboveChild(widget)
            elif path.is_dir() and len(list(path.glob('**/*.py'))):
                child = TreeItem()
                child.setText(0, str(path.parts[-1]))
                child.path = str(path)
                widget.addChild(child)
                genFileTree(child, path, expandAbovePathName)
    widget.sortChildren(0, 0)

def expandAboveChild(child):
    """expands all parent directories, for use with new file creation"""
    child.setExpanded(True)
    if not child.parent() is None:
        expandAboveChild(child.parent())

class EvalTableModel(QtCore.QAbstractTableModel):
    def __init__(self, globalDict):
        super().__init__()
        self.globalDict = globalDict
        self.exprList = [ExpressionValue(None, self.globalDict)]
        self.dataLookup = {(QtCore.Qt.DisplayRole): lambda index: self.exprList[index.row()].string if index.column() == 0 else self.displayGain(self.exprList[index.row()].value),
                           (QtCore.Qt.EditRole): lambda index: self.exprList[index.row()].string if index.column() == 0 else self.displayGain(self.exprList[index.row()].value)}
        self.headerDataLookup = ['Expression', 'Value']

    def rowCount(self, *args):
        return len(self.exprList)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def insertRow(self, position=0, index=QtCore.QModelIndex()):
        self.exprList.append(ExpressionValue(None, self.globalDict))
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        exprlen = len(self.exprList)
        self.exprList[exprlen - 1].valueChanged.connect(partial(self.valueChanged, exprlen - 1), QtCore.Qt.UniqueConnection)
        return range(exprlen-1, exprlen)

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        if len(self.exprList):
            del(self.exprList[position:(position + rows)])
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        return range(position, position+rows)

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get(role, lambda index: None)(index)

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            self.exprList[index.row()].string = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)

    def updateData(self, index=QtCore.QModelIndex):
        index = self.createIndex(0, 1)
        self.dataChanged.emit(index, index)

    def connectAllExprVals(self):
        """connect all ExpressionValue objects to rest of GUI for updating values when global dependencies change"""
        for i in range(len(self.exprList)):
            self.exprList[i]._globalDict = self.globalDict
            self.exprList[i].valueChanged.connect(partial(self.valueChanged, i), QtCore.Qt.UniqueConnection)
            self.exprList[i].string = copy.copy(self.exprList[i].string)

    def valueChanged(self, ind):
        index = self.createIndex(ind, 1)
        self.dataChanged.emit(index, index)

    def flags(self, index):
        if index.column() == 0:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        if index.column() == 1:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal):
                return self.headerDataLookup[section]
        return None

    def displayGain(self, val):
        """check if the object returned is a function for proper display"""
        if isfunction(val):
            return str(val())
        return str(val)

    def copy_rows(self, rows, position):
        """creates a copy of elements in table specified by indices in the rows variable and inserts at position+1"""
        for i in reversed(rows):
            self.exprList.insert(position + 1, copy.deepcopy(self.exprList[i]))
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        self.connectAllExprVals()
        return True

    def moveRow(self, rows, delta):
        """manually resort rows (for use with pgup/pgdn). rows specifies selected rows, delta specifies up/down movement"""
        if len(rows)>0 and (rows[0]>0 or delta>0) and (len(self.exprList) > max(rows)+1 or delta < 0):
            for row in rows:
                self.exprList[row], self.exprList[row + delta] = self.exprList[row + delta], self.exprList[row]
            self.connectAllExprVals()
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            return True
        return False

def fileNameDictEntry(key, splitDir):
    shortname = os.path.basename(self.fullname)
    localpathname = key.split(splitDir)
    return shortname, localpathname

class LastUpdatedOrderedDict(OrderedDict):
    'Store items in the order the keys were last added'

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
            #self.move_to_end(key)
        #else:
        OrderedDict.__setitem__(self, key, value)

class UserCode:
    def __init__(self, dispfull=False, splitDir=''):
        self.code = ''
        self.fullname = ''
        self.dispfull = dispfull#False
        self.splitDir = splitDir#''

    @QtCore.pyqtProperty(str)
    def shortname(self):
        if self.dispfull:
            return self.fullname.split(self.splitDir)[-1]
        return os.path.basename(self.fullname)

    @QtCore.pyqtProperty(str)
    def localpathname(self):
        return self.fullname.split(self.splitDir)[-1]

class UserFunctionsEditor(EditorWidget, EditorBase):
    """Ui for the user function interface."""
    def __init__(self, experimentUi, globalDict):
        super().__init__()
        self.config = experimentUi.config
        self.experimentUi = experimentUi
        self.globalDict = globalDict
        self.recentFiles = dict() #dict of form {shortname: fullname}, where fullname has path and shortname doesn't
        #self.script = UserCode() #carries around code body and filepath info
        self.configDirFolder = 'UserFunctions'
        self.defaultDir = getProject().configDir+'/' + self.configDirFolder
        self.displayFullPathNames = True#False
        self.script = UserCode(self.displayFullPathNames, self.configDirFolder) #carries around code body and filepath info
        if not os.path.exists(self.defaultDir):
            defaultScriptsDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/' + self.configDirFolder)) #/IonControl/config/UserFunctions directory
            shutil.copytree(defaultScriptsDir, self.defaultDir) #Copy over all example scripts
        self.displayFullPathNames = False
        self.defaultExpandAll = False

    def setupUi(self, parent):
        super(UserFunctionsEditor, self).setupUi(parent)
        self.configname = 'UserFunctionsEditor'
        self.fileTreeWidget.setHeaderLabels(['User Function Files'])
        self.populateTree()

        self.tableModel = EvalTableModel(self.globalDict)
        self.tableView.setModel( self.tableModel )
        self.tableView.setSortingEnabled(True)   # triggers sorting
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(1, self.delegate)
        self.addEvalRow.clicked.connect(self.onAddRow)
        self.removeEvalRow.clicked.connect(self.onRemoveRow)

        self.optionsWindow = OptionsWindow(self.config)
        self.optionsWindow.setupUi(self.optionsWindow)
        self.actionOptions.triggered.connect(self.onOpenOptions)
        self.optionsWindow.OptionsChangedSignal.connect(self.updateOptions)
        self.updateOptions()

        if self.optionsWindow.defaultExpand:
            self.onExpandOrCollapse(True, True)

        #hot keys for copy/past and sorting
        self.filter = KeyListFilter( [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown] )
        self.filter.keyPressed.connect( self.onReorder )
        self.tableView.installEventFilter(self.filter)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self, self.copy_to_clipboard)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Paste), self, self.paste_from_clipboard)

        #setup editor
        self.textEdit = PulseProgramSourceEdit()
        self.textEdit.setupUi(self.textEdit, extraKeywords1=[], extraKeywords2=[])
        self.textEdit.textEdit.currentLineMarkerNum = 9
        self.textEdit.textEdit.markerDefine(QsciScintilla.Background, self.textEdit.textEdit.currentLineMarkerNum) #This is a marker that highlights the background
        self.textEdit.textEdit.setMarkerBackgroundColor(QtGui.QColor(0xd0, 0xff, 0xd0), self.textEdit.textEdit.currentLineMarkerNum)
        self.textEdit.setPlainText(self.script.code)
        self.splitterVertical.insertWidget(0, self.textEdit)

        #load file
        self.script.fullname = self.config.get( self.configname+'.script.fullname', '' )
        self.tableModel.exprList = self.config.get(self.configname + '.evalstr', [ExpressionValue(None, self.globalDict)])
        if not isinstance(self.tableModel.exprList, list) or not isinstance(self.tableModel.exprList[0], ExpressionValue):
            self.tableModel.exprList = [ExpressionValue(None, self.globalDict)]
        self.tableModel.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.tableModel.layoutChanged.emit()
        self.tableModel.connectAllExprVals()
        if self.script.fullname != '' and os.path.exists(self.script.fullname):
            with open(self.script.fullname, "r") as f:
                self.script.code = f.read()
        else:
            self.script.code = ''

        #setup filename combo box
        self.recentFiles = self.config.get( self.configname+'.recentFiles', dict() )
        #if len(self.recentFiles):
            #if not all(isinstance(self.recentFiles.items(), dict)):
                #self.recentFiles =
        if not isinstance(self.recentFiles, LastUpdatedOrderedDict):
            #tempdict = copy.deepcopy(self.recentFiles)
            tempdict = {k: v for k,v in self.recentFiles.items() if os.path.exists(v)}
            self.recentFiles = LastUpdatedOrderedDict()
            for k, v in tempdict.items():
                self.recentFiles[k] = v
            #tempdict = {k: v for k,v in self.recentFiles.items() if os.path.exists(v)}
        else:
            self.recentFiles = {k: v for k,v in self.recentFiles.items() if os.path.exists(v)} #removes files from dict if file paths no longer exist
        self.filenameComboBox.setInsertPolicy(1)
        #self.filenameComboBox.setMaxCount(10)
        #self.filenameComboBox.addItems( [shortname for shortname, fullname in list(self.recentFiles.items()) if os.path.exists(fullname)] )
        for shortname, fullname in self.recentFiles.items():
            self.filenameComboBox.addItem(shortname)
            self.filenameComboBox.setItemData(0, fullname)
        self.filenameComboBox.currentIndexChanged[str].connect( self.onFilenameChange )
        self.removeCurrent.clicked.connect( self.onRemoveCurrent )
        self.filenameComboBox.setValidator( QtGui.QRegExpValidator() ) #verifies that files typed into combo box can be used
        self.updateValidator()

        #self.recentFilesDual = {fullname: {shortname: sname, midname: mname}}
        #connect buttons
        self.actionOpen.triggered.connect(self.onLoad)
        self.actionSave.triggered.connect(self.onSave)
        self.actionNew.triggered.connect(self.onNew)

        self.fileTreeWidget.itemDoubleClicked.connect(self.onDoubleClick)
        self.loadFile(self.script.fullname)

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
        self.setWindowIcon(QtGui.QIcon( ":/latex/icons/FuncIcon2.png"))
        self.statusLabel.setText("")
        self.tableModel.updateData()

    def onOpenOptions(self):
        self.optionsWindow.show()
        self.optionsWindow.setWindowState(QtCore.Qt.WindowActive)
        self.optionsWindow.raise_()

    def updateOptions(self):
        self.filenameComboBox.setMaxCount(self.optionsWindow.lineno)
        self.displayFullPathNames = self.optionsWindow.displayPath
        self.defaultExpandAll = self.optionsWindow.defaultExpand
        self.updateFileComboBoxNames(self.displayFullPathNames)
        #print("updated, ", self.optionsWindow.lineno)


    def updateFileComboBoxNames(self, fullnames):
        #for k, v in self.recentFiles.items(): #infinite loop
            #del self.recentFiles[k]
            #if self.displayFullPathNames:
                #k2 = v.split(self.configDirFolder)[-1]
            #else:
                #k2 = os.path.basename(v)
            #self.recentFiles[k2] = v
        with BlockSignals(self.filenameComboBox) as w:
            for ind in range(w.count()):
                #pass
                #ind = w.findText(self.script.shortname)
                if self.displayFullPathNames:
                    w.setItemText(ind, w.itemData(ind).split(self.configDirFolder)[-1])
                else:
                    w.setItemText(ind, os.path.basename(w.itemData(ind)))

                #w.removeItem(ind) #these two lines just push the loaded filename to the top of the combobox
                #w.insertItem(ind, self.script.shortname)
                #w.setCurrentIndex(0)

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

    def confirmLoad(self):
        """pop up window to confirm loss of unsaved changes when loading new file"""
        reply = QtWidgets.QMessageBox.question(self, 'Message',
            "Are you sure you want to discard changes?", QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            return True
        return False

    def onDoubleClick(self, *args):
        """open a file that is double clicked in file tree"""
        if self.script.code != str(self.textEdit.toPlainText()):
            if not self.confirmLoad():
               return False
        if not args[0].isdir:
            self.loadFile(args[0].path)

    def populateTree(self, newfilepath=None):
        """constructs the file tree viewer"""
        genFileTree(self.fileTreeWidget.invisibleRootItem(), Path(self.defaultDir), newfilepath)

    @QtCore.pyqtSlot()
    def onNew(self):
        """New button is clicked. Pop up dialog asking for new name, and create file."""
        logger = logging.getLogger(__name__)
        shortname, ok = QtWidgets.QInputDialog.getText(self, 'New script name', 'Enter new file name (optional path specified by localpath/filename): ')
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
                        newFileText = '#' + shortname + ' created ' + str(datetime.now()) + '\n\n'
                        f.write(newFileText)
                        defaultImportText = 'from expressionFunctions.ExprFuncDecorator import userfunc\n\n'
                        f.write(defaultImportText)
                except Exception as e:
                    message = "Unable to create new file {0}: {1}".format(shortname, e)
                    logger.error(message)
                    return
            self.loadFile(fullname)
            self.populateTree(fullname)

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
                #self.recentFiles[self.script.shortname] = fullname
                self.filenameComboBox.addItem(self.script.shortname)
                self.updateValidator()
            self.recentFiles[self.script.shortname] = fullname
            with BlockSignals(self.filenameComboBox) as w:
                ind = w.findText(self.script.shortname)
                w.removeItem(ind) #these two lines just push the loaded filename to the top of the combobox
                w.insertItem(0, self.script.shortname)
                w.setItemData(0, self.script.fullname)
                w.setCurrentIndex(0)
            logger.info('{0} loaded'.format(self.script.fullname))
            self.initcode = copy.copy(self.script.code)

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
            self.initcode = copy.copy(self.script.code)
        try:
            importlib.machinery.SourceFileLoader("UserFunctions", self.script.fullname).load_module()
            self.tableModel.updateData()
            ExprFunUpdate.dataChanged.emit('__exprfunc__')
            self.statusLabel.setText("Successfully updated {0}".format(self.script.fullname.split('\\')[-1]))
            self.statusLabel.setStyleSheet('color: green')
        except SyntaxError as e:
            self.statusLabel.setText("Failed to execute {0}: {1}".format(self.script.fullname.split('\\')[-1], e))
            self.statusLabel.setStyleSheet('color: red')

    def saveConfig(self):
        """Save configuration."""
        self.config[self.configname+'.recentFiles'] = self.recentFiles
        self.config[self.configname+'.script.fullname'] = self.script.fullname
        self.config[self.configname+'.isVisible'] = self.isVisible()
        self.config[self.configname+'.ScriptingUi.pos'] = self.pos()
        self.config[self.configname+'.ScriptingUi.size'] = self.size()
        self.config[self.configname+".splitterHorizontal"] = self.splitterHorizontal.saveState()
        self.config[self.configname+".splitterVertical"] = self.splitterVertical.saveState()
        self.config[self.configname+".evalstr"] = self.tableModel.exprList

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

    def onAddRow(self):
        """add a row in expression tests"""
        self.tableModel.insertRow()

    def onRemoveRow(self):
        """remove row(s) in expression tests"""
        zeroColSelInd = self.tableView.selectedIndexes()
        if len(zeroColSelInd):
            initRow = zeroColSelInd[0].row()
            finRow = zeroColSelInd[-1].row()-initRow+1
            self.tableModel.removeRows(initRow, finRow)
        else:
            self.tableModel.removeRows(len(self.tableModel.exprList) - 1)

    def copy_to_clipboard(self):
        """ Copy the list of selected rows to the clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        rows = sorted(unique([i.row() for i in self.tableView.selectedIndexes()]))
        clip.setText(str(rows))

    def paste_from_clipboard(self):
        """ Append the string of rows from the clipboard to the end of the TODO list. """
        clip = QtWidgets.QApplication.clipboard()
        row_string = str(clip.text())
        try:
            row_list = list(map(int, row_string.strip('[]').split(',')))
        except ValueError:
            raise ValueError("Invalid data on clipboard. Cannot paste into eval list")
        zeroColSelInd = self.tableView.selectedIndexes()
        initRow = zeroColSelInd[-1].row()
        self.tableModel.copy_rows(row_list, initRow)

    def onReorder(self, key):
        """reorder expression tests with pgup and pgdn"""
        if key in [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown]:
            indexes = self.tableView.selectedIndexes()
            up = key == QtCore.Qt.Key_PageUp
            delta = -1 if up else 1
            rows = sorted(unique([i.row() for i in indexes]), reverse=not up)
            if self.tableModel.moveRow( rows, delta):
                selectionModel = self.tableView.selectionModel()
                selectionModel.clearSelection()
                for index in indexes:
                    selectionModel.select(self.tableModel.createIndex(index.row()+delta, index.column()),
                                          QtCore.QItemSelectionModel.Select)

    def updateValidator(self):
        """Make the validator match the recentFiles list. Uses regExp \\b(f1|f2|f3...)\\b, where fn are filenames."""
        regExp = '\\b('
        for shortname in self.recentFiles:
            if shortname:
                regExp += shortname + '|'
        regExp = regExp[:-1] #drop last pipe symbol
        regExp += ')\\b'
        self.filenameComboBox.validator().setRegExp(QtCore.QRegExp(regExp))

    def onClose(self):
        self.saveConfig()
        self.hide()
