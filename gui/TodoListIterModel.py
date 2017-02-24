# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import deque, ChainMap

from PyQt5 import QtCore, QtGui, QtWidgets
from _functools import partial
import copy

from itertools import chain

from modules.Expression import Expression
from modules.ChainMapStack import ChainMapStack
from modules.flatten import flattenAll

PARENT_TYPES = {'Todo List', 'Rescan'}
GLOBALORDICT = ChainMapStack()

class StopNode:
    """Dummy class that is used to signal if a stop flag is encountered"""
    def updateChildren(self):
        pass

class BaseNode:
    """Skeleton for todo list nodes"""
    def __init__(self, parent, row):
        self.parent = parent
        self.row = row
        self._childNodes = self._children()

    @property
    def childNodes(self):
        if self.hideChildren:
            return list()
        return self._childNodes

    def _children(self):
        raise NotImplementedError()

    def updateChildren(self):
        self._childNodes = self._children()

    def rowList(self):
        if self.parent is not None:
            return list(flattenAll([self.parent.rowList(), self.row]))
        return [self.row]

class TodoListNode(BaseNode):
    rescanNodes = set()
    def __init__(self, entry, parent, row, labelDict, hideChildren=False, highlighted=False, globaldict=None):
        self.entry = entry
        if self.entry.scan == 'Rescan':
            self.rescanNodes.add(self)
        self.highlighted = highlighted
        self.label = ''
        self.labelDict = labelDict
        self.hideChildren = hideChildren # currently used for Rescan
        self.globalDict = globaldict if globaldict is not None else []
        self.exprEval = Expression()
        self.globalOverrides = self.entry.settings
        BaseNode.__init__(self, parent, row)

    @property
    def enabled(self):
        """intended for subtodo lists: checks if parents are also enabled"""
        if self.parent is not None:
            return self.entry.enabled and self.parent.enabled
        return self.entry.enabled

    def _children(self):
        """seek out child nodes and put them into the appropriate format, differs for rescans and subtodo lists"""
        childList = list()
        if not self.hideChildren:
            for ind in range(len(self.entry.children)):
                node = TodoListNode(self.entry.children[ind], self, ind, self.labelDict, globaldict=self.globalDict)
                childList.append(node)
                if node.entry.label != '':
                    if node.entry.label != node.label:
                        if node.label != '' and node.label in self.labelDict:
                            del self.labelDict[node.label]
                        node.label = copy.copy(node.entry.label)
                    self.labelDict[node.entry.label] = node
        else:
            childList = [self.labelDict[child] for child in self.entry.children if child in self.labelDict]
        return childList

    def topLevelParent(self):
        if self.parent is not None:
            return self.parent.topLevelParent()
        return self

    def __iter__(self):
        """Makes todo list nodes iterable, if the node has children they are automatically collected and returned
           as a collection of iterators. The 'with self' statement takes advantage of the built in __enter__ and
           __exit__ context definitions and is used to keep track of nested global overrides as the iterator is
           consumed. The node itself is yielded automatically and handled later, this causes the active element to
           step forward by one row if the todo list is stopped, and it also prevents indexing bugs when starting
           from a subtodo list or a rescan. StopNode() is an empty object that is yielded to indicate that a stop
           flag is enabled. Passing StopNode() greatly simplifies handling of rescans/subtodo lists with stop flags
           enabled."""
        with self:
            yield self
            if self._childNodes and self.evalCondition(True): #limiting elements with evalCondition() here supports recursive Rescan calls but is not ideal
                yield from chain(*map(iter, self._childNodes))
        if self.entry.enabled and self.entry.stopFlag:
            yield StopNode()

    def __enter__(self):
        """push current global overrides to the global override chain map stack"""
        if self.globalOverrides:
            GLOBALORDICT.push(self.globalOverrides)
        return GLOBALORDICT

    def __exit__(self, exc_type, exc_val, exc_tb):
        """pop current global overrides off the global override chain map stack"""
        if self.globalOverrides:
            GLOBALORDICT.pop()

    def evalCondition(self, recursive=False):
        """evaluate condition entry. If recursive is true, it only checks for the condition if the node is also
           one of its own children. The recursive feature is necessary for minor bugfixes for recursive rescans"""
        if recursive:
            if self in self._childNodes:
                return self.evalCondition()
            return True
        condition = True if self.entry.condition == '' else self.exprEval.evaluate(self.entry.condition, ChainMap(GLOBALORDICT, self.globalDict))
        return condition

    @classmethod
    def updateRescans(cls):
        """Recalculate children for rescans which contain labels that have not yet been created."""
        for node in copy.copy(cls.rescanNodes):
            node.updateChildren()

    def recursiveLookup(self, rowlist):
        if len(rowlist) == 1:
            try:
                return self.childNodes[rowlist[0]]
            except:
                pass
        return self.childNodes[rowlist[0]].recursiveLookup(rowlist[1:])


class TodoListBaseModel(QtCore.QAbstractItemModel):
    def __init__(self, globalDict):
        QtCore.QAbstractItemModel.__init__(self)
        self.inRescan = False
        self.currentRescanList = list()
        self.rootNodes = self._rootNodes(init=True)
        TodoListNode.updateRescans()
        self.globalDict = globalDict

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
        """Creates a generator from the root nodes"""
        if node is None:
            initRow = 0
        else:
            initRow = node.topLevelParent().row
        for root in self.rootNodes[initRow:]:
            self.inRescan = True if root.hideChildren else False
            self.currentRescanList = [root, *root._childNodes] if root.hideChildren else list()
            yield from iter(root)

    def recursiveLookup(self, rowlist):
        if len(rowlist) == 1:
            try:
                return self.rootNodes[rowlist[0]]
            except:
                return None
        return self.rootNodes[rowlist[0]].recursiveLookup(rowlist[1:])

class TodoListTableModel(TodoListBaseModel):
    valueChanged = QtCore.pyqtSignal( object )
    labelsChanged = QtCore.pyqtSignal(str, bool)
    headerDataLookup = ['Enable', 'Scan type', 'Scan', 'Evaluation', 'Analysis', 'Condition']
    ignoreTypes = ['Scan', ]
    def __init__(self, todolist, settingsCache, labelDict, globalDict, parent=None, *args):
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        self.todolist = todolist
        self.labelDict = labelDict
        self.settingsCache = settingsCache
        self.globalDict = globalDict
        TodoListBaseModel.__init__(self, globalDict)
        self.defaultDarkBackground = QtGui.QColor(225, 225, 225, 255)
        self.nodeDataLookup = {
            (QtCore.Qt.CheckStateRole, 0): lambda node: QtCore.Qt.Checked
            if node.entry.enabled
            else QtCore.Qt.Unchecked,
            (QtCore.Qt.DisplayRole,    0): lambda node: node.entry.label,
            (QtCore.Qt.DisplayRole,    1): lambda node: node.entry.scan,
            (QtCore.Qt.DisplayRole,    2): lambda node: node.entry.measurement,
            (QtCore.Qt.DisplayRole,    3): lambda node: node.entry.evaluation
            if node.entry.scan == 'Scan'
            else '',
            (QtCore.Qt.DisplayRole,    4): lambda node: node.entry.analysis
            if node.entry.scan == 'Scan'
            else '',
            (QtCore.Qt.DisplayRole,    5): lambda node: node.entry.condition,
            (QtCore.Qt.EditRole,       0): lambda node: node.entry.label,
            (QtCore.Qt.EditRole,       1): lambda node: node.entry.scan,
            (QtCore.Qt.EditRole,       2): lambda node: node.entry.measurement,
            (QtCore.Qt.EditRole,       3): lambda node: node.entry.evaluation,
            (QtCore.Qt.EditRole,       4): lambda node: node.entry.analysis,
            (QtCore.Qt.EditRole,       5): lambda node: node.entry.condition
            #(QtCore.Qt.TextAlignmentRole, 0): lambda node: QtCore.Qt.AlignRight #right justify labels, messes up editor position
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
            (QtCore.Qt.BackgroundRole, 3): lambda node: self.bgLookup(node, True),
            (QtCore.Qt.BackgroundRole, 4): lambda node: self.bgLookup(node, True),
            (QtCore.Qt.BackgroundRole, 5): lambda node: self.defaultDarkBackground
            if node.entry.condition != ''
            else QtGui.QColor(195, 195, 195, 255)
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
        self.choiceLookup = { 1: lambda node: list(self.measurementSelection.keys()),
                              2: self.measurementSelectionLimiter,
                              3: lambda node: self.evaluationSelection[node.entry.scan],
                              4: lambda node: self.analysisSelection[node.entry.scan]}

    def _rootNodes(self, init=False):
        TodoListNode.rescanNodes.clear()
        if init:
            for ind in range(len(self.todolist)):
                self.connectSubTodoLists(self.todolist[ind])
                if self.todolist[ind].scan == 'Rescan':
                    self.todolist[ind].children = [lbl for lbl in self.todolist[ind].measurement.split(',')]
        nodeList = list()
        for ind in range(len(self.todolist)):
            node = TodoListNode(self.todolist[ind], None, ind, self.labelDict, hideChildren=self.todolist[ind].scan == 'Rescan', globaldict=self.globalDict)#, updchildsig=self.updateChildrenSignal)
            nodeList.append(node)
            if node.entry.label != '':
                if node.entry.label != node.label:
                    if node.label != '':
                        del self.labelDict[node.label]
                        self.labelsChanged.emit(node.label, False)
                    node.label = copy.copy(node.entry.label)
                self.labelDict[node.entry.label] = node #should dummy nodes be added in the init routine?
                self.labelsChanged.emit(node.label, True)
        return nodeList

    def measurementSelectionLimiter(self, node):
        """Ensures that a subtodo list can not specify the todo list in which it's
           contained. Also works for nested todo lists (ie subsubtodo lists and so on)"""
        if node.entry.scan != 'Todo List':
            return self.measurementSelection[node.entry.scan]
        reductionSet = set()
        parent = node.parent
        while parent is not None:
            if parent.entry.scan == 'Todo List':
                reductionSet.add(parent.entry.measurement)
            parent = parent.parent
        return sorted(set(self.measurementSelection[node.entry.scan]) - reductionSet)

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self.rootNodes[row])
        parentNode = parent.internalPointer()
        return self.createIndex(row, column, parentNode.childNodes[row])

    def connectSubTodoLists(self, item):
        """grabs all todo list information for subtodo lists"""
        if item.scan == 'Todo List':
            if item.measurement in self.settingsCache.keys():
                item.children = self.settingsCache[item.measurement].todoList
                for ind in range(len(item.children)):
                    self.connectSubTodoLists(item.children[ind])

    def updateRootNodes(self, init=False):
        """reconstruct the tree"""
        self.beginResetModel()
        self.rootNodes = self._rootNodes(init)
        TodoListNode.updateRescans()
        self.endResetModel()
        if self.activeEntry is not None:
            self.setActiveItem(self.activeEntry, self.running)

    def bgLookup(self, node, darkbg=False):
        if node.entry.scan == 'Script' or \
                        node.entry.scan == 'Todo List' or \
                        node.entry.scan == 'Rescan':
            return QtGui.QColor(195, 195, 195, 255) if darkbg else QtGui.QColor(215, 215, 215, 255)
        elif self.currentRescanList and node not in self.currentRescanList:
            return self.defaultDarkBackground
        return QtGui.QColor(255, 255, 255, 255)

    def setString(self, attr, index, value):
        setattr(self.nodeFromIndex(index).entry, attr, str(value))
        return True

    def setEntryEnabled(self, index, value):
        """Toggle the enable checkbox"""
        self.nodeFromIndex(index).entry.enabled = value == QtCore.Qt.Checked
        return True

    def setActiveRow(self, rowlist, running=True):
        """Sets the current highlighted row. Preferably setActiveItem should be used
           but this method is necessary for initializing the todo list on startup"""
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
        """Sets the current highlighted item"""
        oldactive = None
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
        node = self.nodeFromIndex(index)
        if index.isValid():
            value = self.setDataLookup.get((role, index.column()), lambda index, value: None)(index, value)
            if node.entry.scan == 'Todo List':
                self.beginResetModel()
                node.entry.children = self.settingsCache[node.entry.measurement].todoList
                node.updateChildren()
                self.endResetModel()
                if self.activeEntry is not None:
                    self.setActiveItem(self.activeEntry, self.running)
            if node.entry.scan == 'Rescan':
                node.entry.children = [lbl for lbl in node.entry.measurement.split(',')]
                node.updateChildren()
                node.hideChildren = True
            if index.column() == 0 and role == QtCore.Qt.EditRole:
                if node.entry.label != node.label:
                    if node.label != '':
                        del self.labelDict[node.label]
                        self.labelsChanged.emit(node.label, False)
                    node.label = copy.copy(node.entry.label)
                self.labelDict[node.entry.label] = node
                self.labelsChanged.emit(node.label, True)
            if value:
                self.valueChanged.emit(None)
            return value
        return False

    def setValue(self, index):
        self.updateRootNodes()

    def flags(self, index):
        node = self.nodeFromIndex(index)
        if index.column() == 1:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        else:
            if node.entry.scan == 'Scan':
                return (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled |
                        QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable if index.column()==0 else
                        QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable )
            elif node.entry.scan == 'Script' or node.entry.scan == 'Todo List':
                if index.column()==0:
                    return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | \
                           QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable
                elif index.column()==2 or index.column()==5:
                    return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                else:
                    return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            elif node.entry.scan == 'Rescan':
                if index.column()==0:
                    return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | \
                           QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable
                elif index.column()==2 or index.column()==5:
                    return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
                else:
                    return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

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
        self.updateRootNodes(True)
        return len(self.todolist)-1

    def dropMeasurement (self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.todolist.pop(row)
        self.endRemoveRows()
        self.updateRootNodes()

    def setTodolist(self, todolist):
        """Load a specified todo list"""
        self.beginResetModel()
        self.todolist = todolist
        self.rootNodes = self._rootNodes(init=True)
        self.endResetModel()
        if self.activeEntry is not None:
            self.setActiveItem(self.activeEntry, self.running)

    def choice(self, index):
        node = self.nodeFromIndex(index)
        return self.choiceLookup.get(index.column(), lambda row: [])(node)

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

