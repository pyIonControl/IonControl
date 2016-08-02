# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore

from modules.SequenceDict import SequenceDict


class ExternalParameterTableModel( QtCore.QAbstractTableModel ):
    enableChanged = QtCore.pyqtSignal( object )
    headerDataLookup = [ 'E', 'Name', 'Class', 'Instrument' ]
    def __init__(self, parameterDict=None, classdict=None, parent=None):
        super(ExternalParameterTableModel, self).__init__(parent)
        self.parameterDict = parameterDict if parameterDict else SequenceDict()
        self.classdict = classdict
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 2):    lambda row: self.parameterDict.at(row).className,
                             (QtCore.Qt.DisplayRole, 3):    lambda row: self.parameterDict.at(row).instrument,
                             (QtCore.Qt.DisplayRole, 1):    lambda row: self.parameterDict.at(row).name,
                             (QtCore.Qt.EditRole, 2):    lambda row: self.parameterDict.at(row).className,
                             (QtCore.Qt.EditRole, 3):    lambda row: self.parameterDict.at(row).instrument,
                             (QtCore.Qt.EditRole, 1):    lambda row: self.parameterDict.at(row).name,
                             (QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.parameterDict.at(row).enabled else QtCore.Qt.Unchecked }
        self.setDataLookup = { (QtCore.Qt.CheckStateRole, 0): self.setEnabled,
                               (QtCore.Qt.EditRole, 3): self.setInstrument,
                               (QtCore.Qt.EditRole, 1): self.setName,
                               (QtCore.Qt.EditRole, 2): self.setClassName  }
        
    def choice(self, index):
        if index.column()==2:
            return list(self.classdict.keys())
        elif index.column()==3:
            className = str(self.parameterDict.at(index.row()).className)
            myclass = self.classdict[className]
            if hasattr( myclass, 'connectedInstruments'):
                return sorted(myclass.connectedInstruments()) 
        return None
    
    def comboBoxEditable(self, index):
        return index.column()==3
    
    def setParameterDict(self, parameterDict):
        self.beginResetModel()
        self.parameterDict = parameterDict
        self.endResetModel()
        
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.parameterDict) if self.parameterDict else 0
    
    def columnCount(self,  parent=QtCore.QModelIndex()):
        return 4
    
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)
                
    def setValue(self, index, value):
        return self.setData(index, value, QtCore.Qt.EditRole)
                
    def setEnabled(self, index, value):
        self.parameterDict.at(index.row()).enabled = value==QtCore.Qt.Checked
        self.enableChanged.emit( str(self.parameterDict.at(index.row()).name) )
        return True
        
    def setInstrument(self, index, value):
        if not self.parameterDict.at(index.row()).enabled:
            self.parameterDict.at(index.row()).instrument = str(value)
            return True
        return False
        
    def setName(self, index, value):
        if not self.parameterDict.at(index.row()).enabled:
            newname = value
            self.parameterDict.renameAt(index.row(), newname)
            self.parameterDict.at(index.row()).name = newname
            return True
        return False
        
    def setClassName(self, index, value):
        if not self.parameterDict.at(index.row()).enabled:
            self.parameterDict.at(index.row()).className = str(value)
            return True
        return False
        
    def flags(self, index ):
        if index.column()==0:
            return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled if self.parameterDict.at(index.row()).enabled else QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
    
    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Vertical): 
                return str(section)
            elif (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None 
    
    def moveRow(self, rows, up=True):
        if up:
            if len(rows)>0 and rows[0]>0:
                for row in rows:
                    self.parameterDict.swap(row, row-1 )
                    self.dataChanged.emit( self.createIndex(row-1, 0), self.createIndex(row, 3) )
                return True
        else:
            if len(rows)>0 and rows[0]<len(self.parameterDict)-1:
                for row in rows:
                    self.parameterDict.swap(row, row+1 )
                    self.dataChanged.emit( self.createIndex(row, 0), self.createIndex(row+1, 3) )
                return True
        return False
    
