# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore

class ScanNameTableModel(QtCore.QAbstractTableModel):
    scanNameFilterChanged = QtCore.pyqtSignal(object)
    headerDataLookup = ['Show', 'Name' ]
    def __init__(self, scanNames, container=None, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.container = container  
        # scanNames are given as a SortedDict
        self.scanNames = scanNames
        self.container.scanNamesChanged.subscribe( self.setScanNames )
        self.dataLookup = {  (QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.scanNames.at(row) else QtCore.Qt.Unchecked,
                             (QtCore.Qt.DisplayRole, 1): lambda row: str(self.scanNames.keyAt(row))
                              }

    def setScanNames(self, event):
        self.beginResetModel()
        self.scanNames = event.scanNames
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.scanNames) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
    
    def setData(self, index, value, role):
        if role==QtCore.Qt.CheckStateRole and index.column()==0:
            self.scanNames.setAt(index.row(), value == QtCore.Qt.Checked)
            self.scanNameFilterChanged.emit( self.scanNames)
            return True
        return False
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable if index.column()==0 else QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None  # QtCore.QVariant()
    
    def showAll(self, show=False, showOnlyThese=None):
        if showOnlyThese is not None:
            showthis = lambda x: x in showOnlyThese
        else:
            showthis = lambda x: show
        for row in range(len(self.scanNames)):
            self.scanNames.setAt(row, showthis(row))
        self.scanNameFilterChanged.emit(self.scanNames)
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0, len(self.scanNames)))
       
