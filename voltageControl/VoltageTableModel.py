# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


import operator
import sys
import logging

from PyQt5 import QtCore, QtGui


class VoltageTableModel(QtCore.QAbstractTableModel):
    def __init__(self, voltageBlender, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.blender = voltageBlender
        self.orderLookup = None
        #self.electrodes, self.aoNums, self.dsubNums, self.outputVoltage
        #arrange the ones in the voltage file first and in the same order
        #self.orderAsVoltageFile()
        self.lastElectrodeOrder = 0
        self.lastLength = 0
        self.voltagesOutOfRange = list()
        self.allVoltagesOkay = False
        
    def sort(self, column, order ):
        if (self.blender.electrodes):
            if column==0:
                self.lastElectrodeOrder = (self.lastElectrodeOrder +1 )% 4
                if self.lastElectrodeOrder==0:
                    self.orderLookup = list(range(len(self.blender.electrodes)))
                elif self.lastElectrodeOrder==1:
                    self.orderAsVoltageFile()
                elif self.lastElectrodeOrder in [2, 3]:
                    d = enumerate(self.blender.electrodes)
                    d = sorted( d, key=operator.itemgetter(1), reverse=True if self.lastElectrodeOrder==3 else False )
                    self.orderLookup = [operator.itemgetter(0)(t) for t in d]
            else:
                d = enumerate({ 0:self.blender.electrodes, 1:self.blender.outputVoltage, 2:self.blender.aoNums, 3:[int(val) for val in self.blender.dsubNums]}[column])
                d = sorted( d, key=operator.itemgetter(1), reverse=True if order==QtCore.Qt.DescendingOrder else False )
                self.orderLookup = [operator.itemgetter(0)(t) for t in d]
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.blender.electrodes) -1, 3))
        
    def electrodeIndex(self, name):  
        try:
            index = self.blender.electrodes.index(name)
        except Exception as e:
            raise type(e)(str(e) + " for x='{0}'".format(name)).with_traceback(sys.exc_info()[2])
        return index
        
    def orderAsVoltageFile(self):
        if self.blender.electrodes:
            self.orderLookup = list()
            allindices = [False]*len(self.blender.electrodes)
            for name in self.blender.tableHeader:
                index = self.electrodeIndex(name)
                self.orderLookup.append( index )
                allindices[index] = True
            for index, included in enumerate(allindices):
                if not included:
                    self.orderLookup.append( index )

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.blender.electrodes) if self.blender.electrodes is not None else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 4
 
    def onDataChanged(self, x1, y1, x2, y2):
        logger = logging.getLogger(__name__)
        logger.debug( "VoltageTableModel.onDataChanged {0} {1} {2} {3}".format(x1, y1, x2, y2) )
        newLength = len(self.blender.electrodes)
        if newLength>self.lastLength:
            self.beginInsertRows(QtCore.QModelIndex(), self.lastLength, newLength-1)
            self.endInsertRows()
            self.lastLength = newLength
        if self.orderLookup is None:
            self.orderLookup = list(range(newLength))
        self.voltagesOutOfRange = [False]*newLength
        self.allVoltagesOkay = True
        self.dataChanged.emit(self.index(0, y1), self.index(len(self.blender.electrodes) -1, y2))
        
    def onDataError(self, boolarray):
        self.voltagesOutOfRange = boolarray
        self.allVoltagesOkay = False
        self.dataChanged.emit(self.index(1, 0), self.index(1, len(self.blender.electrodes) -1))
        
    def displayToolTip(self, index):
        return "ToolTip"
  
    def data(self, index, role): 
        if index.isValid():
            if role==QtCore.Qt.DisplayRole:
                return { 0: str(self.blender.electrodes[self.orderLookup[index.row()]]) if self.blender.electrodes is not None else None,
                         1: str(self.blender.outputVoltage[self.orderLookup[index.row()]]) if self.blender.outputVoltage is not None else None,
                         2: self.blender.aoNums[self.orderLookup[index.row()]] if self.blender.aoNums is not None else None,
                         3: self.blender.dsubNums[self.orderLookup[index.row()]] if self.blender.dsubNums is not None else None,
                         }.get(index.column(), None)
            elif role==QtCore.Qt.BackgroundColorRole:
                return { 0:  QtGui.QColor(QtCore.Qt.white) if self.allVoltagesOkay else QtGui.QColor(QtCore.Qt.red),
                         1:  QtGui.QColor(QtCore.Qt.red) if self.voltagesOutOfRange[self.orderLookup[index.row()]] else QtGui.QColor(QtCore.Qt.white)
                         }.get(index.column(), None)
        return None
        
    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return { 0: "Electrode", 1: "voltage", 2: "ao channel", 3: "dsub pin" }[section]
            elif (orientation == QtCore.Qt.Vertical): 
                return section
        return None #QtCore.QVariant()

    def flags(self, index ):
        return QtCore.Qt.ItemIsEnabled 
