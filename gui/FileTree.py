# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os.path
from PyQt5 import QtWidgets, QtCore, uic
from pathlib import Path
from modules.PyqtUtility import BlockSignals
from collections import UserList

uipathOptions = os.path.join(os.path.dirname(__file__), '..', 'ui/UserFunctionsOptions.ui')
OptionsWidget, OptionsBase = uic.loadUiType(uipathOptions)

class OrderedList(UserList):
    def add(self, item):
        if item in self.data:
            self.remove(item)
        self.data.append(item)

    def replace(self, olditem, newitem):
        for i in range(self.__len__()):
            if self.data[i] == olditem:
                self.data[i] = newitem

class TreeItem(QtWidgets.QTreeWidgetItem):
    """a custom TreeWidgetItem that keeps track of full paths for loading files"""
    def __init__(self):
        super().__init__()
        self.path = ''
        self.isdir = True

def ensurePath(path):
    """check if path exists, if not add the path"""
    if not path.exists():
        path.mkdir(parents=True)

def checkTree(widget, pathobj, fileChanges=[]):
    """
    Construct the file tree
    :param widget: Initial object is root TreeWidget
    :param pathobj: Root directory that contains files that show up in the file tree
    :param expandAbovePathName: Specifies path of a new file so directories can be expanded to reveal the file
    :return:
    """
    childrange = range(widget.childCount())
    for childind in childrange:
        oldpath = Path(widget.child(childind).path)
        if pathobj != oldpath.parent:
            newpath = pathobj.joinpath(oldpath.name)
            fileChanges.append((oldpath, newpath))
            if oldpath.exists(): #check if file has already been moved
                oldpath.rename(newpath)
            widget.child(childind).path = str(newpath)
        if widget.child(childind).isdir:
            checkTree(widget.child(childind), Path(widget.child(childind).path), fileChanges)

def genFileTree(widget, pathobj, expandAbovePathName=None, onlyIncludeDirsWithPyFiles=False):
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
                child.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable)
                widget.addChild(child)
                if not expandAbovePathName is None and path == expandAbovePathName: # expand directories containing a new file
                    expandAboveChild(widget)
            elif path.is_dir() and not path.match('*/__*__*') and (not onlyIncludeDirsWithPyFiles or len(list(path.glob('**/*.py')))):
                child = TreeItem()
                child.setText(0, str(path.parts[-1]))
                child.path = str(path)
                child.setFlags(QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable)
                widget.addChild(child)
                genFileTree(child, path, expandAbovePathName)
    widget.sortChildren(0, 0)

def expandAboveChild(child):
    """expands all parent directories, for use with new file creation"""
    child.setExpanded(True)
    if not child.parent() is None:
        expandAboveChild(child.parent())

def onExpandOrCollapse(widget, expglobal=True, expand=True):
    """For expanding/collapsing file tree, expglobal=True will expand/collapse everything and False will
       collapse/expand only selected nodes. expand=True will expand, False will collapse"""
    if expglobal:
        root = widget.invisibleRootItem()
        recurseExpand(root, expand)
    else:
        selected = widget.selectedItems()
        if selected:
            for child in selected:
                child.setExpanded(expand)
                recurseExpand(child, expand)

def recurseExpand(node, expand=True):
    """recursively descends into tree structure below node to expand/collapse all subdirectories.
       expand=True will expand, False will collapse."""
    for childind in range(node.childCount()):
        node.child(childind).setExpanded(expand)
        recurseExpand(node.child(childind), expand)

class OptionsWindow(OptionsWidget, OptionsBase):
    OptionsChangedSignal = QtCore.pyqtSignal()
    def __init__(self, config, configname):
        super().__init__()
        self.config = config
        self.lineno = 15
        self.displayPath = False
        self.defaultExpand = False
        self.configname = configname

    def setupUi(self, parent):
        super(OptionsWindow, self).setupUi(parent)

        self.loadConfig()
        self.spinBox.setValue(self.lineno)
        self.radioButton_2.setChecked(self.displayPath)
        self.checkBox.setChecked(self.defaultExpand)
        self.applyButton.clicked.connect(self.saveAndClose)
        self.cancelButton.clicked.connect(self.cancelAndClose)
        self.radioButton.toggled.connect(lambda: self.btnstate(self.radioButton, True))

    def btnstate(self, b, buttonFlag):
        self.displayPath = b.isChecked() ^ buttonFlag

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

class FileTreeMixin:
    fileTreeWidget = None
    defaultDir = None
    configname = ''
    config = None
    filenameComboBox = None
    script = None
    displayFullPathNames = True

    def setupUi(self, parent):
        super().setupUi(parent)
        self.fileTreeWidget.setDragDropMode(self.fileTreeWidget.InternalMove)
        self.fileTreeWidget.setAcceptDrops(True)
        self.fileTreeWidget.setDragEnabled(True)
        self.fileTreeWidget.setDropIndicatorShown(True)
        self.fileTreeWidget.setSortingEnabled(True)
        self.fileTreeWidget.sortItems(0, QtCore.Qt.AscendingOrder)
        self.fileTreeWidget.setHeaderLabels(['User Function Files'])
        self.populateTree()


        self.expandTree = QtWidgets.QAction("Expand All", self)
        self.collapseTree = QtWidgets.QAction("Collapse All", self)
        self.expandChild = QtWidgets.QAction("Expand Selected", self)
        self.collapseChild = QtWidgets.QAction("Collapse Selected", self)
        self.expandTree.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, True, True))
        self.collapseTree.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, True, False))
        self.expandChild.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, False, True))
        self.collapseChild.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, False, False))
        self.fileTreeWidget.addAction(self.expandTree)
        self.fileTreeWidget.addAction(self.collapseTree)
        self.fileTreeWidget.addAction(self.expandChild)
        self.fileTreeWidget.addAction(self.collapseChild)

        self.fileTreeWidget.dropEvent = lambda x: self.onDrop(x)
        self.fileTreeWidget.itemDoubleClicked.connect(self.onDoubleClick)

        self.fileTreeWidget.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def populateTree(self, newfilepath=None):
        """constructs the file tree viewer"""
        genFileTree(self.fileTreeWidget.invisibleRootItem(), Path(self.defaultDir), newfilepath)

    def onDrop(self, event):
        changedFiles = []
        if event.source() == self.fileTreeWidget:
            QtWidgets.QTreeWidget.dropEvent(self.fileTreeWidget, event)
        checkTree(self.fileTreeWidget.invisibleRootItem(), Path(self.defaultDir), changedFiles)
        self.updatePathChanges(changedFiles)
        for oldName, newName in changedFiles:
            if oldName == self.script.fullname:
                self.script.fullname = newName

    def updatePathChanges(self, changedFiles):
        with BlockSignals(self.filenameComboBox) as w:
            combolen = range(w.count())
            for oldPath, newPath in changedFiles:
                self.recentFiles.replace(oldPath, newPath)
                for ind in combolen:
                    if w.itemData(ind) == oldPath:
                        w.setItemData(ind, newPath)
                        w.setItemText(ind, self.getName(newPath))

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
            self.loadFile(Path(args[0].path))

    def getName(self, fullpath):
        if self.displayFullPathNames:
            return fullpath.relative_to(self.defaultDir).as_posix()
        return fullpath.name

    def updateFileComboBoxNames(self, fullnames):
        with BlockSignals(self.filenameComboBox) as w:
            for ind in range(w.count()):
                w.setItemText(ind, self.getName(w.itemData(ind)))

