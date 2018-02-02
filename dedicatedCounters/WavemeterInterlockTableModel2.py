# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui

from dedicatedCounters.WavemeterInterlock import LockStatus, InterlockChannel
from modules.quantity import Q


class WavemeterInterlockTableModel(QtCore.QAbstractTableModel):
    getWavemeterData = QtCore.pyqtSignal(object)
    headerDataLookup = ['Enable', 'Wavemeter', 'Channel', 'Current', 'Minimum', 'Maximum', 'Use Server', 'Contexts']
    attributeLookup = ['enabled', 'wavemeter', 'channel', 'current', 'minimum', 'maximum', 'useServerInterlock', None]
    edited = QtCore.pyqtSignal()

    def __init__(self, channelData=list(), parent=None, *args):
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.channelData = channelData
        self.setDataLookup = {(QtCore.Qt.EditRole, 1): self.setWavemeter,
                              (QtCore.Qt.EditRole, 2): self.setChannel,
                              (QtCore.Qt.EditRole, 4): self.setMin,
                              (QtCore.Qt.EditRole, 5): self.setMax,
                              (QtCore.Qt.CheckStateRole, 0): self.setEnable,
                              (QtCore.Qt.CheckStateRole, 6): self.setUseServer,}
        self.dataLookup = {(QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.channelData[row].enabled else QtCore.Qt.Unchecked,
                           (QtCore.Qt.CheckStateRole, 6): lambda row: QtCore.Qt.Checked if self.channelData[row].useServerInterlock else QtCore.Qt.Unchecked,
                           (QtCore.Qt.DisplayRole, 1): lambda row: self.channelData[row].wavemeter,
                           (QtCore.Qt.DisplayRole, 2): lambda row: self.channelData[row].channel,
                           (QtCore.Qt.DisplayRole, 3): lambda row: "{}".format(
                               self.channelData[row].currentFreq),
                           (QtCore.Qt.BackgroundColorRole, 3): lambda row: QtGui.QColor(QtCore.Qt.white) if not self.channelData[row].enabled else QtGui.QColor(0xa6, 0xff, 0xa6, 0xff) if self.channelData[row].currentState == LockStatus.Locked else QtGui.QColor(0xff, 0xa6, 0xa6, 0xff),
                           (QtCore.Qt.DisplayRole, 4): lambda row: str(self.channelData[row].minimum),
                           (QtCore.Qt.DisplayRole, 5): lambda row: str(self.channelData[row].maximum),
                           (QtCore.Qt.EditRole, 2): lambda row: self.channelData[row].channel,
                           (QtCore.Qt.EditRole, 4): lambda row: str(self.channelData[row].minimum),
                           (QtCore.Qt.EditRole, 5): lambda row: str(self.channelData[row].maximum),
                           (QtCore.Qt.UserRole, 4): lambda row: Q(1, 'GHz'),
                           (QtCore.Qt.UserRole, 5): lambda row: Q(1, 'GHz'), }
        self._subscribe()
        self.lookup = {(c.wavemeter, c.channel): i for i, c in enumerate(self.channelData)}

    def _subscribe(self):
        for c in self.channelData:
            c.subscribe(self._dataChanged)

    def _dataChanged(self, wavemeter=None, channel=None):
        idx = self.lookup.get((wavemeter, channel))
        self.dataChanged.emit(self.createIndex(idx, 3), self.createIndex(idx, 7))

    def setChannels(self, channelData):
        self.beginResetModel()
        self.channelData = channelData
        self.endResetModel()

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal):
                return self.headerDataLookup[section]
        return None

    def setData(self, index, value, role):
        result = self.setDataLookup.get((role, index.column()), lambda index, value: False)(index, value)
        if result:
            self.edited.emit()
        return result

    def setValue(self, index, value):
        pass

    def flags(self, index):
        if index.column() in [1, 3, 4]:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        if index.column() == 0:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def setWavemeter(self, index, value):
        pass

    def setChannel(self, index, value):
        channel = int(value)
        if channel == self.channelData[index.row()].channel:  # no change
            return True
        self.channelData[index.row()].channel = channel
        return True

    def setMin(self, index, value):
        self.channelData[index.row()].minimum = value
        return True

    def setMax(self, index, value):
        self.channelData[index.row()].maximum = value
        return True

    def setEnable(self, index, value):
        self.channelData[index.row()].enabled = value == QtCore.Qt.Checked
        return True

    def setUseServer(self, index, value):
        self.channelData[index.row()].useServerInterlock = value == QtCore.Qt.Checked
        return True

    def addChannel(self):
        index = len(self.channelData)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        c = InterlockChannel(channel=0)
        c.subscribe(self._dataChanged)
        self.channelData.append()
        self.endInsertRows()

    def removeChannel(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        self.channelData.pop(index)
        self.endRemoveRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.channelData)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 8

    def sort(self, column, order):
        self.beginResetModel()
        # self.channelData = sorted(self.channelData, key=lambda x: getattr(x, self.attributeLookup[column]), reverse=order==QtCore.Qt.DescendingOrder)
        self.endResetModel()
