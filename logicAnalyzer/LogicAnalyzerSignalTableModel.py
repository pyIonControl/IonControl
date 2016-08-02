# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore

    
class LogicAnalyzerSignalTableModel(QtCore.QAbstractTableModel):
    enableChanged = QtCore.pyqtSignal()
    def __init__(self, config, channelNameData, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.shutterChannelNames, self.shutterNamesSignal, self.triggerChannelNames, self.triggerNamesSignal, _ = channelNameData
        self.dataSignals = 64
        self.auxSignals = 10
        self.gateSignals = 32
        self.triggerSignals = 7
        self.enabledList = config.get('LogicAnalyzer.EnabledChannels', [True]*(self.dataSignals+self.auxSignals+self.triggerSignals) )
        if len(self.enabledList)!=self.rowCount():
            self.enabledList.extend( [True]*(self.rowCount()-len(self.enabledList)))
        self.dataLookup = { (QtCore.Qt.DisplayRole, 1): lambda row: self.channelName(row),
                            (QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.enabledList[row] else QtCore.Qt.Unchecked,
                     }
        self.shutterNamesSignal.dataChanged.connect( lambda first, last: self.dataChanged.emit( self.createIndex(first, 0), self.createIndex(last, 0) ))
        self.triggerNamesSignal.dataChanged.connect( lambda first, last: self.dataChanged.emit( self.createIndex(first+self.dataSignals, 0), self.createIndex(last+self.dataSignals, 0) ))
        
    auxChannelNames = ['dds write done', 'out fifo full', 'in fifo empty', 'ram fifo valid', 'DDS 0 CS', 'DDS 1 CS', 'DDS 2 CS', 'DDS 3 CS', 'DDS 4 CS', 'DDS 5 CS']
            
    def channelName(self, index):
        if index<self.dataSignals:
            return self.primaryChannelName(index)
        elif index<self.dataSignals+self.auxSignals:
            return self.auxChannelName(index - self.dataSignals)
        elif index<self.dataSignals+self.auxSignals+self.triggerSignals:
            return self.triggerChannelName(index-self.dataSignals-self.auxSignals)
        else:
            return self.gateChannelName(index-self.dataSignals-self.auxSignals-self.triggerSignals)
                
    def auxChannelName(self, index):
        return self.auxChannelNames[index]
    
    def triggerChannelName(self, index):
        if index == 6:
            return "Ram set address"
        elif index in self.triggerChannelNames:
            return self.triggerChannelNames[index]
        else:
            return "Trigger {0}".format(index)

    def primaryChannelName(self, index):
        if index in self.shutterChannelNames:
            return self.shutterChannelNames[index]
        else:
            return "Shutter {0}".format(index)

    def gateChannelName(self, index):
        if index>23: 
            return "Timestamp {0}".format(index-24)
        else:
            return "Counter {0}".format(index)
         
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return self.dataSignals+self.auxSignals+self.triggerSignals+self.gateSignals
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def setData(self, index, value, role):
        if (role, index.column()) == (QtCore.Qt.CheckStateRole, 0): 
            self.enabledList[index.row()] = value==QtCore.Qt.Checked
            
            self.enableChanged.emit()
            return True
        return False

    def flags(self, index ):
        return { 0: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled,
                 1: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled,
                 }.get(index.column(), QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return {
                    0: 'Show',
                    1: 'Signal',
                     }.get(section)
        return None #QtCore.QVariant()
    
    def saveConfig(self):
        self.config['LogicAnalyzer.EnabledChannels'] = self.enabledList
        