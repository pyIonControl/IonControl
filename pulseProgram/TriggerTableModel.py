# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools

from PyQt5 import QtCore, QtGui


class TriggerTableModel(QtCore.QAbstractTableModel):
    contentsChanged = QtCore.pyqtSignal()
    def __init__(self, triggerdict, channelNameData, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.triggerdict = triggerdict
        self.channelNames, self.channelSignal = channelNameData
        self.channelSignal.dataChanged.connect( self.onHeaderChanged )

    def setTriggerdict(self, triggerdict):
        self.beginResetModel()
        self.triggerdict = triggerdict
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.triggerdict) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 32
 
    def currentState(self, index):
        data = self.triggerdict.at(index.row()).data
        bit = 0x80000000>>index.column()
        return bool( bit & data )
        
    def setState(self, index, state):
        bit = 0x80000000>>index.column()
        var = self.triggerdict.at(index.row())
        if state:
            var.data = (var.data & ~bit) | bit
        else:
            var.data &= ~bit
        self.dataChanged.emit(index, index)
        self.contentsChanged.emit()
                
    def displayData(self, index):
        return str(self.currentState(index))
        
    def displayDataColor(self, index):
        return QtGui.QColor(QtCore.Qt.green) if self.currentState(index) else QtGui.QColor(QtCore.Qt.white)
  
    def data(self, index, role): 
        if index.isValid():
            return { #(QtCore.Qt.DisplayRole): functools.partial( self.displayData, index),
                     (QtCore.Qt.BackgroundColorRole): functools.partial( self.displayDataColor, index),
                     }.get(role, lambda : None)()
        return None
        
    def flags(self, index ):
        return  QtCore.Qt.ItemIsEnabled 

    def onHeaderChanged(self, first, last):
        self.headerDataChanged.emit( QtCore.Qt.Horizontal, first, last )        

    def headerData(self, section, orientation, role ):
        index = 31-section
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal):
                if index in self.channelNames:
                    return self.channelNames[index]
                return index
            elif (orientation == QtCore.Qt.Vertical): 
                return self.triggerdict.at(section).name
        return None #QtCore.QVariant()

    def onClicked(self, index):
        self.setState(index, not self.currentState(index))

    def getVariables(self):
        myvariables = dict()
        for var in list(self.triggerdict.values()):
            myvariables[var.name] = var.data
        return myvariables
