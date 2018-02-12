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

    def __init__(self, channelData=list(), wavemeterNames=[], contexts=set(), parent=None, *args):
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.lookup = dict()
        self.channelData = channelData
        self.setDataLookup = {(QtCore.Qt.EditRole, 0): self.setName,
                              (QtCore.Qt.EditRole, 1): self.setWavemeter,
                              (QtCore.Qt.EditRole, 2): self.setChannel,
                              (QtCore.Qt.EditRole, 4): self.setMin,
                              (QtCore.Qt.EditRole, 5): self.setMax,
                              (QtCore.Qt.EditRole, 7): self.setContext,
                              (QtCore.Qt.CheckStateRole, 0): self.setEnable,
                              (QtCore.Qt.CheckStateRole, 6): self.setUseServer,}
        self.dataLookup = {(QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.channelData[row].enabled else QtCore.Qt.Unchecked,
                           (QtCore.Qt.CheckStateRole, 6): lambda row: QtCore.Qt.Checked if self.channelData[row].useServerInterlock else QtCore.Qt.Unchecked,
                           (QtCore.Qt.DisplayRole, 0): lambda row: self.channelData[row].name,
                           (QtCore.Qt.DisplayRole, 1): lambda row: self.channelData[row].wavemeter,
                           (QtCore.Qt.DisplayRole, 2): lambda row: self.channelData[row].channel,
                           (QtCore.Qt.DisplayRole, 3): lambda row: "{}".format(
                               self.channelData[row].currentFreq),
                           (QtCore.Qt.BackgroundColorRole, 3): lambda row: QtGui.QColor(QtCore.Qt.white) if not self.channelData[row].enabled else QtGui.QColor(0xa6, 0xff, 0xa6, 0xff) if self.channelData[row].currentState == LockStatus.Locked else QtGui.QColor(0xff, 0xa6, 0xa6, 0xff),
                           (QtCore.Qt.BackgroundColorRole, 4): lambda row: QtGui.QColor(QtCore.Qt.white) if not self.channelData[row].useServerInterlock else QtGui.QColor(QtCore.Qt.lightGray),
                           (QtCore.Qt.BackgroundColorRole, 5): lambda row: QtGui.QColor(QtCore.Qt.white) if not self.channelData[row].useServerInterlock else QtGui.QColor(QtCore.Qt.lightGray),
                           (QtCore.Qt.BackgroundColorRole, 6): lambda row: QtGui.QColor(QtCore.Qt.white) if self.channelData[row].serverRangeActive else QtGui.QColor(QtCore.Qt.lightGray),
                           (QtCore.Qt.DisplayRole, 4): lambda row: str(self.channelData[row].minimum),
                           (QtCore.Qt.DisplayRole, 5): lambda row: str(self.channelData[row].maximum),
                           (QtCore.Qt.DisplayRole, 7): lambda row: " | ".join(self.channelData[row].contextSet),
                           (QtCore.Qt.EditRole, 0): lambda row: self.channelData[row].name,
                           (QtCore.Qt.EditRole, 2): lambda row: self.channelData[row].channel,
                           (QtCore.Qt.EditRole, 4): lambda row: str(self.channelData[row].minimum),
                           (QtCore.Qt.EditRole, 5): lambda row: str(self.channelData[row].maximum),
                           (QtCore.Qt.EditRole, 7): lambda row: self.channelData[row].contextSet,
                           (QtCore.Qt.UserRole, 4): lambda row: Q(1, 'GHz'),
                           (QtCore.Qt.UserRole, 5): lambda row: Q(1, 'GHz'), }
        self._subscribe()
        self.wavemeterNames = wavemeterNames
        self.contexts = contexts
        self._updateLookup()

    def _updateLookup(self):
        self.lookup = {(c.wavemeter, c.channel): i for i, c in enumerate(self.channelData)}

    def choice(self, index):
        if index.column() == 1:
            return self.wavemeterNames
        if index.column() == 7:
            return [c for c in self.contexts if c]  # remove the None

    def _subscribe(self):
        for c in self.channelData:
            c.subscribe(self._dataChanged)

    def _dataChanged(self, wavemeter=None, channel=None):
        idx = self.lookup.get((wavemeter, channel))
        if idx is not None:
            self.dataChanged.emit(self.createIndex(idx, 3), self.createIndex(idx, 3))

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
        if index.column() in [1, 2, 4, 5, 7]:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        if index.column() in [6]:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
        if index.column() in [0]:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def setWavemeter(self, index, value):
        self.channelData[index.row()].wavemeter = value
        return True

    def setName(self, index, value):
        self.channelData[index.row()].name = value
        return True

    def setContext(self, index, value):
        self.channelData[index.row()].contextSet = set(value)
        return True

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
        self.channelData.append(c)
        self.endInsertRows()

    def removeChannel(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        self.channelData.pop(index)
        self._updateLookup()
        self.endRemoveRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.channelData)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 8

    def sort(self, column, order):
        self.beginResetModel()
        # self.channelData = sorted(self.channelData, key=lambda x: getattr(x, self.attributeLookup[column]), reverse=order==QtCore.Qt.DescendingOrder)
        self.endResetModel()
