# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from PyQt5 import QtCore, QtGui
from pulseProgram.VariableDictionary import CyclicDependencyException


class VariableTableModel(QtCore.QAbstractTableModel):
    flagsLookup = [ QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable |  QtCore.Qt.ItemIsEnabled,
                    QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled,
                    QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled,
                    QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled ]
    headerDataLookup = ['use', 'variable', 'value', 'evaluated']
    contentsChanged = QtCore.pyqtSignal()
    def __init__(self, variabledict=None, config=dict(), contextName=None, parent=None, contextHasParent=False, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.link_icons = {True: QtGui.QIcon('ui/icons/link.png'), False: QtGui.QIcon('ui/icons/broken_link.png')}
        self.contextHasParent = contextHasParent
        self.variabledict = variabledict if variabledict is not None else dict()
        self.normalFont = QtGui.QFont("MS Shell Dlg 2", -1, QtGui.QFont.Normal )
        self.boldFont = QtGui.QFont("MS Shell Dlg 2", -1, QtGui.QFont.Bold )
        self.contextName = contextName
        self.config = config
        self.contextBoldSets = self.config.get("VariableTableModel.BoldContext", dict() )
        self.contextColorDicts = self.config.get("VariableTableModel.ColorContext", dict() )
        self.contextBoldSets.setdefault( contextName, set() )
        self.contextColorDicts.setdefault( contextName, dict() )
        self.boldSet = self.contextBoldSets[self.contextName]
        self.colorDict = self.contextColorDicts[self.contextName]
        self.dataLookup = {  (QtCore.Qt.CheckStateRole,0): lambda var: QtCore.Qt.Checked if var.enabled else QtCore.Qt.Unchecked,
                             (QtCore.Qt.DisplayRole,1):    lambda var: var.name,
                             (QtCore.Qt.DecorationRole, 1): lambda var: self.link_icons[var.useParentValue] if var.hasParent else None,
                             (QtCore.Qt.DisplayRole,2):    lambda var: str(var.strvalue if hasattr(var,'strvalue') else var.value),
                             (QtCore.Qt.BackgroundColorRole,0): lambda var: self.getBackgroundColor(var, 0),
                             (QtCore.Qt.BackgroundColorRole,1): lambda var: self.getBackgroundColor(var, 1),
                             (QtCore.Qt.BackgroundColorRole,2): lambda var: self.getBackgroundColor(var, 2),
                             (QtCore.Qt.BackgroundColorRole,3): lambda var: self.getBackgroundColor(var, 3),
                             (QtCore.Qt.ToolTipRole,2):    lambda var: var.strerror if hasattr(var,'strerror') and var.strerror else None,
                             (QtCore.Qt.DisplayRole,3):    lambda var: str(var.outValue()),
                             (QtCore.Qt.EditRole,2):       lambda var: str(var.strvalue if hasattr(var,'strvalue') else var.value),
                             (QtCore.Qt.FontRole,1): lambda var: self.boldFont if var.name in self.boldSet else self.normalFont,
                             }
        self.setDataLookup ={    (QtCore.Qt.CheckStateRole, 0): self.setVarEnabled,
                                 (QtCore.Qt.EditRole, 2):       self.setDataValue,
                                }

    def setContextHasParent(self, contextHasParent):
        self.contextHasParent = contextHasParent
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0, self.rowCount()))

    def getBackgroundColor(self, var, col):
        if col==2:
            if hasattr(var,'strerror') and var.strerror:
                return QtGui.QColor( 255, 200, 200)
            elif not hasattr(var, 'strvalue'):
                return QtGui.QColor(200, 200, 255)
        if var.name in self.colorDict:
            r = self.colorDict[var.name]['r']
            g = self.colorDict[var.name]['g']
            b = self.colorDict[var.name]['b']
            return QtGui.QColor(r,g,b)
        if var.hasParent and var.useParentValue:
            if col == 1 or col == 2 or var.enabled:
                return QtGui.QColor(190, 190, 190)

    def setVariables(self, variabledict, contextName ):
        self.beginResetModel()
        self.variabledict = variabledict
        self.contextName = contextName
        self.contextBoldSets.setdefault( contextName, set() )
        self.contextColorDicts.setdefault( contextName, dict() )
        self.boldSet = self.contextBoldSets[self.contextName]
        self.colorDict = self.contextColorDicts[self.contextName]
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.variabledict) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 4
 
    def data(self, index, role): 
        if index.isValid():
            var = self.variabledict.at(index.row())
            return self.dataLookup.get((role, index.column()), lambda var: None)(var)
        return None
        
    def setDataValue(self, index, value):
        try:
            updatednames = self.variabledict.setStrValueIndex(index.row(), value)
            for name in updatednames:
                index = self.variabledict.index(name)
                self.dataChanged.emit( self.createIndex(index, 0), self.createIndex(index, 4) )
            self.contentsChanged.emit()
            return True
        except CyclicDependencyException as e:
            logger = logging.getLogger(__name__)
            logger.error( "Cyclic dependency {0}".format(str(e)) )
            return False           
        except KeyError as e:
            logger = logging.getLogger(__name__)
            logger.error("Expression '{0}' cannot be evaluated {1}".format(value, str(e)))
            return False
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error("No match for '{0}' error '{1}'".format(value, str(e)))
            return False
        
    def recalculateDependent(self, name):
        updatednames = self.variabledict.recalculateDependent(name)
        for name in updatednames:
            index = self.variabledict.index(name)
            self.dataChanged.emit( self.createIndex(index, 0), self.createIndex(index, 4) )
        
    def setDataEncoding(self, index, value):
        self.variabledict.setEncodingIndex(index.row(), value)
        return True
        
    def setVarEnabled(self, index, value):
        self.variabledict.setEnabledIndex(index.row(), value == QtCore.Qt.Checked)
        self.dataChanged.emit( self.createIndex(index.row(), 0), self.createIndex(index.row(), 4) )
        self.recalculateDependent(self.variabledict.keyAt(index.row()))
        self.contentsChanged.emit()
        return True      

    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)

    def flags(self, index ):
        return self.flagsLookup[index.column()]

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None #QtCore.QVariant()
        
    def saveConfig(self):
        self.config["VariableTableModel.BoldContext"] = self.contextBoldSets
        self.config["VariableTableModel.ColorContext"] = self.contextColorDicts
        
    def toggleBold(self, index):
        key = self.variabledict.keyAt(index.row())
        if key in self.boldSet:
            self.boldSet.remove(key)
        else:
            self.boldSet.add(key)
        self.dataChanged.emit( self.createIndex(index.row(), 1), self.createIndex(index.row(), 1) )
    
    def setBackgroundColor(self, index, color):
        row = index.row()
        key = self.variabledict.keyAt(row)
        self.colorDict[key] = {'r':color.red(), 'g':color.green(), 'b':color.blue()}
        topLeftIndex = self.createIndex(row, 0)
        bottomRightIndex = self.createIndex(row, self.columnCount()-1)
        self.dataChanged.emit(topLeftIndex, bottomRightIndex)

    def removeBackgroundColor(self, index):
        row = index.row()
        key = self.variabledict.keyAt(row)
        if key in self.colorDict:
            self.colorDict.pop(key)
        topLeftIndex = self.createIndex(row, 0)
        bottomRightIndex = self.createIndex(row, self.columnCount()-1)
        self.dataChanged.emit(topLeftIndex, bottomRightIndex)

    def onClicked(self, index):
        self.dataChanged.emit(self.createIndex(index.row(), 0), self.createIndex(index.row(), self.columnCount() - 1))

