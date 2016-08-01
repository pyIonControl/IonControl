# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
from pandas.compat.chainmap_impl import ChainMap


class CounterTableModel(QtCore.QAbstractTableModel):
    contentsChanged = QtCore.pyqtSignal()
    def __init__(self, counterdict, namedict, size=49, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.counterdict = counterdict
        self.size = size
        defaultChannelNames = ['Count {0}'.format(i) for i in range(24)]
        defaultChannelNames.extend( ['TS {0}'.format(i) for i in range(8)] )
        defaultChannelNames.extend( ['ADC {0}'.format(i) for i in range(8)] )
        defaultChannelNames.extend( ['PI {0}'.format(i) for i in range(8)] )
        defaultChannelNames.append( 'time Tick' )
        defaultChannelNames.append('id')
        self.channelNames = ChainMap( namedict, dict( ((index, name) for index, name in enumerate(defaultChannelNames)) ) )

    def setCounterdict(self, counterdict):
        self.beginResetModel()
        self.counterdict = counterdict
        self.endResetModel()
    
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.counterdict) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return self.size+1
 
    def currentState(self, index):
        data = self.counterdict.at(index.row()).data
        bit = 0x1<<(self.size-index.column())
        return bool( bit & data )
        
    def setState(self, index, state):
        bit = 0x1<<(self.size-index.column())
        var = self.counterdict.at(index.row())
        if state:
            var.data = (var.data & ~bit) | bit
        else:
            var.data &= ~bit
        self.dataChanged.emit(index, index)
        self.contentsChanged.emit()
        
    def currentId(self, index):
        var = self.counterdict.at(index.row())
        return var.data >> 56
    
    def setCurrentId(self, index, newid):
        var = self.counterdict.at(index.row())
        var.data = (var.data & 0xffffffffffffff) | ((newid & 0xff) << 56)
        
    def displayData(self, index):
        return str(self.currentState(index))
        
    def displayDataColor(self, index):
        if index.column()==0:
            return QtGui.QColor(QtCore.Qt.white)  
        return QtGui.QColor(QtCore.Qt.green) if self.currentState(index) else QtGui.QColor(QtCore.Qt.white)
  
    def data(self, index, role): 
        if index.isValid():
            if index.column()>0:
                if role == QtCore.Qt.BackgroundColorRole: 
                    return self.displayDataColor( index )
            elif index.column()==0:
                if role == QtCore.Qt.DisplayRole:
                    return str(self.currentId(index))
                elif role==QtCore.Qt.EditRole:
                    return self.currentId(index)
        return None
        
    def setData(self, index, value, role):
        if index.isValid() and index.column()==0 and role==QtCore.Qt.EditRole and 0<=value<256:
            self.setCurrentId(index, int(value))
            return True
        return False
            
    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)
        
    def flags(self, index ):
        return  QtCore.Qt.ItemIsEnabled if index.column()>0 else (QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.channelNames[self.size-section]
            elif (orientation == QtCore.Qt.Vertical): 
                return self.counterdict.at(section).name
        return None #QtCore.QVariant()

    def onClicked(self, index):
        if index.column()>0:
            self.setState(index, not self.currentState(index))
        
    def getVariables(self):
        myvariables = dict()
        for var in list(self.counterdict.values()):
            myvariables[var.name] = var.data
        return myvariables
