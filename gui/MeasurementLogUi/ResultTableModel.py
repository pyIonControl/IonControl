# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore

class ResultTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal(object)
    headerDataLookup = ['Name', 'Value', 'Bottom', 'Top' ]
    def __init__(self, results, container=None, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.container = container
        # results are given as a list
        self.results = results
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda row: self.results[row].name,
                             (QtCore.Qt.DisplayRole, 1): lambda row: str(self.results[row].value),
                             (QtCore.Qt.DisplayRole, 2): lambda row: str(self.results[row].bottom) if self.results[row].bottom is not None else None,
                             (QtCore.Qt.DisplayRole, 3): lambda row: str(self.results[row].top) if self.results[row].top is not None else None
                             }

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.results) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 4
 
    def setResults(self, results):
        self.beginResetModel()
        self.results = results
        self.endResetModel()
        
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
            elif (orientation == QtCore.Qt.Vertical):
                return self.results[section].id
        return None  # QtCore.QVariant()
                
    def sort(self, column, order):
        if column == 0 and self.variables:
            self.results.sort(reverse=order == QtCore.Qt.DescendingOrder)
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.variables) - 1, 1))
            
