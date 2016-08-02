# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore
from modules.firstNotNone import firstNotNone


class GenericTableModel(QtCore.QAbstractTableModel):
    def __init__(self, config, data, objectName, columnHeaders, printers=None, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.objectName = objectName
        self.data = data
        self.columnHeaders = columnHeaders
        self.printers = printers if printers else [None for _ in range(len(self.columnHeaders))]
                        
    def setDataTable(self, data):
        self.beginResetModel()
        self.data = data
        self.endResetModel()
                        
    def add(self, key, value ):
        if key not in self.data:
            self.beginInsertRows(QtCore.QModelIndex(), len(self.data), len(self.data))
            self.data[key] = value
            self.endInsertRows()
             
    def remove(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        self.data.popAt(index)
        self.endRemoveRows()
                               
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.data) if self.data else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return len(self.columnHeaders) 

    def data(self, index, role): 
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                printer = firstNotNone( self.printers[index.column()], str )
                return printer(self.data[index.row()][index.column()])
        return None
        
    def flags(self, index ):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.columnHeaders[section]
        return None #QtCore.QVariant()
    