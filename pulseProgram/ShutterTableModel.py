# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools

from PyQt5 import QtCore, QtGui


class ShutterTableModel(QtCore.QAbstractTableModel):
    contentsChanged = QtCore.pyqtSignal()
    def __init__(self, shutterdict, channelNameData, size=32, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.shutterdict = shutterdict
        self.channelNames, self.channelSignal = channelNameData
        self.channelSignal.dataChanged.connect( self.onHeaderChanged )
        self.size = size
        self.bitsLookup = sorted(channelNameData[0].defaultDict.keys())
        self.size = max(size, self.bitsLookup[-1] + 1) if self.bitsLookup else size

    def setShutterdict(self, shutterdict):
        self.beginResetModel()
        self.shutterdict = shutterdict
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.shutterdict) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return self.size
 
    def currentState(self, index):
        var, mask = self.shutterdict.at(index.row())
        mask = mask.data if mask else 0xffffffffffffffff
        value = var.data
        bit = 0x1<<(self.size-index.column()-1)
        if mask & bit:
            if value & bit:
                return 1
            else:
                return -1
        else:
            return 0
        
    def setState(self, index, state):
        bit = 0x1<<(self.size-index.column()-1)
        var, mask = self.shutterdict.at(index.row())
        if mask is not None:
            if state == 0:
                mask.data &= ~bit
            else:
                mask.data = (mask.data & ~bit) | bit
        if state == -1:
            var.data &= ~bit
        elif state == 1:
            var.data = (var.data & ~bit) | bit
        self.dataChanged.emit(index, index)
        self.contentsChanged.emit()
        
    def displayData(self, index):
        return str(self.currentState(index))
        
    colorLookup = { -1: QtGui.QColor(QtCore.Qt.red), 0: QtGui.QColor(QtCore.Qt.white), 1: QtGui.QColor(QtCore.Qt.green) }
    def displayDataColor(self, index):
        return self.colorLookup[self.currentState(index)]
        
    def displayToolTip(self, index):
        return "ToolTip"
  
    def data(self, index, role): 
        if index.isValid():
            return { #(QtCore.Qt.DisplayRole): functools.partial( self.displayData, index),
                     (QtCore.Qt.BackgroundColorRole): functools.partial( self.displayDataColor, index),
                     #(QtCore.Qt.ToolTipRole): functools.partial( self.displayToolTip, index )
                     }.get(role, lambda : None)()
        return None
        
    def flags(self, index ):
        return  QtCore.Qt.ItemIsEnabled 

    def onHeaderChanged(self, first, last):
        self.headerDataChanged.emit( QtCore.Qt.Horizontal, first, last )

    def headerData(self, section, orientation, role ):
        index = self.size-1-section
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal):
                if index in self.channelNames:
                    return self.channelNames[index]
                return index
            elif (orientation == QtCore.Qt.Vertical): 
                return self.shutterdict.at(section)[0].name
        return None #QtCore.QVariant()

    def onClicked(self, index):
        oldState = self.currentState(index)
        if self.shutterdict.at(index.row())[1] is not None:
            newState = (oldState+2)%3 -1
        else:
            newState = -oldState
        self.setState(index, newState)
        #print index.row(), index.column()
        
    def getVariables(self):
        returndict = dict()
        #print "Maskdict: ", self.maskdict
        for var, mask in list(self.shutterdict.values()):
            returndict[var.name] = var.data
            if mask is not None:
                returndict[mask.name] = mask.data
        return returndict