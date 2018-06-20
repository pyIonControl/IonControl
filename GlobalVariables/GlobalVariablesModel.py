# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtCore, QtGui, QtWidgets
from modules import Expression
from modules.MagnitudeParser import isIdentifier
from persist.ValueHistory import HistoryException
from uiModules.CategoryTree import CategoryTreeModel, nodeTypes
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.enum import enum
from modules.quantity import Q
from .GlobalVariable import GlobalVariable
from expressionFunctions.ExprFuncDecorator import ExprFunUpdate

class GridDelegateMixin(object):
    """Contains methods for drawing a grid and setting the size in a view. Used as part of a delegate in a CategoryTreeView."""
    gridColor = QtGui.QColor(215, 215, 215, 255) #light gray
    def paint(self, painter, option, index):
        """Draw the grid if the node is a data node"""
        model = index.model()
        if model.nodeFromIndex(index).nodeType==nodeTypes.data and model.showGrid:
            painter.save()
            painter.setPen(self.gridColor)
            painter.drawRect(option.rect)
            painter.restore()
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)


class MagnitudeSpinBoxGridDelegate(MagnitudeSpinBoxDelegate, GridDelegateMixin):
    """Same as MagnitudeSpinBoxDelegate, but with a grid and different default size"""
    paint = GridDelegateMixin.paint


class GridDelegate(QtWidgets.QStyledItemDelegate, GridDelegateMixin):
    """Same as the default delegate, but with a grid and different default size"""
    paint = GridDelegateMixin.paint


class GlobalVariablesModel(CategoryTreeModel):
    """Model for global variables.

    Attributes:
        valueChanged (PyQt signal): emitted whenever the value of any global changes
        globalRemoved (PyQt signal): emitted whenever a global is removed

    Args:
        _globalDict_ (dict[name:GlobalVariable]): initial dict of global variables to display
    """
    valueChanged = QtCore.pyqtSignal(object)
    globalRemoved = QtCore.pyqtSignal()
    expression = Expression.Expression()
    def __init__(self, config, _globalDict_, parent=None):
        super(GlobalVariablesModel, self).__init__(list(_globalDict_.values()), parent)
        self.config = config
        self._globalDict_ = _globalDict_
        self.columnNames = ['name', 'value']
        self.numColumns = len(self.columnNames)
        self.column = enum(*self.columnNames)
        self.headerLookup.update({
            (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, self.column.name): "Name",
            (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, self.column.value): "Value"
            })
        self.dataLookup.update({
            (QtCore.Qt.DisplayRole, self.column.name): lambda node: node.content.name,
            (QtCore.Qt.DisplayRole, self.column.value): lambda node: format(node.content.value),
            (QtCore.Qt.EditRole, self.column.name): lambda node: node.content.name,
            (QtCore.Qt.EditRole, self.column.value): lambda node: format(node.content.value)
            })
        self.setDataLookup.update({
            (QtCore.Qt.EditRole, self.column.name): self.setName,
            (QtCore.Qt.EditRole, self.column.value): self.setValue
            })
        self.flagsLookup = {
            self.column.name: QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled,
            self.column.value: QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
            }
        self.allowReordering = True
        self.allowDeletion = True
        self.showGrid = True
        self.connectAllVariableSignals()

    def connectAllVariableSignals(self):
        """connect all variable valueChanged signals to the model's onValueChanged slot"""
        ExprFunUpdate.dataChanged.connect(self.onFunctionChanged)
        for item in list(self._globalDict_.values()):
            try:
                item.valueChanged.connect(self.onValueChanged, QtCore.Qt.UniqueConnection)
            except:
                pass

    def endResetModel(self):
        super(GlobalVariablesModel, self).endResetModel()
        self.connectAllVariableSignals()

    def onValueChanged(self, name, value, origin):
        node = self.nodeFromContent(self._globalDict_[name])
        ind = self.indexFromNode(node, col=self.column.value)
        if origin != 'gui':
            self.dataChanged.emit(ind, ind)
        self.valueChanged.emit(name)

    def onFunctionChanged(self, name):
        self.valueChanged.emit(name)

    def sort(self, column, order):
        """sort the tree"""
        if column==self.column.name:
            self.beginResetModel()
            self.sortChildren(self.root)
            self.endResetModel()

    def sortChildren(self, node):
        """Recursively sort tree below 'node' """
        node.children.sort(key=self.nodeSortKey)
        for child in node.children:
            self.sortChildren(child)

    @staticmethod
    def nodeSortKey(node):
        """Sort key that puts categories before data"""
        nodeName = getattr(node.content, 'name', node.content)
        return nodeName if node.children==[] else '0_'+nodeName

    def setName(self, index, value):
        """Change the name of a global variable"""
        node = self.nodeFromIndex(index)
        var = node.content
        newName = value.strip()
        if var.name != newName:
            if not isIdentifier(newName):
                logging.getLogger(__name__).warning("'{0}' is not a valid identifier".format(newName))
                return False
            if newName in self._globalDict_:
                logging.getLogger(__name__).warning("'{0}' already exists".format(newName))
                return False
            del self._globalDict_[var.name]
            try:
                var.name = newName
            except HistoryException as e:
                logging.getLogger(__name__).warning(str(e))
            self._globalDict_[newName] = var
            return True
        return True

    def setValue(self, index, value):
        """Change the value of a global variable"""
        name = self.nodeFromIndex(index).content.name
        oldValue = self._globalDict_[name].value
        self._globalDict_[name].value = (value, "gui")

    def addVariable(self, name, categories=None):
        """Add a new global variable"""
        if name=="":
            name = 'NewGlobalVariable'
        if name not in self._globalDict_ and isIdentifier(name):
            newGlobal = GlobalVariable(name, Q(0))
            newGlobal.categories = categories
            newGlobal.valueChanged.connect(self.onValueChanged)
            node = self.addNode(newGlobal)
            self._globalDict_[name] = newGlobal
            return node

    def addNode(self, content, name=None):
        """makes sure nodeID property of global variable is set whenever a node is added"""
        node = super(GlobalVariablesModel, self).addNode(content, name)
        node.content.nodeID = node.id #store ID to tree node in global variable itself for fast lookup
        return node

    def removeNode(self, node, useModelReset=False):
        """Remove the global from the tree and from the globalDict"""
        if node.nodeType==nodeTypes.data:
            parent = node.parent
            var = node.content
            deletedID = super(GlobalVariablesModel, self).removeNode(node, useModelReset)
            del self._globalDict_[var.name]
            del self.config["GlobalVariables.dict.{}".format(var.name)]
            self.removeAllEmptyParents(parent)
            self.globalRemoved.emit()
        elif node.nodeType==nodeTypes.category and node.children==[]: #deleting whole categories of global variables with one keystroke is a bad idea
            deletedID = super(GlobalVariablesModel, self).removeNode(node, useModelReset)
        else:
            deletedID = None
        return deletedID

    def changeCategory(self, node, categories=None, deleteOldIfEmpty=True):
        """change the global's category, and update the nodeID and categories attributes"""
        node, oldDeleted, deletedCategoryNodeIDs = super(GlobalVariablesModel, self).changeCategory(node, categories, deleteOldIfEmpty)
        #update global variable to reflect category change
        var = node.content
        var.nodeID = node.id
        var.categories = categories
        return node, oldDeleted, deletedCategoryNodeIDs

    def update(self, updlist):
        """Update the global variables based on updlist"""
        for destination, name, value in updlist:
            value = Q(value)
            if destination=='Global' and name in self._globalDict_:
                oldValue = self._globalDict_[name].value
                if value.dimensionality != oldValue.dimensionality or value != oldValue:
                    var = self._globalDict_[name]
                    var.value = value
                    node = self.nodeFromContent(var)
                    ind = self.indexFromNode(node, col=self.column.value)
                    self.dataChanged.emit(ind, ind)

    def nodeFromContent(self, content):
        """Get the corresponding tree node from a global variable"""
        return self.nodeDict[content.nodeID]