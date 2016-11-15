# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui, QtWidgets
from _functools import partial
import copy

from itertools import chain

from modules.flatten import flattenAll


class BaseNode(object):
    def __init__(self, parent, row):
        self.parent = parent
        self.row = row
        self.childNodes = self._children()
        if self.hideChildren:
            self.hiddenChildren = self.childNodes
            self.childNodes = list()

    def _children(self):
        raise NotImplementedError()

class TodoListNode(BaseNode):
    allNodes = []

    def __init__(self, entry, parent, row, labelDict, hideChildren=False, highlighted=False):
        self.entry = entry
        self.highlighted = highlighted
        self.labelDict = labelDict
        self.hideChildren = hideChildren
        self.hiddenChildren = None
        BaseNode.__init__(self, parent, row)

    def _children(self):
        childList = list()
        if not self.hideChildren:
            for ind in range(len(self.entry.children)):
                node = TodoListNode(self.entry.children[ind], self, ind, self.labelDict)
                childList.append(node)
                if node.entry.label != '':
                    self.labelDict[node.entry.label] = node
        else:
            childList = self.entry.children
        return childList

    def topLevelParent(self):
        if self.parent is not None:
            return self.parent.topLevelParent()
        return self

    def incrementer(self, initNode=None):
        iterator = flattenAll(self.incr(initNode))
        for item in iterator:
            yield item

    def incr(self, initNode=None):
        if not self.entry.enabled or (self.entry.condition != '' and (not eval(self.entry.condition) and self.entry.stopFlag)):
            return [] #doesn't create a generator for disabled todo list items, needed here for sublists/rescans
        if initNode is None or initNode is self:
            if self.childNodes:
                return flattenAll([item.incr(initNode) for item in self.childNodes])
            elif self.hideChildren:
                return flattenAll([self.labelDict[child].incr(initNode) for child in self.hiddenChildren])
            else:
                return [self]
        elif isinstance(initNode, list):
            return chain(item.incr() for item in initNode)
        elif initNode in self.childNodes:
            return chain(item.incr(initNode) for item in self.childNodes[initNode.row:])
        else:
            return [self]

    def increment(self):
        try:
            return next(self.childGenerator)
        except StopIteration:
            return False

    @classmethod
    def initializeGenerators(cls):
        for node in cls.allNodes:
            node.childGenerator = node.incrementer()

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
        self.inRescan = False
        self.currentRescanList = list()
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

    def entryGenerator(self, node=None):
        if node is None:
            initRow = 0
            initNode = self.rootNodes[0]
        else:
            initRow = node.topLevelParent().row
            initNode = node
        for root in self.rootNodes[initRow:]:
            self.inRescan = True if root.hideChildren else False
            self.currentRescanList = [self.labelDict[child] for child in root.hiddenChildren] if root.hideChildren else list()
            yield from root.incrementer()

    def flattenEntries(self, item):
        for subitem in item:
            if isinstance(subitem, TodoListNode):
                yield subitem
            else:
                yield from self.flattenEntries(subitem)

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
    ignoreTypes = ['Scan', ]
    def __init__(self, todolist, settingsCache, labelDict, currentRescanList, parent=None, *args):
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        self.todolist = todolist
        self.labelDict = labelDict
        self.settingsCache = settingsCache
        TodoListBaseModel.__init__(self)
        self.defaultDarkBackground = QtGui.QColor(225, 225, 225, 255)
        self.nodeDataLookup = {
             (QtCore.Qt.CheckStateRole, 0): lambda node: QtCore.Qt.Checked
                                                         if node.entry.enabled
                                                         else QtCore.Qt.Unchecked,
             (QtCore.Qt.DisplayRole,    0): lambda node: node.entry.label,
             (QtCore.Qt.DisplayRole,    1): lambda node: node.entry.scan,
             (QtCore.Qt.DisplayRole,    2): lambda node: node.entry.measurement,
             (QtCore.Qt.DisplayRole,    3): lambda node: node.entry.evaluation
                                                         if node.entry.scan == 'Scan'# or
                                                             #node.entry.scan == 'Todo List')
                                                         else '',
             (QtCore.Qt.DisplayRole,    4): lambda node: node.entry.analysis
                                                         if node.entry.scan == 'Scan'# or
                                                             #node.entry.scan == 'Todo List' )
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
        self.darkColorDataLookup = {
            (QtCore.Qt.BackgroundRole, 0): lambda node: self.colorStopFlagLookup[node.entry.stopFlag],
            (QtCore.Qt.BackgroundRole, 1): lambda node: self.colorLookup[self.running]
                                                        if node.highlighted else self.defaultDarkBackground,
            (QtCore.Qt.BackgroundRole, 2): lambda node: self.defaultDarkBackground,
            (QtCore.Qt.BackgroundRole, 3): lambda node: self.bgLookup(node),
            (QtCore.Qt.BackgroundRole, 4): lambda node: self.bgLookup(node),
            (QtCore.Qt.BackgroundRole, 5): lambda node: self.defaultDarkBackground
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
                self.connectSubTodoLists(self.todolist[ind])
                if self.todolist[ind].scan == 'Rescan':
                    self.todolist[ind].children = [lbl for lbl in self.todolist[ind].measurement.split(',')]
        nodeList = list()
        for ind in range(len(self.todolist)):
            node = TodoListNode(self.todolist[ind], None, ind, self.labelDict, hideChildren=self.todolist[ind].scan == 'Rescan')
            nodeList.append(node)
            if node.entry.label != '':
                self.labelDict[node.entry.label] = node
        return nodeList

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self.rootNodes[row])
        parentNode = parent.internalPointer()
        return self.createIndex(row, column, parentNode.childNodes[row])

    def connectSubTodoLists(self, item):
        if item.scan == 'Todo List':
            item.children = self.settingsCache[item.measurement].todoList
            for ind in range(len(item.children)):
                self.connectSubTodoLists(item.children[ind])

    def updateRootNodes(self):
        self.beginResetModel()
        self.rootNodes = self._rootNodes()
        self.endResetModel()
        if self.activeEntry is not None:
            self.setActiveItem(self.activeEntry, self.running)

    def bgLookup(self, node):
        if node.entry.scan == 'Script' or \
           node.entry.scan == 'Todo List' or \
           node.entry.scan == 'Rescan':
            return QtGui.QColor(215, 215, 215, 255)
        elif self.currentRescanList and node not in self.currentRescanList:
            return self.defaultDarkBackground
        return QtGui.QColor(255, 255, 255, 255)

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
        self.activeEntry.highlighted = True
        self.activeRow = row
        self.running = running
        if row is not None:
            self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
        if oldactive is not None and oldactive!=row:
            self.dataChanged.emit( self.createIndex(oldactive, 0), self.createIndex(oldactive+1, 3) )

    def setActiveItem(self, item, running=True):
        if self.activeEntry is not None:
            self.activeEntry.highlighted = False
            oldactive = self.activeEntry.row
        self.activeEntry = item
        self.activeEntry.highlighted = True
        self.activeRow = item.row
        self.running = running
        row = item.row
        if row is not None:
            self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
        if oldactive is not None and oldactive!=row:
            self.dataChanged.emit( self.createIndex(oldactive, 0), self.createIndex(oldactive+1, 3) )

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
            if len(self.currentRescanList):
                if self.nodeFromIndex(index) not in self.currentRescanList:
                    return self.darkColorDataLookup.get((QtCore.Qt.BackgroundRole, index.column()), lambda row: self.defaultDarkBackground)(self.nodeFromIndex(index))
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
                if self.activeEntry is not None:
                    self.setActiveItem(self.activeEntry, self.running)
            if self.nodeFromIndex(index).entry.scan == 'Rescan':
                self.nodeFromIndex(index).entry.children = [lbl for lbl in self.nodeFromIndex(index).entry.measurement.split(',')]
                self.nodeFromIndex(index).hiddenChildren = self.nodeFromIndex(index)._children()
                #self.todolist[index.row()].children = [lbl for lbl in self.nodeFromIndex(index).entry.measurement.split(',')]
                #self.updateRootNodes()
            if value:
                self.valueChanged.emit( None )
            return value
        #self.setActiveItem(self.activeEntry, self.running)
        return False

    def setValue(self, index):
        self.updateRootNodes()
        #if self.nodeFromIndex(index).entry.scan == 'Rescan':
            #self.nodeFromIndex(index).entry.hiddenChildren = [lbl for lbl in self.nodeFromIndex(index).entry.measurement.split(',')]

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
        if self.activeEntry is not None:
            self.setActiveItem(self.activeEntry, self.running)

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

