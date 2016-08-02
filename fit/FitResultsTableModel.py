# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore


class FitResultsTableModel(QtCore.QAbstractTableModel):
    
    def __init__(self, config, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.dataLookup = { (QtCore.Qt.DisplayRole, 0): lambda row: self.fitfunction.results.at(row).name,
                            (QtCore.Qt.DisplayRole, 1): lambda row: self.fitfunction.results.at(row).definition,
                            (QtCore.Qt.DisplayRole, 2): lambda row: str(self.fitfunction.results.at(row).value),
                            }                           
        self.fitfunction = None
                         
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.fitfunction.results) if self.fitfunction else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 3
 
    def setFitfunction(self, fitfunction):
        self.beginResetModel()
        self.fitfunction = fitfunction
        self.endResetModel()
        
    def allDataChanged(self):
        pass
    
    def fitDataChanged(self):
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(self.rowCount(), 2))
 
    def startDataChanged(self):
        self.dataChanged.emit( self.createIndex(0, 2), self.createIndex(self.rowCount(), 2))
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def setData(self, index, value, role):
        if (role, index.column()) == (QtCore.Qt.CheckStateRole, 0): 
            self.fitfunction.parameterEnabled[index.row()] = value==QtCore.Qt.Checked
            return True
        if (role, index.column()) == (QtCore.Qt.EditRole, 2):
            self.fitfunction.startParameters[index.row()] = value
        return False
    
    def setValue(self, index, value):
        self.fitfunction.startParameters[index.row()] = value

    def flags(self, index ):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    headerDataLookup = ['Name', 'Definition', 'Value']
    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None #QtCore.QVariant()
    
    def saveConfig(self):
        pass
