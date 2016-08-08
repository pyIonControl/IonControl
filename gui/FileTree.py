# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os.path
from PyQt5 import QtWidgets, QtCore
from pathlib import Path

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

def getName(fullpath, dispfull=False):
    if dispfull:
        return self.fullname.split(self.splitDir)[-1]
    return os.path.basename(self.fullname)
#
    #@QtCore.pyqtProperty(str)
    #def localpathname(self):
        #return self.fullname.split(self.splitDir)[-1]

#class FileTreeModel(QtCore.QAbstractItemModel):
#
    #def __init__(self):
        #super().__init__()
        ##self.setHeaderLabels(['User Function Files'])
        ##super(FileTreeModel, self).setDragEnabled(True)
        ##self.setDragDropMode(self.InternalMove)
        ##self.setDropIndicatorShown(True)
#
#
    #def dropEvent(self, event):
        #item = self.itemAt(event.pos())
        #super(FileTreeModel,self).dropEvent(event)
        ##if item is not None and ( isinstance(item.data, Family) ):
            ##super(CustomTreeWidget,self).dropEvent(event)
        ##self.dropEvent(event)
        #print(item.path)
        ##moveFiles(item)
        ##else:
            ##print "ignored"
            ###event.setDropAction(QtCore.Qt.IgnoreAction)
