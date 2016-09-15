# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
from modules.firstNotNone import firstNotNone


class PushVariableTableModel(QtCore.QAbstractTableModel):
    backgroundLookup = {1:QtGui.QColor(QtCore.Qt.green).lighter(175), 0:QtGui.QColor(QtCore.Qt.white), 
                        -1:QtGui.QColor(QtCore.Qt.red).lighter(175)}   
    pushChanged = QtCore.pyqtSignal()  
    def __init__(self, config, globalDict, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.dataLookup = { (QtCore.Qt.CheckStateRole, 0): lambda row:  QtCore.Qt.Checked if self.pushVariables.at(row).push else QtCore.Qt.Unchecked,
                            (QtCore.Qt.DisplayRole, 1): lambda row: str(self.pushVariables.at(row).destinationName),
                            (QtCore.Qt.DisplayRole, 2): lambda row: str(self.pushVariables.at(row).variableName),
                            (QtCore.Qt.DisplayRole, 3): lambda row: str(self.pushVariables.at(row).definition),
                            (QtCore.Qt.DisplayRole, 4): lambda row: str(self.pushVariables.at(row).value),                           
                            (QtCore.Qt.DisplayRole, 5): lambda row: str(self.pushVariables.at(row).minimum),
                            (QtCore.Qt.DisplayRole, 6): lambda row: str(self.pushVariables.at(row).maximum),
                            (QtCore.Qt.EditRole, 1): lambda row: self.pushVariables.at(row).destinationName,
                            (QtCore.Qt.EditRole, 2): lambda row: self.pushVariables.at(row).variableName,
                            (QtCore.Qt.EditRole, 3): lambda row: self.pushVariables.at(row).definition,
                            (QtCore.Qt.EditRole, 5): lambda row: firstNotNone( self.pushVariables.at(row).strMinimum, str(self.pushVariables.at(row).minimum)),
                            (QtCore.Qt.EditRole, 6): lambda row: firstNotNone( self.pushVariables.at(row).strMaximum, str(self.pushVariables.at(row).maximum)),
                            (QtCore.Qt.BackgroundRole, 4): lambda row: self.backgroundLookup[self.pushVariables.at(row).valueStatus],  
                            (QtCore.Qt.BackgroundRole, 5): lambda row: self.backgroundLookup[self.pushVariables.at(row).hasStrMinimum],  
                            (QtCore.Qt.BackgroundRole, 6): lambda row: self.backgroundLookup[self.pushVariables.at(row).hasStrMaximum]  

                            }                           
        self.setDataLookup =   { (QtCore.Qt.EditRole, 1): self.setDataDestinationName,
                                 (QtCore.Qt.EditRole, 2): self.setDataVariableName,
                                 (QtCore.Qt.UserRole, 3): self.setDataDefinition,
                                 (QtCore.Qt.EditRole, 5): self.setDataMinimum,
                                 (QtCore.Qt.EditRole, 6): self.setDataMaximum,
                                 (QtCore.Qt.UserRole, 5): self.setDataStrMinimum,
                                 (QtCore.Qt.UserRole, 6): self.setDataStrMaximum,
                                 (QtCore.Qt.CheckStateRole, 0): self.setDataPush }
        self.pushVariables = None
        self.fitfunction = None
        self.pushDestinations = dict()
        self.globalDict = globalDict
                         
    def localReplacementDict(self):
        return self.fitfunction.replacementDict()
                         
    def updateDestinations(self, destinations):
        self.pushDestinations = destinations
        
    def choice(self, index):
        if index.column()==1:
            return sorted(self.pushDestinations.keys())
        elif index.column()==2:
            return sorted(list(self.pushDestinations[self.pushVariables.at(index.row()).destinationName].keys()))
        return None
                         
    def setDataPush(self, row, value):
        self.pushVariables.at(row).push = value==QtCore.Qt.Checked
        return True
        
    def setDataVariableName(self, row, value):
        value =  str(value)
        if value:
            self.pushVariables.at(row).variableName = value
            self.pushVariables.renameAt(row, self.pushVariables.at(row).key)
            return True
        return False

    def setDataDestinationName(self, row, value):
        value =  str(value)
        if value:
            self.pushVariables.at(row).destinationName = value
            self.pushVariables.renameAt(row, self.pushVariables.at(row).key)
            return True
        return False

    def setDataDefinition(self, row, value):
        value =  str(value)
        if value:
            self.pushVariables.at(row).definition = value
            replacementDict = self.fitfunction.replacementDict()
            replacementDict.update( self.globalDict )
            self.pushVariables.at(row).evaluate(replacementDict)
            self.dataChanged.emit( self.createIndex(row, 3), self.createIndex(row, 3))
            return True
        return False
        
    def setDataMinimum(self, row, value):
        self.pushVariables.at(row).minimum = value
        return True
        
    def setDataMaximum(self, row, value):
        self.pushVariables.at(row).maximum = value
        return True
                         
    def setDataStrMinimum(self, row, value):
        self.pushVariables.at(row).strMinimum = value
        return True
        
    def setDataStrMaximum(self, row, value):
        self.pushVariables.at(row).strMaximum = value
        return True
                         
    def addVariable(self, pushVariable ):
        if self.pushVariables is not None and pushVariable.key not in self.pushVariables:
            self.beginInsertRows(QtCore.QModelIndex(), len(self.pushVariables), len(self.pushVariables))
            self.pushVariables[pushVariable.key] = pushVariable
            self.endInsertRows()
             
    def removeVariable(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        self.pushVariables.popAt(index)
        self.endRemoveRows()
        
                         
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.pushVariables) if self.pushVariables else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 7

    def update(self):
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(self.rowCount(), 7) )
 
    def setPushVariables(self, pushVariables, fitfunction):
        self.beginResetModel()
        self.pushVariables = pushVariables
        self.fitfunction = fitfunction
        self.endResetModel()
        
    def allDataChanged(self):
        pass
    
    def fitDataChanged(self, extraDict=None ):
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(self.rowCount(), 3))
 
    def startDataChanged(self):
        pass
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def setData(self, index, value, role):
        result = self.setDataLookup.get((role, index.column()), lambda row, value: None)(index.row(), value)
        if result:
            self.pushChanged.emit()
        return result
    
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)

    def flags(self, index ):
        if index.column()==0:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
        if index.column() in [1, 2, 3, 5, 6]:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    headerDataLookup = ['Push', 'Destination', 'Variable', 'Definition', 'Value', 'Min Accept', 'Max Accept']
    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None #QtCore.QVariant()
    
    def saveConfig(self):
        pass
