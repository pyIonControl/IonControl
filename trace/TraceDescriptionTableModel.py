# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from PyQt5 import QtCore

class TraceDescriptionTableModel(QtCore.QAbstractTableModel):
    headerDataLookup = ['Name', 'Value']
    def __init__(self, parent=None, *args): 
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.description = None
        self.dataLookup =  { (QtCore.Qt.DisplayRole, 0): lambda row: self.description.keyAt(row),
                             (QtCore.Qt.DisplayRole, 1): lambda row: str(self.description.at(row)),
                             }

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.description) if self.description else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def flags(self, index ):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None #QtCore.QVariant()
            
    def sort(self, column, order ):
        if column==0 and self.description:
            self.description.sort(reverse=order==QtCore.Qt.DescendingOrder)
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.description) -1, 1))
            
    def moveRow(self, rows, up=True):
        if up:
            if len(rows)>0 and rows[0]>0:
                for row in rows:
                    self.description.swap(row, row-1 )
                    self.dataChanged.emit( self.createIndex(row-1, 0), self.createIndex(row, 3) )
                return True
        else:
            if len(rows)>0 and rows[0]<len(self.description)-1:
                for row in rows:
                    self.description.swap(row, row+1 )
                    self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
                return True
        return False
    
    def setDescription(self, description):
        self.beginResetModel()
        if self.description:
            self.description.dataChanged.disconnect()
        self.description = description
        self.description.sort()
        self.description.dataChanged.connect( self.onUpdate )
        self.endResetModel()
        
    def onUpdate(self):
        self.beginResetModel()
        self.endResetModel()
        
        