# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
from _functools import partial
import copy

class TodoListTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal( object )
    headerDataLookup = ['Enable', 'Scan type', 'Scan', 'Evaluation', 'Analysis']
    def __init__(self, todolist, parent=None, *args): 
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.todolist = todolist
        self.dataLookup =  { (QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.todolist[row].enabled else QtCore.Qt.Unchecked,
                             (QtCore.Qt.DisplayRole, 1): lambda row: self.todolist[row].scan,
                             (QtCore.Qt.DisplayRole, 2): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.DisplayRole, 3): lambda row: self.todolist[row].evaluation,
                             (QtCore.Qt.DisplayRole, 4): lambda row: self.todolist[row].analysis,
                             (QtCore.Qt.EditRole, 1): lambda row: self.todolist[row].scan,
                             (QtCore.Qt.EditRole, 2): lambda row: self.todolist[row].measurement,
                             (QtCore.Qt.EditRole, 3): lambda row: self.todolist[row].evaluation,
                             (QtCore.Qt.EditRole, 4): lambda row: self.todolist[row].analysis,
                             (QtCore.Qt.BackgroundColorRole, 1): lambda row: self.colorLookup[self.running] if self.activeRow==row else QtCore.Qt.white,
                             (QtCore.Qt.BackgroundColorRole, 0): lambda row: self.colorStopFlagLookup[self.todolist[row].stopFlag]
                             }
        self.setDataLookup ={ (QtCore.Qt.CheckStateRole, 0): self.setEntryEnabled,
                             (QtCore.Qt.EditRole, 1): partial( self.setString, 'scan' ),
                             (QtCore.Qt.EditRole, 2): partial( self.setString, 'measurement' ),
                             (QtCore.Qt.EditRole, 3): partial( self.setString, 'evaluation' ),
                             (QtCore.Qt.EditRole, 4): partial( self.setString, 'analysis' )
                             }
        self.colorLookup = { True: QtGui.QColor(0xd0, 0xff, 0xd0), False: QtGui.QColor(0xff, 0xd0, 0xd0) }
        self.colorStopFlagLookup = {True: QtGui.QColor( 0xcb, 0x4e, 0x28), False: QtCore.Qt.white}
        self.activeRow = None
        self.tabSelection = []
        self.measurementSelection = {}
        self.evaluationSelection = {}
        self.analysisSelection = {}
        self.choiceLookup = { 1: lambda row: list(self.measurementSelection.keys()),
                              2: lambda row: self.measurementSelection[self.todolist[row].scan],
                              3: lambda row: self.evaluationSelection[self.todolist[row].scan],
                              4: lambda row: self.analysisSelection[self.todolist[row].scan]}

    def setString(self, attr, index, value):
        setattr( self.todolist[index.row()], attr, str(value) )
        return True

    def setEntryEnabled(self, index, value):
        self.todolist[index.row()].enabled = value == QtCore.Qt.Checked
        return True      

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
        return 5
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
    
    def setData(self, index, value, role):
        if index.isValid():
            value = self.setDataLookup.get((role, index.column()), lambda index, value: None)(index, value)
            if value:
                self.valueChanged.emit( None )
            return value
        return False
       
    def flags(self, index ):
        return (QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable if index.column()==0 else 
                QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable )

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
    
    def setTodolist(self, todolist):
        self.beginResetModel()
        self.todolist = todolist
        self.endResetModel()
        
    def choice(self, index):
        return self.choiceLookup.get(index.column(), lambda row: [])(index.row())
    
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)

    def copy_rows(self, row_list):
        """ Copy a the rows given and append to the end of the TODO list.
        row_list :: [Int] List of rows to copy
        """
        for row_index in row_list:
            row_data = self.todolist[row_index]
            self.addMeasurement(copy.deepcopy(row_data))
            
        