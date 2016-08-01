# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


import PyQt5.uic
from PyQt5 import QtGui, QtCore
from modules.SequenceDict import SequenceDict
from networkx import DiGraph
from _collections import defaultdict

ControlForm, ControlBase = PyQt5.uic.loadUiType(r'..\..\ui\TreeViewTest.ui')


class Structure(object):
    def __init__(self):
        self.children = defaultdict( list )
        self.parent = dict()
        
    def addChild(self, parent, child):
        self.children[parent].append(child)
        self.parent[child] = parent
        
    def addChildren(self, parent, children ):
        self.children[parent].extend(children)
        for child in children:
            self.parent[child] = parent
                    
    def insertChild(self, parent, child, index ):
        self.children[parent].insert(index, child)
        self.parent[child] = parent
        
    def insertChildren(self, parent, children, index ):
        oldlist = self.children[parent]
        newlist = oldlist[:index]
        newlist.extend(children)
        newlist.extend(oldlist[index:])
        self.children[parent] = newlist
        for child in children:
            if child in self.parent:
                self.removeChild(self.parent[child], child)
            self.parent[child] = parent
        
    def removeChild(self, parent, child):
        children = self.children[parent]
        children.pop( children.index(child) )
        self.parent.pop(child)
        
        

class TreeViewModelAdapter( QtCore.QAbstractItemModel ):
    def __init__(self, data, structure, rootNode, parent=None ):
        super(TreeViewModelAdapter, self).__init__(parent)
        self.data = data
        self.structure = structure
        self.rootNode = rootNode
        self.dataLookup = { (QtCore.Qt.DisplayRole, 0): lambda child: child,
                            (QtCore.Qt.DisplayRole, 1): lambda child: self.data[child] }
        
    def data(self, index, role):
        nodeName = self.getItem(index)
        return self.dataLookup.get( (role, index.column()), lambda child: None )(nodeName)

    def flags(self, index):
        if index.column()<=0:
            return (QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled) 
        return (QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable)

    headerLookup = ['Key', 'Value']
    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerLookup[section]

    def index(self, row, column, parent):
        if (parent.isValid() and parent.column() != 0):
            return QtCore.QModelIndex()
        parentName = self.getItem(parent)
        if row>=len(self.structure.children[parentName]):
            return QtCore.QModelIndex()
        childName =  self.structure.children[parentName][row]
        if childName:
            return self.createIndex(row, column, childName)
    
    def getItem(self, index):
        if index.isValid():
            if index.internalPointer() not in self.structure.parent:
                return None
            return index.internalPointer()
        return self.rootNode    

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        childName = self.getItem(index)
        if childName is None:
            return QtCore.QModelIndex()
        parentName = self.structure.parent[childName]
        if parentName == self.rootNode:
            return QtCore.QModelIndex()
        return self.createIndex(self.structure.children[parentName].index(childName), 0, parentName)
        
    def rowCount(self, parent):
        parentName = self.getItem(parent)
        return len(self.structure.children[parentName]) 
    
    def columnCount(self, parent):
        return len(self.headerLookup)
    
    def supportedDragActions(self):
        return QtCore.Qt.MoveAction
    
    def supportedDropActions(self):
        return QtCore.Qt.MoveAction
    
    def mimeTypes(self):
        return ["text.list"]
    
    def mimeData(self, indices):
        mimedata = QtCore.QMimeData()
        mimedata.setData('text.list', '\n'.join((self.getItem(index) for index in indices)) )
        return mimedata
        
    def dropMimeData(self, mimedata, action, row, column, parentIndex ):
        if not mimedata.hasFormat("text.list") or column>0:
            return False
        items = str(mimedata.data("text.list")).splitlines()
        self.insertItems(row, items, parentIndex)
        return True
    
    def insertItems(self, row, items, parentIndex):
        parentName = self.getItem(parentIndex)
        print("insert", items)
        for item in items:
            oldParent = self.structure.parent[item]
            oldRow = self.structure.children[oldParent].index(item)
            self.beginRemoveRows( self.createIndex(0, 0, oldParent), oldRow, oldRow )
            self.structure.removeChild(oldParent, item)
            self.endRemoveRows()          
        self.beginInsertRows( parentIndex, row, row+len(items)-1 )
        self.structure.insertChildren( parentName, items, row+1 )
        self.endInsertRows()
        return True 
    
    def removeRows(self, row, count, parent):
        print("removeRows", row, count, self.getItem(parent))
        return True

class TreeViewTest( ControlForm, ControlBase ):
    def __init__(self, parent=None):
        ControlForm.__init__(self)
        ControlBase.__init__(self, parent)
        self.data = { 'alpha': 'a', 'beta':'b', 'gamma':'c' , 'delta':'d', 'epsilon':'e'}
        #self.structure = DiGraph()
        #self.structure.add_edges_from([('root','alpha'),('gamma','beta'),('alpha','gamma')])
        self.structure = Structure()
        self.structure.addChildren('root', ['alpha', 'beta', 'gamma', 'delta', 'epsilon'] )
       
    def setupUi(self, parent):
        ControlForm.setupUi(self, parent)
        self.model = TreeViewModelAdapter(self.data, self.structure, 'root')
        self.treeView.setModel( self.model )
        self.treeView.setDragEnabled(True)
        self.treeView.setAcceptDrops(True)
        self.treeView.setDropIndicatorShown(True)
        # History and Dictionary

if __name__=="__main__":
    import sys
    from PyQt5 import QtGui
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    
    
    data = SequenceDict( {})
    
    ui = TreeViewTest()
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
