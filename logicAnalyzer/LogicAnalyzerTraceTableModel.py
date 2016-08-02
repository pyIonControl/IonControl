# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui


def anyNonZero( dictionary, keys ):
    for key in keys:
        if dictionary.get(key, None):
            return True
    return False

    
class LogicAnalyzerTraceTableModel(QtCore.QAbstractTableModel):
    def __init__(self, config, signalTableModel, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.signalTableModel = signalTableModel
        self.dataLookup = { (QtCore.Qt.DisplayRole, 0): lambda row: self.pulseData[row][0],
                            (QtCore.Qt.DisplayRole, 1): lambda row: self.pulseData[row][0]-self.referenceTime
                     }
        self.pulseData = None
        self.rawPulseData = None
        self.referenceTime = 0
        self.onEnabledChannelsChanged()
        self.signalTableModel.enableChanged.connect( self.onEnabledChannelsChanged )
        
    def eliminateEmptyRows(self, rawPulseData):
        significantPulseData = list()
        for record in rawPulseData:
            if anyNonZero( record[1], self.enabledSignalLookup ):
                significantPulseData.append(record)    
        return significantPulseData            
        
    def setPulseData(self, pulseData):
        self.beginResetModel()
        self.rawPulseData = list(sorted(pulseData.items()))
        self.headerDataChanged.emit( QtCore.Qt.Horizontal, 0, len(self.enabledSignalLookup) )
        self.pulseData = self.eliminateEmptyRows(self.rawPulseData)
        self.endResetModel()
        
    def onEnabledChannelsChanged(self):
        self.beginResetModel()
        self.enabledSignalLookup = list()
        for channel, enabled in enumerate(self.signalTableModel.enabledList):
            if enabled:
                self.enabledSignalLookup.append(channel)
        if self.rawPulseData:
            self.pulseData = self.eliminateEmptyRows(self.rawPulseData)
        self.endResetModel()
        self.headerDataChanged.emit( QtCore.Qt.Horizontal, 0, len(self.enabledSignalLookup) )
        
    def setReferenceTime(self, time):
        self.referenceTime = time
        self.dataChanged.emit( self.createIndex(0, 1), self.createIndex(self.rowCount(), 1))
        
    def setReferenceTimeCell(self, index):
        self.referenceTime = self.pulseData[index.row()][0]
        self.dataChanged.emit( self.createIndex(0, 1), self.createIndex(self.rowCount(), 1))
        
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.pulseData) if self.pulseData else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 2 + len(self.enabledSignalLookup)
 
    colorLookup = { -1: QtGui.QColor(QtCore.Qt.red), 1: QtGui.QColor(QtCore.Qt.green), 0: QtGui.QColor(QtCore.Qt.white), None: QtGui.QColor(QtCore.Qt.white) }
    def pulseDataLookup(self, timestep, signal):
        return self.colorLookup[self.pulseData[timestep][1].get(signal, None)]
    
    def data(self, index, role): 
        if index.isValid():
            if index.column()>1 and role==QtCore.Qt.BackgroundColorRole:
                return self.pulseDataLookup(index.row(), self.enabledSignalLookup[index.column()-2])
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def flags(self, index ):
        return  QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                if section==0:
                    return 'Time'
                if section==1:
                    return 'relative time'
                return self.signalTableModel.channelName(self.enabledSignalLookup[section-2])
        return None #QtCore.QVariant()
    
    def saveConfig(self):
        self.config['LogicAnalyzer.EnabledChannels'] = self.enabledList
        