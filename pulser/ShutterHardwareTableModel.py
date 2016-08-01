# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtCore, QtGui
from modules.dictReverseLookup import dictValueFind


class ShutterHardwareTableModel(QtCore.QAbstractTableModel):
    onColor =  QtGui.QColor(QtCore.Qt.green)
    offColor =  QtGui.QColor(QtCore.Qt.red)
    customColor = QtGui.QColor(QtCore.Qt.black)
    defaultColor = QtGui.QColor(QtCore.Qt.gray)
    def __init__(self, pulserHardware, outputname, data, size=32, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.pulserHardware = pulserHardware
        self.outputname = outputname
        self.size = size
        self._shutter = getattr(self.pulserHardware, self.outputname)
        self.data, self.dataChangedSignal = data 
        self.dataLookup = { (QtCore.Qt.DisplayRole, 0):          lambda row: self.data.get(row, None),
                            (QtCore.Qt.BackgroundColorRole, 1):  lambda row: self.onColor if self._shutter & (1<<row) else self.offColor,
                            (QtCore.Qt.TextColorRole, 0):        lambda row: self.customColor if row in self.data.customDict else self.defaultColor,
                            (QtCore.Qt.EditRole, 0):             lambda row: self.data.get(row, ''),
                            (QtCore.Qt.ToolTipRole, 0):          lambda row: self.data.defaultDict.get(row, None)
                           }

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return self.size
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
 
    def setData(self, index, value, role):
        logger = logging.getLogger(__name__)
        if index.column()==0 and role==QtCore.Qt.EditRole:
            key = dictValueFind( self.data.customDict, value )
            if key and key==index.row(): # no change
                return True
            elif key: # duplicate
                logger.warning( "cannot have the same name '{0}' twice".format(value) )
                return False
            else:
                if value.strip() != '':
                    self.data[index.row()] = value
                    if self.dataChangedSignal is not None:
                        self.dataChangedSignal.dataChanged.emit( index.row(), index.row() )
                else:
                    if index.row() in self.data.customDict:
                        self.data.pop(index.row())
                        if self.dataChangedSignal is not None:
                            self.dataChangedSignal.dataChanged.emit( index.row(), index.row() )
        return False
        
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def flags(self, index ):
        return  { 0: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable,
                  1: QtCore.Qt.ItemIsEnabled }[index.column()]

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Vertical): 
                return str(section)
            elif (orientation == QtCore.Qt.Horizontal): 
                return { 0: 'Name',
                         1: 'Value' }[section]
        return None 

    def onClicked(self, index):
        if index.column()==1:
            self._shutter ^= 1<<index.row()
        setattr(self.pulserHardware, self.outputname, self._shutter)
        self.dataChanged.emit(index, index)
        
    @property
    def shutter(self):
        return self._shutter  #
         
    @shutter.setter
    def shutter(self, value):
        self._shutter = value
        setattr(self.pulserHardware, self.outputname, self._shutter)
        self.dataChanged.emit(self.createIndex(0, 1), self.createIndex(self.size, 1))
        
    def updateShutter(self, value):
        """ updates the display only,
        called by the hardware backend to indicate changes
        by other means than the gui
        """
        if self._shutter != value:
            self._shutter = value
            self.dataChanged.emit(self.createIndex(0, 1), self.createIndex(self.size, 1))