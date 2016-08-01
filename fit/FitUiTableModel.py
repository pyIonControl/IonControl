# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore

from modules.round import roundToNDigits, roundToStdDev
from modules.firstNotNone import firstNotNone
from PyQt5 import QtGui
from _functools import partial

def mystr(x):
    return '' if x is None else str(x)

class FitUiTableModel(QtCore.QAbstractTableModel):
    backgroundLookup = {True:QtGui.QColor(QtCore.Qt.green).lighter(175), False:QtGui.QColor(QtCore.Qt.white)}
    parametersChanged = QtCore.pyqtSignal()
    def __init__(self, config, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.dataLookup = { (QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.fitfunction.parameterEnabled[row] else QtCore.Qt.Unchecked,
                            (QtCore.Qt.DisplayRole, 1): lambda row: self.fitfunction.parameterNames[row],
                            (QtCore.Qt.DisplayRole, 2): lambda row: str(self.fitfunction.startParameters[row]),
                            (QtCore.Qt.DisplayRole, 3): lambda row: mystr(self.fitfunction.parameterBounds[row][0]),
                            (QtCore.Qt.DisplayRole, 4): lambda row: mystr(self.fitfunction.parameterBounds[row][1]),
                            (QtCore.Qt.EditRole, 2):    lambda row: firstNotNone( self.fitfunction.startParameterExpressions[row], str(self.fitfunction.startParameters[row])),
                            (QtCore.Qt.UserRole, 2):    lambda row: self.fitfunction.units[row] if self.fitfunction.units else None,
                            (QtCore.Qt.EditRole, 3):    lambda row: firstNotNone( self.fitfunction.parameterBoundsExpressions[row][0], self.fitfunction.parameterBounds[row][0], ""),
                            (QtCore.Qt.UserRole, 3):    lambda row: self.fitfunction.units[row] if self.fitfunction.units else None,
                            (QtCore.Qt.EditRole, 4):    lambda row: firstNotNone( self.fitfunction.parameterBoundsExpressions[row][1], self.fitfunction.parameterBounds[row][1], ""),
                            (QtCore.Qt.UserRole, 4):    lambda row: self.fitfunction.units[row] if self.fitfunction.units else None,
                            (QtCore.Qt.DisplayRole, 5): self.fitValue,
                            (QtCore.Qt.DisplayRole, 6): self.confidenceValue,
                            (QtCore.Qt.DisplayRole, 7): self.relConfidenceValue,
                            (QtCore.Qt.ToolTipRole, 2): lambda row: self.fitfunction.startParameterExpressions[row] if self.fitfunction.startParameterExpressions[row] is not None else None,
                            (QtCore.Qt.BackgroundRole, 2): lambda row: self.backgroundLookup[self.fitfunction.startParameterExpressions[row] is not None],
                            (QtCore.Qt.BackgroundRole, 3): lambda row: self.backgroundLookup[self.fitfunction.parameterBoundsExpressions[row][0] is not None],
                            (QtCore.Qt.BackgroundRole, 4): lambda row: self.backgroundLookup[self.fitfunction.parameterBoundsExpressions[row][1] is not None]  }
        self.setDataLookup = { (QtCore.Qt.CheckStateRole, 0): self.setParametersEnabled,
                               (QtCore.Qt.EditRole, 2): self.setStartParameters,
                               (QtCore.Qt.UserRole, 2): self.setStartParameterExpression,
                               (QtCore.Qt.EditRole, 3): partial( self.setParametersBound, 0) ,
                               (QtCore.Qt.UserRole, 3): partial( self.setParametersBoundsExpression, 0),
                               (QtCore.Qt.EditRole, 4): partial( self.setParametersBound, 1),
                               (QtCore.Qt.UserRole, 4): partial( self.setParametersBoundsExpression, 1) }
        self.fitfunction = None
        
    def update(self):
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(self.rowCount(), 5) )
        
    def relConfidenceValue(self, row):
        if self.fitfunction.parametersConfidence and len(self.fitfunction.parametersConfidence)>row and self.fitfunction.parameters[row] and self.fitfunction.parametersConfidence[row]:
            return "{0}%".format(roundToNDigits(100*self.fitfunction.parametersConfidence[row]/abs(self.fitfunction.parameters[row]), 2))
        return None
        
    def confidenceValue(self, row):
        if len(self.fitfunction.parametersConfidence)>row and self.fitfunction.parametersConfidence[row]:
            return str(roundToNDigits(self.fitfunction.parametersConfidence[row], 2))
        return None
    
    def fitValue(self, row):
        if self.fitfunction.parameters[row] is None:
            return None
        if not self.fitfunction.parametersConfidence[row]:
            return str(self.fitfunction.parameters[row])
        return repr(roundToStdDev(self.fitfunction.parameters[row], self.fitfunction.parametersConfidence[row], 2)) 
                 
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.fitfunction.parameters) if self.fitfunction else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 8
 
    def setFitfunction(self, fitfunction):
        self.beginResetModel()
        self.fitfunction = fitfunction
        if self.fitfunction and self.fitfunction.startParameterExpressions is None:
            self.fitfunction.startParameterExpressions = [None]*len(self.fitfunction.startParameters)
        if self.fitfunction and self.fitfunction.parameterBoundsExpressions is None:
            self.fitfunction.parameterBoundsExpressions = [[None, None] for _ in range(len(self.fitfunction.startParameters))]
        self.endResetModel()
        
    def allDataChanged(self):
        pass
    
    def fitDataChanged(self):
        self.dataChanged.emit( self.createIndex(0, 3), self.createIndex(self.rowCount(), 5))
 
    def startDataChanged(self):
        self.dataChanged.emit( self.createIndex(0, 2), self.createIndex(self.rowCount(), 2))
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def setData(self, index, value, role):
        result = self.setDataLookup.get((role, index.column()), lambda row, value: False)(index.row(), value)
        self.parametersChanged.emit()
        return result
    
    def setParametersEnabled(self, row, value):
        self.fitfunction.parameterEnabled[row] = value==QtCore.Qt.Checked
        return True
        
    def setStartParameters(self, row, value):
        self.fitfunction.startParameters[row] = value
        return True

    def setStartParameterExpression(self, row, value):
        self.fitfunction.startParameterExpressions[row] = str(value) if value is not None else None
        return True

    def setParametersBound(self, bound, row, value):
        self.fitfunction.parameterBounds[row][bound] = value
        return True
    
    def setParametersBoundsExpression(self, bound, row, value):
        self.fitfunction.parameterBoundsExpressions[row][bound] = str(value) if value else None
        return True

    def setValue(self, index, value):
        self.fitfunction.startParameters[index.row()] = value
        self.parametersChanged.emit()

    def flags(self, index ):
        return { 0: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled,
                 2: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable,
                 3: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable,
                 4: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable,
                 }.get(index.column(), QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

    headerDataLookup = ['Fit', 'Var', 'Start', 'min', 'max', 'Fit', 'StdError', 'Relative']
    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None #QtCore.QVariant()
    
    def saveConfig(self):
        pass
        