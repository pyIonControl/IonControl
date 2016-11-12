# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui, QtWidgets
from _functools import partial
import copy

#from gui.TodoList import TodoListEntry


class BaseNode(object):
    def __init__(self, parent, row):
        self.parent = parent
        self.row = row
        self.childNodes = self._children()

    def _children(self):
        raise NotImplementedError()

class TodoListNode(BaseNode):
    def __init__(self, entry, parent, row, labelDict):
        self.entry = entry
        self.highlighted = False
        self.labelDict = labelDict
        BaseNode.__init__(self, parent, row)

    def _children(self):
        childList = list()
        labelDict = dict()
        if not isinstance(self.entry, TodoListNode):#'children'):
            for ind in range(len(self.entry.children)):
                node = TodoListNode(self.entry.children[ind], self, ind, self.labelDict)
                childList.append(node)
                if node.entry.label != '':
                    self.labelDict[node.entry.label] = node
        ##self.labelDict.update(labelDict)
        return childList


        #childList = [TodoListNode(self.entry.children[ind], self, ind) for ind in range(len(self.entry.children))]
        #labelDict = {self.}
        #return [TodoListNode(self.entry.children[ind], self, ind) for ind in range(len(self.entry.children))]

    def recursiveLookup(self, rowlist):
        if len(rowlist) == 1:
            try:
                return self.childNodes[rowlist[0]]
            except:
                pass
        return self.childNodes[rowlist[0]].recursiveLookup(rowlist[1:])

class TodoListBaseModel(QtCore.QAbstractItemModel):
    def __init__(self):
        QtCore.QAbstractItemModel.__init__(self)
        self.rootNodes = self._rootNodes(init=True)

    def _rootNodes(self, init=False):
        raise NotImplementedError()

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self.rootNodes[row])
        parentNode = parent.internalPointer()
        return self.createIndex(row, column, parentNode.childNodes[row])

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        node = index.internalPointer()
        if not hasattr(node, 'parent') or node.parent is None:
            return QtCore.QModelIndex()
        else:
            return self.createIndex(node.parent.row, 0, node.parent)

    def reset(self):
        self.rootNodes = self._rootNodes()
        QtCore.QAbstractItemModel.reset(self)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if not parent.isValid():
            return len(self.rootNodes)
        node = parent.internalPointer()
        return len(node.childNodes)

    def recursiveLookup(self, rowlist):
        if len(rowlist) == 1:
            try:
                return self.rootNodes[rowlist[0]]
            except:
                pass
        return self.rootNodes[rowlist[0]].recursiveLookup(rowlist[1:])

class TodoListTableModel(TodoListBaseModel):
    valueChanged = QtCore.pyqtSignal( object )
    headerDataLookup = ['Enable', 'Scan type', 'Scan', 'Evaluation', 'Analysis', 'Condition']
    def __init__(self, todolist, settingsCache, labelDict, parent=None, *args):
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        self.todolist = todolist
        self.labelDict = labelDict
        self.settingsCache = settingsCache
        TodoListBaseModel.__init__(self)
        self.nodeDataLookup = {
             (QtCore.Qt.CheckStateRole, 0): lambda node: QtCore.Qt.Checked
                                                         if node.entry.enabled
                                                         else QtCore.Qt.Unchecked,
             (QtCore.Qt.DisplayRole,    0): lambda node: node.entry.label,
             (QtCore.Qt.DisplayRole,    1): lambda node: node.entry.scan,
             (QtCore.Qt.DisplayRole,    2): lambda node: node.entry.measurement,
             (QtCore.Qt.DisplayRole,    3): lambda node: node.entry.evaluation
                                                         if (node.entry.scan == 'Scan' or
                                                             node.entry.scan == 'Todo List')
                                                         else '',
             (QtCore.Qt.DisplayRole,    4): lambda node: node.entry.analysis
                                                         if (node.entry.scan == 'Scan' or
                                                             node.entry.scan == 'Todo List')
                                                         else '',
             (QtCore.Qt.DisplayRole,    5): lambda node: node.entry.condition,
             (QtCore.Qt.EditRole,       0): lambda node: node.entry.label,
             (QtCore.Qt.EditRole,       1): lambda node: node.entry.scan,
             (QtCore.Qt.EditRole,       2): lambda node: node.entry.measurement,
             (QtCore.Qt.EditRole,       3): lambda node: node.entry.evaluation,
             (QtCore.Qt.EditRole,       4): lambda node: node.entry.analysis,
             (QtCore.Qt.EditRole,       5): lambda node: node.entry.condition,
             (QtCore.Qt.TextAlignmentRole, 0): lambda node: QtCore.Qt.AlignRight
             }
        self.colorDataLookup = {
             (QtCore.Qt.BackgroundRole, 0): lambda node: self.colorStopFlagLookup[node.entry.stopFlag],
             (QtCore.Qt.BackgroundRole, 1): lambda node: self.colorLookup[self.running]
                                                         if node.highlighted else QtCore.Qt.white,
             (QtCore.Qt.BackgroundRole, 2): lambda node: QtCore.Qt.white,
             (QtCore.Qt.BackgroundRole, 3): lambda node: self.bgLookup(node),
             (QtCore.Qt.BackgroundRole, 4): lambda node: self.bgLookup(node),
             (QtCore.Qt.BackgroundRole, 5): lambda node: QtGui.QColor(255, 255, 255, 255)
                                                         if node.entry.condition != ''
                                                         else QtGui.QColor(215, 215, 215, 255)
        }
        self.setDataLookup ={(QtCore.Qt.CheckStateRole, 0): self.setEntryEnabled,
                             (QtCore.Qt.EditRole, 0): partial( self.setString, 'label' ),
                             (QtCore.Qt.EditRole, 1): partial( self.setString, 'scan' ),
                             (QtCore.Qt.EditRole, 2): partial( self.setString, 'measurement' ),
                             (QtCore.Qt.EditRole, 3): partial( self.setString, 'evaluation' ),
                             (QtCore.Qt.EditRole, 4): partial( self.setString, 'analysis' ),
                             (QtCore.Qt.EditRole, 5): partial( self.setString, 'condition' )
                             }
        self.colorLookup = {True: QtGui.QColor(0xd0, 0xff, 0xd0), False: QtGui.QColor(0xff, 0xd0, 0xd0)}
        self.colorStopFlagLookup = {True: QtGui.QColor( 0xcb, 0x4e, 0x28), False: QtCore.Qt.white}
        self.activeRow = None
        self.activeEntry = None
        self.tabSelection = []
        self.measurementSelection = {}
        self.evaluationSelection = {}
        self.analysisSelection = {}
        self.choiceLookup = { 1: lambda row: list(self.measurementSelection.keys()),
                              2: lambda row: self.measurementSelection[self.todolist[row].scan],
                              3: lambda row: self.evaluationSelection[self.todolist[row].scan],
                              4: lambda row: self.analysisSelection[self.todolist[row].scan]}

    def _rootNodes(self, init=False):
        if init:
            for ind in range(len(self.todolist)):
                if self.todolist[ind].scan == 'Todo List':
                    self.todolist[ind].children = self.settingsCache[self.todolist[ind].measurement].todoList
                #elif self.todolist[ind].scan == 'Rescan':
                    #self.todolist[ind].children = [copy.deepcopy(self.labelDict[lbl].entry) for lbl in self.todolist[ind].measurement]#self.settingsCache[self.todolist[index.row()].measurement].todoList
        nodeList = list()
        for ind in range(len(self.todolist)):
            node = TodoListNode(self.todolist[ind], None, ind, self.labelDict)
            nodeList.append(node)
            if node.entry.label != '':
                self.labelDict[node.entry.label] = node
        return nodeList

    def updateRootNodes(self):
        self.beginResetModel()
        self.rootNodes = self._rootNodes()
        self.endResetModel()

    def bgLookup(self, node):
        if node.entry.scan == 'Script' or node.entry.scan == 'Todo List':
            return QtGui.QColor(215, 215, 215, 255)
        return QtGui.QColor(255, 255, 255, 255)
        #if node.entry.scan == 'Scan':
            #return QtGui.QColor(255, 255, 255, 255)
        #if node.entry.scan == 'Script' or node.entry.scan == 'Todo List':
            #return QtGui.QColor(215, 215, 215, 255)

    def setString(self, attr, index, value):
        setattr(self.nodeFromIndex(index).entry, attr, str(value))
        return True

    def setEntryEnabled(self, index, value):
        self.nodeFromIndex(index).entry.enabled = value == QtCore.Qt.Checked
        return True

    def setActiveRow(self, rowlist, running=True):
        ref = self.recursiveLookup(rowlist)
        row = rowlist[-1]
        oldactive = None
        if self.activeEntry is not None:
            self.activeEntry.highlighted = False
            oldactive = self.activeEntry.row
        ref.highlighted = True
        self.activeEntry = ref
        self.activeRow = row
        self.running = running
        if row is not None:
            self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
        if oldactive is not None and oldactive!=row:
            self.dataChanged.emit( self.createIndex(oldactive, 0), self.createIndex(oldactive+1, 3) )
        print(self.labelDict)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 6

    def nodeFromIndex(self, index):
        """Return the node at the given index"""
        return index.internalPointer() if index.isValid() else self.root

    def data(self, index, role):
        if index.isValid():
            return self.nodeDataLookup.get((role, index.column()), lambda row: None)(self.nodeFromIndex(index))
        return None

    def colorData(self, index):
        if index.isValid():
            return self.colorDataLookup.get((QtCore.Qt.BackgroundRole, index.column()), lambda row: QtGui.QColor(255, 255, 255, 255))(self.nodeFromIndex(index))
        return QtGui.QColor(255, 255, 255, 255)


    def setData(self, index, value, role):
        if index.isValid():
            value = self.setDataLookup.get((role, index.column()), lambda index, value: None)(index, value)
            if self.todolist[index.row()].scan == 'Todo List':
                self.todolist[index.row()].children = self.settingsCache[self.todolist[index.row()].measurement].todoList
                self.beginResetModel()
                self.rootNodes[index.row()] = TodoListNode(self.todolist[index.row()], None, index.row(), self.labelDict)
                self.endResetModel()
            #elif self.todolist[index.row()].scan == 'Rescan':
                #labelList = []
                #for lbl in self.todolist[index.row()].measurement:
                    #entry = copy.deepcopy(self.labelDict[lbl].entry)
                    #entry.label = ''
                    #labelList.append(entry)
                #self.todolist[index.row()].children = labelList#[copy.deepcopy(self.labelDict[lbl].entry) for lbl in self.todolist[index.row()].measurement]#self.settingsCache[self.todolist[index.row()].measurement].todoList
                #self.beginResetModel()
                #self.rootNodes[index.row()] = TodoListNode(self.todolist[index.row()], None, index.row(), self.labelDict)
                #self.endResetModel()
            if value:
                self.valueChanged.emit( None )
            return value
        return False

    def flags(self, index):
        if self.todolist[index.row()].scan == 'Scan':
            return (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable if index.column()==0 else
                    QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable )
        elif self.todolist[index.row()].scan == 'Script' or self.todolist[index.row()].scan == 'Todo List':
            if index.column()==0:
                return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | \
                       QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable
            elif index.column()==1 or index.column()==2 or index.column()==5:
                return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
            else:
                return QtCore.Qt.ItemIsSelectable
        elif self.nodeFromIndex(index).entry.scan == 'Rescan':
            if index.column()==0:
                return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | \
                       QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable
            elif index.column()==1 or index.column()==2 or index.column()==5:
                return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
            else:
                return QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None
                        
    def moveRow(self, rows, up=True):
        if up:
            if len(rows)>0 and rows[0]>0:
                for row in rows:
                    self.todolist[row], self.todolist[row-1] = self.todolist[row-1], self.todolist[row]
                    self.dataChanged.emit(self.createIndex(row-1, 0), self.createIndex(row, 3))
                self.updateRootNodes()
                return True
        else:
            if len(rows)>0 and rows[0]<len(self.todolist)-1:
                for row in rows:
                    self.todolist[row], self.todolist[row+1] = self.todolist[row+1], self.todolist[row]
                    self.dataChanged.emit(self.createIndex(row, 0), self.createIndex(row+1, 3))
                self.updateRootNodes()
                return True
        return False

    def addMeasurement(self, todoListElement):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.todolist), len(self.todolist))
        self.todolist.append(todoListElement)
        self.endInsertRows()
        self.updateRootNodes()
        return len(self.todolist)-1
        
    def dropMeasurement (self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.todolist.pop(row)
        self.endRemoveRows()
        self.updateRootNodes()

    def setTodolist(self, todolist):
        self.beginResetModel()
        self.todolist = todolist
        self.rootNodes = self._rootNodes(init=True)
        self.endResetModel()
        
    def choice(self, index):
        return self.choiceLookup.get(index.column(), lambda row: [])(index.row())
    
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)

    def copy_rows(self, row_list):
        """ Copy a the rows given and append to the end of the TODO list.
        row_list :: [Int] List of rows to copy
        """
        for row_index in row_list:
            row_data = self.todolist[row_index]
            self.addMeasurement(copy.deepcopy(row_data))
        self.updateRootNodes()

