'''
Created on Jul 2, 2015

@author: Geoffrey Ji
'''
from PyQt5 import QtCore, QtGui

from modules.Expression import Expression
from modules.firstNotNone import firstNotNone
from modules.enum import enum

class AWGTableModel(QtCore.QAbstractTableModel):
    """Table model for displaying AWG variables"""
    headerDataLookup = ["Variable", "Value"]
    valueChanged = QtCore.pyqtSignal( object, object )
    expression = Expression()

    def __init__(self, settings, globalDict, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.settings = settings
        self.globalDict = globalDict
        self.defaultBG = QtGui.QColor(QtCore.Qt.white)
        self.textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
        self.column = enum('variable', 'value')
        self.defaultFontName = "Segoe UI"
        self.defaultFontSize = 9
        self.normalFont = QtGui.QFont(self.defaultFontName, self.defaultFontSize, QtGui.QFont.Normal)
        self.boldFont = QtGui.QFont(self.defaultFontName, self.defaultFontSize, QtGui.QFont.Bold)

        self.dataLookup = {
            (QtCore.Qt.DisplayRole, self.column.variable): lambda row: self.settings.varDict.keyAt(row),
            (QtCore.Qt.DisplayRole, self.column.value): lambda row: str(self.settings.varDict.at(row)['value']),
            (QtCore.Qt.FontRole, self.column.variable): lambda row: self.boldFont if self.settings.varDict.keyAt(row).startswith('Duration') else self.normalFont,
            (QtCore.Qt.FontRole, self.column.value): lambda row: self.boldFont if self.settings.varDict.keyAt(row).startswith('Duration') else self.normalFont,
            (QtCore.Qt.EditRole, self.column.value): lambda row: firstNotNone( self.settings.varDict.at(row)['text'], str(self.settings.varDict.at(row)['value'])),
            (QtCore.Qt.BackgroundColorRole, self.column.value): lambda row: self.defaultBG if self.settings.varDict.at(row)['text'] is None else self.textBG,
            (QtCore.Qt.ToolTipRole, self.column.value): lambda row: self.settings.varDict.at(row)['text'] if self.settings.varDict.at(row)['text'] else None
        }
        self.setDataLookup =  { 
            (QtCore.Qt.EditRole, self.column.value): self.setValue,
            (QtCore.Qt.UserRole, self.column.value): self.setText
        }
        
    def setValue(self, index, value):
        row = index.row()
        name = self.settings.varDict.keyAt(row)
        var = self.settings.varDict.at(row)
        var['value'] = value
        self.valueChanged.emit(name, value)
        return True
    
    def setText(self, index, value):
        row = index.row()
        self.settings.varDict.at(row)['text'] = value
        return True
    
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.settings.varDict)
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
    
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None

    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled if index.column()==self.column.variable else QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
            elif (orientation == QtCore.Qt.Vertical):
                return str(section)
        return None  # QtCore.QVariant()
    
    def evaluate(self, name):
        for (varName, varValueTextDict) in list(self.settings.varDict.items()):
            expr = varValueTextDict['text']
            if expr is not None:
                value = self.expression.evaluateAsMagnitude(expr, self.globalDict)
                self.settings.varDict[varName]['value'] = value   # set saved value to make this new value the default
                modelIndex = self.createIndex(self.settings.varDict.index(varName), self.column.value)
                self.dataChanged.emit(modelIndex, modelIndex)
                self.valueChanged.emit(varName, value)