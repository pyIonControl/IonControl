# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui

class TodoListTreeModel(QtCore.QAbstractItemModel):
    valueChanged = QtCore.pyqtSignal( object )
    headerDataLookup = ['Scan', 'Measurement']
    def __init__(self, todolist, parent=None, *args): 
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractItemModel.__init__(self, parent, *args) 
        self.todolist = todolist
        self.dataLookup =  { (QtCore.Qt.DisplayRole, 0): lambda row: self.todolist[row].scan,
                             (QtCore.Qt.DisplayRole, 1): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 2): lambda row: self.todolist[row].scanSegment.start,
                             (QtCore.Qt.DisplayRole, 3): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 4): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 5): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 6): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 7): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 8): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.BackgroundColorRole, 0): lambda row: self.colorLookup[self.running] if self.activeRow==row else QtCore.Qt.white
                             }
        self.colorLookup = { True: QtGui.QColor(0xd0, 0xff, 0xd0), False: QtGui.QColor(0xff, 0xd0, 0xd0) }
        self.activeRow = None

    def setActiveRow(self, row, running=True):
        oldactive = self.activeRow
        self.activeRow = row
        self.running = running
        if row is not None:
            self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
        if oldactive is not None and oldactive!=row:
            self.dataChanged.emit( self.createIndex(oldactive, 0), self.createIndex(oldactive+1, 3) )

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.todolist) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 8
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def flags(self, index ):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None #QtCore.QVariant()
                        
    def moveRow(self, rows, up=True):
        if up:
            if len(rows)>0 and rows[0]>0:
                for row in rows:
                    self.todolist[row], self.todolist[row-1] = self.todolist[row-1], self.todolist[row]
                    self.dataChanged.emit( self.createIndex(row-1, 0), self.createIndex(row, 3) )
                return True
        else:
            if len(rows)>0 and rows[0]<len(self.todolist)-1:
                for row in rows:
                    self.todolist[row], self.todolist[row+1] = self.todolist[row+1], self.todolist[row]
                    self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
                return True
        return False

    def addMeasurement(self, todoListElement):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.todolist), len(self.todolist))
        self.todolist.append( todoListElement )
        self.endInsertRows()
        return len(self.todolist)-1
        
    def dropMeasurement (self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row )
        self.todolist.pop(row)
        self.endRemoveRows()
    
    
            
