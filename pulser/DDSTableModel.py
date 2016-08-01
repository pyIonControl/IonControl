# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
from modules.firstNotNone import firstNotNone
from functools import partial

class DDSTableModel(QtCore.QAbstractTableModel):
    headerDataLookup = ['On', 'Name', 'Frequency', 'Phase', 'Amplitude', 'Square' ]
    frequencyChanged = QtCore.pyqtSignal( object, object )
    phaseChanged = QtCore.pyqtSignal( object, object )
    amplitudeChanged = QtCore.pyqtSignal( object, object )
    enableChanged = QtCore.pyqtSignal( object, object )
    squareChanged = QtCore.pyqtSignal( object, object )
    def __init__(self, ddsChannels, globalDict, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        # scanNames are given as a SortedDict
        self.ddsChannels = ddsChannels
        self.defaultBG = QtGui.QColor(QtCore.Qt.white)
        self.textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
        self.dataLookup = {  (QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.ddsChannels[row].enabled else QtCore.Qt.Unchecked,
                             (QtCore.Qt.DisplayRole, 1): lambda row: self.ddsChannels[row].name,
                             (QtCore.Qt.DisplayRole, 2): lambda row: str(self.ddsChannels[row].frequency),
                             (QtCore.Qt.DisplayRole, 3): lambda row: str(self.ddsChannels[row].phase),
                             (QtCore.Qt.DisplayRole, 4): lambda row: str(self.ddsChannels[row].amplitude),
                             (QtCore.Qt.EditRole, 1): lambda row: self.ddsChannels[row].name,
                             (QtCore.Qt.EditRole, 2): lambda row: firstNotNone( self.ddsChannels[row].frequencyText, str(self.ddsChannels[row].frequency)),
                             (QtCore.Qt.EditRole, 3): lambda row: firstNotNone( self.ddsChannels[row].phaseText, str(self.ddsChannels[row].phase)),
                             (QtCore.Qt.EditRole, 4): lambda row: firstNotNone( self.ddsChannels[row].amplitudeText, str(self.ddsChannels[row].amplitude)),
                             (QtCore.Qt.BackgroundColorRole, 2): lambda row: self.defaultBG if self.ddsChannels[row].frequencyText is None else self.textBG,
                             (QtCore.Qt.BackgroundColorRole, 3): lambda row: self.defaultBG if self.ddsChannels[row].phaseText is None else self.textBG,
                             (QtCore.Qt.BackgroundColorRole, 4): lambda row: self.defaultBG if self.ddsChannels[row].amplitudeText is None else self.textBG,
                             (QtCore.Qt.CheckStateRole, 5): lambda row: QtCore.Qt.Checked if self.ddsChannels[row].squareEnabled else QtCore.Qt.Unchecked,
                              }
        self.setDataLookup =  {  (QtCore.Qt.CheckStateRole, 0): self.setEnabled,
                                 (QtCore.Qt.EditRole, 1): self.setName,
                                 (QtCore.Qt.EditRole, 2): self.setFrequency,
                                 (QtCore.Qt.EditRole, 3): self.setPhase,
                                 (QtCore.Qt.EditRole, 4): self.setAmplitude,
                                 (QtCore.Qt.UserRole, 2): partial( self.setFieldText, 'frequencyText'),
                                 (QtCore.Qt.UserRole, 3): partial( self.setFieldText, 'phaseText'),
                                 (QtCore.Qt.UserRole, 4): partial( self.setFieldText, 'amplitudeText'),
                                 (QtCore.Qt.CheckStateRole, 5): self.setSquareEnabled,
                                 }
        self.globalDict = globalDict

    def onShutterChanged(self):
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(0, self.rowCount()) )

    def setEnabled(self, index, value):
        enabled = value==QtCore.Qt.Checked
        self.ddsChannels[index.row()].enabled = enabled
        self.enableChanged.emit( index.row(), enabled)
        return True
 
    def setSquareEnabled(self, index, value):
        enabled = value==QtCore.Qt.Checked
        self.ddsChannels[index.row()].squareEnabled = enabled
        self.squareChanged.emit( index.row(), enabled)
        return True
    
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)
                
    def setName(self, index, value):
        self.ddsChannels[index.row()].name = value
        return True
    
    def setFrequency(self, index, value):
        self.ddsChannels[index.row()].frequency = value
        self.frequencyChanged.emit( index.row(), value)
        return True
    
    def setPhase(self, index, value):
        self.ddsChannels[index.row()].phase = value 
        self.phaseChanged.emit( index.row(), value)
        return True
    
    def setAmplitude(self, index, value):
        self.ddsChannels[index.row()].amplitude = value
        self.amplitudeChanged.emit( index.row(), value)
        return True
    
    def setFieldText(self, fieldname, index, value):
        setattr( self.ddsChannels[index.row()], fieldname, value )
        return True

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.ddsChannels) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 6
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
    
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)
        
    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable if index.column() in [0, 5] else QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
            elif (orientation == QtCore.Qt.Vertical):
                return str(section)
        return None  # QtCore.QVariant()
