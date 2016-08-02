# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore
from persist.MeasurementLog import Parameter
from _functools import partial

class ParameterTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal(object)
    headerDataLookup = ['Space', 'Name', 'Value', 'Definition' ]
    def __init__(self, parameters, container=None, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.container = container 
        # parameters are given as a list
        self.parameters = parameters
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda row: self.parameters[row].space.name,
                             (QtCore.Qt.DisplayRole, 1): lambda row: self.parameters[row].name,
                             (QtCore.Qt.DisplayRole, 2): lambda row: str(self.parameters[row].value),
                             (QtCore.Qt.DisplayRole, 3): lambda row: self.parameters[row].definition,
                             (QtCore.Qt.EditRole, 1): lambda row: self.parameters[row].name,
                             (QtCore.Qt.EditRole, 2): lambda row: self.parameters[row].value,
                             (QtCore.Qt.EditRole, 3): lambda row: self.parameters[row].definition
                             }
        self.setDataLookup = { (QtCore.Qt.EditRole, 1): partial( self.setDataString, 'name' ),
                               (QtCore.Qt.EditRole, 2): partial( self.setDataValue, 'value' ),
                               (QtCore.Qt.EditRole, 3): partial( self.setDataString, 'definition' )
                               }
        
    def setDataString(self, field, row, value):
        setattr(self.parameters[row], field, value)
        self.parameters[row]._sa_instance_state.session.commit()
        return True
    
    def setDataValue(self, field, row, value):
        setattr( self.parameters[row], field, value )
        self.parameters[row]._sa_instance_state.session.commit()
        return True

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.parameters) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 4
 
    def setParameters(self, parameters):
        self.beginResetModel()
        self.parameters = parameters
        self.endResetModel()
        
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda row, value: False)(index.row(), value)       
    
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole )
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | (QtCore.Qt.ItemIsEditable if self.parameters[index.row()].manual and index.row()>0 else 0 )

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
            elif (orientation == QtCore.Qt.Vertical):
                return self.parameters[section].id
        return None  # QtCore.QVariant()
                
    def sort(self, column, order):
        if column == 0 and self.variables:
            self.parameters.sort(reverse=order == QtCore.Qt.DescendingOrder)
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.variables) - 1, 1))
            
    def addManualParameter(self):
        self.beginInsertRows( QtCore.QModelIndex(), len(self.parameters), len(self.parameters) )
        customSpace = self.container.getSpace('Manual')
        p = Parameter(name='Manual', space=customSpace, manual=True, value=0 )
        self.parameters.append( p )
        self.container.session.add( p )
        self.container.commit()
        self.endInsertRows()
        