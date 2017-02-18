# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtCore

from modules import Expression
from externalParameter.persistence import DBPersist
from externalParameter.decimation import StaticDecimation
import time
from functools import partial
from collections import defaultdict

from modules.quantity import Q


class TodoListSettingsTableModel(QtCore.QAbstractTableModel):
    headerDataLookup = ['Name', 'Value']
    expression = Expression.Expression()
    edited = QtCore.pyqtSignal()
    def __init__(self, settings, globalDict, parent=None, *args): 
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.variables = settings
        self.globalDict = globalDict
        self.dataLookup = { (QtCore.Qt.DisplayRole, 0): lambda row: self.variables.keyAt(row),
                             (QtCore.Qt.DisplayRole, 1): lambda row: str(self.variables.at(row)),
                             (QtCore.Qt.EditRole, 0):    lambda row: self.variables.keyAt(row),
                             (QtCore.Qt.EditRole, 1):    lambda row: str(self.variables.at(row)),
                             }
        self.setDataLookup = { (QtCore.Qt.EditRole, 0): self.setDataName,
                               (QtCore.Qt.EditRole, 1): self.setDataValue,
                               }

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.variables) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None

    def setDataValue(self, index, value):
        logger = logging.getLogger(__name__)
        try:
            if type(value) == str:
                value = self.expression.evaluate(value, self.globalDict )
            name = self.variables.keyAt(index.row())
            self.variables[name] = value
            return True    
        except Exception:
            logger.exception("No match for {0}".format(value))
            return False
 
    def setDataName(self, index, value):
        try:
            strvalue = str(value).strip()
            self.variables.renameAt(index.row(), strvalue)
            return True    
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("No match for {0}".format(strvalue))
            return False
       
    def setData(self, index, value, role):
        result = self.setDataLookup.get((role, index.column()), lambda row, value: False)(index, value)
        if result:
            self.edited.emit()
        return result

    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None  # QtCore.QVariant()
            
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)            

    def getVariables(self):
        return self.variables
 
    def getVariableValue(self, name):
        return self.variables[name]
    
    def addSetting(self):
        if None not in self.variables:
            self.beginInsertRows(QtCore.QModelIndex(), len(self.variables), len(self.variables))
            self.variables[None] = Q(0)
            self.endInsertRows()
            self.edited.emit()
        return len(self.variables) - 1
        
    def dropSetting(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        name = self.variables.keyAt(row)
        self.variables.pop(name)
        self.endRemoveRows()
        self.edited.emit()
        return name
    
    def choice(self, index):
        if index.column()==0:
            return sorted(list(self.globalDict.keys()))
        return None
    
    def setSettings(self, settings):
        self.beginResetModel()
        self.variables = settings
        self.endResetModel()
