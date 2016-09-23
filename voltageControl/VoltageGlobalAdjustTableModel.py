
# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui

class VoltageGlobalAdjustTableModel(QtCore.QAbstractTableModel):
    headerDataLookup = ['Solution', 'Amplitude' ]
    def __init__(self, globalAdjustDict, globalDict, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.globalAdjustDict = globalAdjustDict  
        # scanNames are given as a SortedDict
        defaultBG = QtGui.QColor(QtCore.Qt.white)
        textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
        self.backgroundLookup = { True:textBG, False:defaultBG}
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda row: self.globalAdjustDict.keyAt(row),
                             (QtCore.Qt.DisplayRole, 1): lambda row: str(self.globalAdjustDict.at(row).value),
                             (QtCore.Qt.EditRole, 1): lambda row: self.globalAdjustDict.at(row).string,                            
                             (QtCore.Qt.BackgroundColorRole, 1): lambda row: self.backgroundLookup[self.globalAdjustDict.at(row).hasDependency],
                              }

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.globalAdjustDict) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
    
    def setData(self, index, value, role):
        if index.column()==1:
            if role==QtCore.Qt.EditRole:
                self.globalAdjustDict.at(index.row()).value = float(value) if not callable(value.m) else value.m
                return True
            if role==QtCore.Qt.UserRole:
                self.globalAdjustDict.at(index.row()).string = value
                return True
        return False
        
    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled  if index.column()==0 else QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None  # QtCore.QVariant()
                
    def setGlobalAdjust(self, globalAdjustDict ):
        self.beginResetModel()
        self.globalAdjustDict = globalAdjustDict
        self.endResetModel()

    def valueRecalcualted(self, name):
        index = self.createIndex(self.globalAdjustDict.index(name), 1)
        self.dataChanged.emit( index, index )
        
    def sort(self, column, order):
        if column == 0 and self.globalAdjustDict:
            self.globalAdjustDict.sort(reverse=order == QtCore.Qt.DescendingOrder)
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.globalAdjustDict) - 1, 1))
            
