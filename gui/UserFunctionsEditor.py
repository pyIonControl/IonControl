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
from expressionFunctions.ExprFuncDecorator import ExprFunUpdate, ExpressionFunctions
from inspect import isfunction
import importlib
import inspect
from pathlib import Path
from gui.ExpressionValue import ExpressionValue
import copy
from modules.Utility import unique
from gui.FileTree import ensurePath, onExpandOrCollapse, FileTreeMixin, OptionsWindow, OrderedList

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/UserFunctionsEditor.ui')
EditorWidget, EditorBase = PyQt5.uic.loadUiType(uipath)

class EvalTableModel(QtCore.QAbstractTableModel):
    def __init__(self, globalDict):
        super().__init__()
        self.globalDict = globalDict
        self.exprList = [ExpressionValue(None, self.globalDict)]
        self.dataLookup = {(QtCore.Qt.DisplayRole): lambda index: self.exprList[index.row()].string if index.column() == 0 else self.displayGain(index.row()),#(self.exprList[index.row()].value),
                           (QtCore.Qt.EditRole): lambda index: self.exprList[index.row()].string if index.column() == 0 else self.displayGain(self.exprList[index.row()].value)}
        self.headerDataLookup = ['Expression', 'Value']

    def displayGain(self, row):
        if isfunction(self.exprList[row].value.m):
            return str(self.exprList[row].value.m())
        return str(self.exprList[row].value)

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

    def displayGain2(self, val):
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

class UserCode:
    def __init__(self, dispfull=False, homeDir=Path()):
        self.code = ''
        self.fullname = Path()
        self.dispfull = dispfull
        self.homeDir = homeDir

    @QtCore.pyqtProperty(str)
    def shortname(self):
        if self.dispfull:
            return self.localpathname
        return self.filename

    @QtCore.pyqtProperty(str)
    def filename(self):
        return str(self.fullname.name)

    @QtCore.pyqtProperty(str)
    def localpathname(self):
        return str(self.fullname.relative_to(self.homeDir).as_posix())

class DocTreeItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, widget, text, path, line):
        super().__init__(widget, [text])
        self.path = Path(path)
        self.line = line

class UserFunctionsEditor(FileTreeMixin, EditorWidget, EditorBase):
    """Ui for the user function interface."""
    def __init__(self, experimentUi, globalDict):
        super().__init__()
        self.config = experimentUi.config
        self.experimentUi = experimentUi
        self.globalDict = globalDict
        self.docDict = dict()
        self.configDirFolder = 'UserFunctions'
        self.configname = 'UserFunctionsEditor'
        self.defaultDir = Path(getProject().configDir + '/' + self.configDirFolder)
        self.displayFullPathNames = True
        self.script = UserCode(self.displayFullPathNames, self.defaultDir) #carries around code body and filepath info
        if not self.defaultDir.exists():
            defaultScriptsDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config/' + self.configDirFolder)) #/IonControl/config/UserFunctions directory
            shutil.copytree(defaultScriptsDir, self.defaultDir) #Copy over all example scripts

    def setupUi(self, parent):
        super(UserFunctionsEditor, self).setupUi(parent)
        self.tableModel = EvalTableModel(self.globalDict)
        self.tableView.setModel(self.tableModel)
        self.tableView.setSortingEnabled(True)   # triggers sorting
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(1, self.delegate)
        self.addEvalRow.clicked.connect(self.onAddRow)
        self.removeEvalRow.clicked.connect(self.onRemoveRow)

        #setup documentation list
        self.getDocs()
        self.docTreeWidget.setHeaderLabels(['Available Script Functions'])
        #self.docTreeWidget.setSortIndicator(0, 0)

        #initialize default options
        self.optionsWindow = OptionsWindow(self.config, 'UserFunctionsEditorOptions')
        self.optionsWindow.setupUi(self.optionsWindow)
        self.actionOptions.triggered.connect(self.onOpenOptions)
        self.optionsWindow.OptionsChangedSignal.connect(self.updateOptions)
        self.updateOptions()
        if self.optionsWindow.defaultExpand:
            onExpandOrCollapse(self.fileTreeWidget, True, True)

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

        #load recent files, also checks if data was saved correctly and if files still exist
        savedfiles = self.config.get( self.configname+'.recentFiles', OrderedList())
        self.initRecentFiles(savedfiles)
        self.initComboBox()

        self.tableModel.exprList = self.config.get(self.configname + '.evalstr', [ExpressionValue(None, self.globalDict)])
        if not isinstance(self.tableModel.exprList, list) or not isinstance(self.tableModel.exprList[0], ExpressionValue):
            self.tableModel.exprList = [ExpressionValue(None, self.globalDict)]
        self.tableModel.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.tableModel.layoutChanged.emit()
        self.tableModel.connectAllExprVals()

        #load last opened file
        self.script.fullname = self.config.get( self.configname+'.script.fullname', '' )
        self.initLoad()

        self.openFile = QtWidgets.QAction("Open Source Code", self)
        self.openFile.triggered.connect(self.gotoCode)
        self.docTreeWidget.addAction(self.openFile)
        self.docTreeWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        #connect buttons
        self.actionOpen.triggered.connect(self.onLoad)
        self.actionSave.triggered.connect(self.onSave)
        self.actionNew.triggered.connect(self.onNew)

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
        self.script.dispfull = self.optionsWindow.displayPath
        self.defaultExpandAll = self.optionsWindow.defaultExpand
        self.updateFileComboBoxNames(self.displayFullPathNames)

    def getDocs(self):
        """Assemble the script function documentation into a dictionary"""
        currentDocs = {fname: [func, inspect.getdoc(func), func.__code__.co_filename, func.__code__.co_firstlineno] for fname, func in ExpressionFunctions.items()}
        if self.docDict != currentDocs:
            self.docDict = currentDocs
            self.docTreeWidget.clear()
            for funcDef, funcAttrs in list(self.docDict.items()):
                funcDesc = funcAttrs[1]
                funcDisp = funcDef+inspect.formatargspec(*inspect.getfullargspec(funcAttrs[0]))
                itemDef = DocTreeItem(self.docTreeWidget, funcDisp, *funcAttrs[2::])
                self.docTreeWidget.addTopLevelItem(itemDef)
                if funcDesc:
                    DocTreeItem(itemDef, funcDesc+'\n', *funcAttrs[2::])
                else:
                    tempDesc = '{0}({1})'.format(funcDef,', '.join(inspect.getargspec(ExpressionFunctions[funcDef]).args))
                    DocTreeItem(itemDef, tempDesc, *funcAttrs[2::])
                self.docTreeWidget.setWordWrap(True)
        self.docTreeWidget.invisibleRootItem().sortChildren(0, 0)

    def markLocation(self, line):
        """mark a specified location"""
        self.textEdit.textEdit.markerDeleteAll()
        self.textEdit.textEdit.markerAdd(line, self.textEdit.textEdit.ARROW_MARKER_NUM)
        self.textEdit.textEdit.setScrollPosition(line-2)
        self.textEdit.textEdit.setCursorPosition(line, 0)

    def gotoCode(self, *args):
        docitem = self.docTreeWidget.currentItem()
        path = docitem.path
        lineno = docitem.line
        if self.defaultDir in path.parents:
            if self.script.code != str(self.textEdit.toPlainText()):
                if not self.confirmLoad():
                    return False
            self.loadFile(path)
            self.markLocation(lineno)
        else:
            self.statusLabel.setText("Can only load files in UserFunctions directory!")
            self.statusLabel.setStyleSheet('color: red')

    @QtCore.pyqtSlot()
    def onNew(self):
        """New button is clicked. Pop up dialog asking for new name, and create file."""
        logger = logging.getLogger(__name__)
        shortname, ok = QtWidgets.QInputDialog.getText(self, 'New script name', 'Enter new file name (optional path specified by localpath/filename): ')
        if ok:
            shortname = str(shortname)
            shortname = shortname.replace(' ', '_') #Replace spaces with underscores
            shortname = shortname.split('.')[0] + '.py'#Take only what's before the '.'
            fullname = self.defaultDir.joinpath(shortname)
            ensurePath(fullname.parent)
            if not fullname.exists():
                try:
                    with fullname.open('w') as f:
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
        fullname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Script', self.defaultDir, 'Python scripts (*.py *.pyw)')
        if fullname!="":
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
            self.statusLabel.setText("")
            self.initcode = copy.copy(self.script.code)

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
            self.initcode = copy.copy(self.script.code)
        try:
            importlib.machinery.SourceFileLoader("UserFunctions", str(self.script.fullname)).load_module()
            self.tableModel.updateData()
            ExprFunUpdate.dataChanged.emit('__exprfunc__')
            self.statusLabel.setText("Successfully updated {0}".format(self.script.fullname.name))
            self.statusLabel.setStyleSheet('color: green')
        except SyntaxError as e:
            self.statusLabel.setText("Failed to execute {0}: {1}".format(self.script.fullname.name, e))
            self.statusLabel.setStyleSheet('color: red')
        self.getDocs()

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

    def onClose(self):
        self.saveConfig()
        self.hide()

