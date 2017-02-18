# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os.path
from PyQt5 import QtWidgets, QtCore, uic, QtGui
from pathlib import Path
from modules.PyqtUtility import BlockSignals
from collections import UserList

uipathOptions = os.path.join(os.path.dirname(__file__), '..', 'ui/UserFunctionsOptions.ui')
OptionsWidget, OptionsBase = uic.loadUiType(uipathOptions)

class OrderedList(UserList):
    """add updates list by pushing duplicate items to the end.
       replace is used to maintain order while updating filenames in the event they change."""
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
    def __init__(self, *args):
        super().__init__(args)
        self.path = ''
        self.isdir = True

def ensurePath(path):
    """check if path exists, if not add the path"""
    if not path.exists():
        path.mkdir(parents=True)

def checkTree(widget, pathobj, fileChanges=[]):
    """
    Walks file tree widget and determines if any file paths need to be updated
    Args:
        widget: Initial input is top node of file tree widget
        pathobj: Root directory of file tree
        fileChanges: input should be a variable name containing a blank list, file changes overwrite the contents of the input

    Returns: nothing, overwriting input doesn't seem to cause any issues but might need to be redone

    """
    childrange = range(widget.childCount())
    for childind in childrange:
        oldpath = Path(widget.child(childind).path)
        if pathobj != oldpath.parent:
            newpath = sequenceFile(pathobj.joinpath(oldpath.name))
            fileChanges.append((oldpath, newpath))
            if oldpath.exists(): #check if file has already been moved
                oldpath.rename(newpath)
            widget.child(childind).path = str(newpath)
            widget.child(childind).setText(0, newpath.name)
        if widget.child(childind).isdir:
            checkTree(widget.child(childind), Path(widget.child(childind).path), fileChanges)

def genFileTree(widget, pathobj, expandAbovePathName=None, onlyIncludeDirsWithPyFiles=False, fullFileList=None, rootdir=None):
    """
    Construct the file tree
    :param widget: Initial object is root TreeWidget
    :param pathobj: Root directory that contains files that show up in the file tree
    :param expandAbovePathName: Specifies path of a new file so directories can be expanded to reveal the file
    :return:
    """
    if fullFileList is None:
        fullFileList = dict()
    if rootdir is None:
        rootdir = pathobj
    for path in pathobj.iterdir():
        childpaths = [widget.child(p).path for p in range(widget.childCount())]
        if str(path) in childpaths:
            if path.is_dir():
                childind = childpaths.index(str(path))
                genFileTree(widget.child(childind), path, expandAbovePathName, fullFileList=fullFileList, rootdir=rootdir)
        else: #otherwise make a new tree item.
            if path.suffix == '.py':
                child = TreeItem()
                child.setText(0, path.name)
                child.path = str(path)
                fullFileList[str(path.relative_to(rootdir))] = path
                child.isdir = False
                child.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable)
                child.setIcon(0,QtGui.QIcon( ":/openicon/icons/edit-shred.png"))
                widget.addChild(child)
                if not expandAbovePathName is None and path == expandAbovePathName: # expand directories containing a new file
                    expandAboveChild(widget)
            elif path.is_dir() and not path.match('*/__*__*') and (not onlyIncludeDirsWithPyFiles or len(list(path.glob('**/*.py')))):
                child = TreeItem()
                child.setText(0, path.name)
                child.path = str(path)
                child.setFlags(QtCore.Qt.ItemIsDropEnabled | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable)
                child.setIcon(0,QtGui.QIcon( ":/openicon/icons/document-open-5.png"))
                widget.addChild(child)
                genFileTree(child, path, expandAbovePathName, fullFileList=fullFileList, rootdir=rootdir)
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

def sequenceFile(filename:Path):
    if filename.exists():
        import re
        n = re.compile('\(\d+\)')
        m = n.search(filename.name)
        if m:
            newname = re.sub('\(\d+\)','({0})'.format(int(m.group()[1:-1])+1),filename.stem)
        else:
            newname = filename.stem+'(1)'
        newname += '.py'
        return sequenceFile(filename.with_name(newname))
    return filename

class OptionsWindow(OptionsWidget, OptionsBase):
    OptionsChangedSignal = QtCore.pyqtSignal()
    def __init__(self, config, configname):
        super().__init__()
        self.config = config
        self.lineno = 99
        self.displayPath = True
        self.defaultExpand = True
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
    currentItem = None
    recentFiles = list()

    def setupUi(self, parent):
        super().setupUi(parent)
        self.fileTreeWidget.setDragDropMode(self.fileTreeWidget.InternalMove)
        self.fileTreeWidget.setSelectionMode(self.fileTreeWidget.ExtendedSelection)
        self.fileTreeWidget.setAcceptDrops(True)
        self.fileTreeWidget.setDragEnabled(True)
        self.fileTreeWidget.setDropIndicatorShown(True)
        self.fileTreeWidget.setSortingEnabled(True)
        self.fileTreeWidget.sortItems(0, QtCore.Qt.AscendingOrder)
        self.fileTreeWidget.setHeaderLabels(['User Function Files'])
        self.allFiles = dict()
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
        self.fileTreeWidget.itemClicked.connect(self.onClick)
        self.fileTreeWidget.itemChanged.connect(self.onItemChanged)

        self.fileTreeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.fileTreeWidget.customContextMenuRequested.connect(self.rightClickMenu)

    def initLoad(self):
        """loads last opened file, if path no longer exists, starts
           trying files in recentFiles, else returns an empty script"""
        if self.script.fullname != '':
            if isinstance(self.script.fullname, str):
                self.script.fullname = Path(self.script.fullname)
            if self.script.fullname.exists():
                self.loadFile(self.script.fullname)
            elif len(self.recentFiles):
                self.script.fullname = self.recentFiles[-1]
                recentFileGen = iter(self.recentFiles)
                while True:
                    if self.script.fullname.exists():
                        self.loadFile(self.script.fullname)
                        break
                    else:
                        self.script.fullname = next(recentFileGen)
                else:
                    self.script.fullname = ''

    def initRecentFiles(self, savedfiles):
        """checks if saved recentFiles list contains bad paths or an obsolete format"""
        if not isinstance(savedfiles, OrderedList):
            savedfiles = OrderedList()
        self.recentFiles = OrderedList()
        for fullname in savedfiles:
            if isinstance(fullname, Path) and fullname.exists():
                self.recentFiles.add(fullname)
            elif isinstance(fullname, str) and os.path.exists(fullname):
                correctedname = Path(fullname)
                self.recentFiles.add(correctedname)

    def initComboBox(self):
        """populates combo box and sets defaults"""
        self.filenameComboBox.setInsertPolicy(1)
        for fullname in self.recentFiles:
            self.filenameComboBox.insertItem(0, self.getName(fullname))
            self.filenameComboBox.setItemData(0, fullname)
        self.filenameComboBox.currentIndexChanged[int].connect(self.onComboIndexChange)
        self.filenameComboBox.setMaxVisibleItems(15)
        self.removeCurrent.clicked.connect(self.onRemoveCurrent)
        self.filenameComboBox.setEditable(False)

    def onItemChanged(self, item):
        """checks to see if file or directory name was changed by the user"""
        if item.isdir and item.text(0) != Path(item.path).stem:
            newpath = sequenceFile(Path(item.path).parent.joinpath(item.text(0)))
            Path(item.path).rename(newpath)
            item.path = str(newpath)
            item.setText(0, newpath.stem)
            changedFiles = []
            checkTree(self.fileTreeWidget.invisibleRootItem(), Path(self.defaultDir), changedFiles)
            self.updatePathChanges(changedFiles)
        elif item.text(0) != Path(item.path).name:
            oldpath = Path(item.path)
            newpath = sequenceFile(Path(item.path).with_name(item.text(0)).with_suffix('.py'))
            Path(item.path).rename(newpath)
            item.path = str(newpath)
            item.setText(0, newpath.name)
            self.updatePathChanges([(oldpath, newpath)])

    def rightClickMenu(self, pos):
        """a CustomContextMenu for right click, different for files and directories"""
        items = self.fileTreeWidget.selectedItems()
        menu = QtWidgets.QMenu()
        self.expandTree = QtWidgets.QAction("Expand All", self)
        self.collapseTree = QtWidgets.QAction("Collapse All", self)
        self.expandChild = QtWidgets.QAction("Expand Selected", self)
        self.collapseChild = QtWidgets.QAction("Collapse Selected", self)
        self.expandTree.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, True, True))
        self.collapseTree.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, True, False))
        self.expandChild.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, False, True))
        self.collapseChild.triggered.connect(lambda: onExpandOrCollapse(self.fileTreeWidget, False, False))
        if items[0].isdir == False:
            menu.addAction(self.expandTree)
            menu.addAction(self.collapseTree)
        else:
            menu.addAction(self.expandTree)
            menu.addAction(self.collapseTree)
            menu.addAction(self.expandChild)
            menu.addAction(self.collapseChild)
        menu.exec_(self.fileTreeWidget.mapToGlobal(pos))

    def populateTree(self, newfilepath=None):
        """constructs the file tree viewer"""
        genFileTree(self.fileTreeWidget.invisibleRootItem(), Path(self.defaultDir), newfilepath, fullFileList=self.allFiles)

    def onDrop(self, event):
        """an extension of dropEvent call that applies path changes to the system"""
        changedFiles = []
        if event.source() == self.fileTreeWidget:
            QtWidgets.QTreeWidget.dropEvent(self.fileTreeWidget, event)
        checkTree(self.fileTreeWidget.invisibleRootItem(), Path(self.defaultDir), changedFiles)
        self.updatePathChanges(changedFiles)
        for oldName, newName in changedFiles:
            if oldName == self.script.fullname:
                self.script.fullname = sequenceFile(newName)

    def updatePathChanges(self, changedFiles):
        """updates path information in file tree, combo box, recentFiles,
           and script attributes after drag/drop or renaming"""
        with BlockSignals(self.filenameComboBox) as w:
            combolen = range(w.count())
            for oldPath, newPath in changedFiles:
                if oldPath == self.script.fullname:
                    self.script.fullname = newPath
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

    def onLoad(self):
        """The load button is clicked. Open file prompt for file."""
        fullname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Script', str(self.defaultDir), 'Python scripts (*.py *.pyw)')
        fullPath = Path(fullname)
        if fullname!="":
            if self.defaultDir not in fullPath.parents:
                if self.copyToDir(self.defaultDir.stem):
                    newpath = sequenceFile(self.defaultDir.joinpath(fullPath.name))
                    newpath.write_bytes(fullPath.read_bytes())
                    fullPath = newpath
                    self.populateTree(fullPath)
                    self.loadFile(fullPath)
            else:
                self.loadFile(fullPath)

    def copyToDir(self, dirname):
        """when loading a file from outside Scripting directory"""
        reply = QtWidgets.QMessageBox.question(self, 'Message',
                                               "Files must be in {} directory, make a local copy?".format(dirname), QtWidgets.QMessageBox.Yes |
                                               QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            return True
        return False

    def onClick(self, *args):
        """enters verified click after doubleClickInterval. if a doubleClick occurs,
           self.currentItem is set to 0 to reset editing condition"""
        QtCore.QTimer.singleShot(QtWidgets.QApplication.instance().doubleClickInterval(), lambda: self.verifiedClick(args[0]))

    def onDoubleClick(self, *args):
        """open a file that is double clicked in file tree"""
        self.currentItem = 0 #resets state of currentItem so as not to edit the filename after being double clicked
        if not args[0].isdir:
            if self.script.code != str(self.textEdit.toPlainText()):
                if not self.confirmLoad():
                    return False
            self.loadFile(Path(args[0].path))

    def verifiedClick(self, args):
        "verifiedClick is a second click that doesn't register as a single click, supports filename editing"
        if args == self.currentItem: #registered as a slow second click, item can be renamed
            args.setFlags(args.flags() | QtCore.Qt.ItemIsEditable)
            self.currpath = args.path
            self.fileTreeWidget.editItem(args)
            args.setFlags(args.flags() ^ QtCore.Qt.ItemIsEditable)
        elif self.currentItem != 0: #next consecutive click on this item will go into edit mode
            self.currentItem = args
        else:
            self.currentItem = 1 #previous click was a double click, initialize slow click state for renaming

    def getName(self, fullpath):
        """returns file name optionally with local path if displayFullPathNames is true"""
        if self.displayFullPathNames:
            return fullpath.relative_to(self.defaultDir).as_posix()
        return fullpath.name

    def updateFileComboBoxNames(self, fullnames):
        """repopulates combo box if MaxCount increases, otherwise updates displayed names if directory
           or file name change or if user opts to display full paths or just local names in options menu"""
        with BlockSignals(self.filenameComboBox) as w:
            if w.count() < w.maxCount() and w.count() < len(self.recentFiles):
                for fullname in self.recentFiles:
                    w.insertItem(0, self.getName(fullname))
                    w.setItemData(0, fullname)
                    w.setCurrentIndex(0)
            else:
                for ind in range(w.count()):
                    w.setItemText(ind, self.getName(w.itemData(ind)))

