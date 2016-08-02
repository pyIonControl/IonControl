"""
Created on 09 Dec 2015 at 8:38 PM

author: jmizrahi
"""
import logging

from PyQt5 import QtCore

from modules.MagnitudeParser import isIdentifier
from modules.enum import enum


class AWGSegmentTableModel(QtCore.QAbstractTableModel):
    """Table model for displaying AWG segments when the AWGUi is in segment mode"""
    segmentChanged = QtCore.pyqtSignal(int, int, int, object) #channel, row, column, value
    def __init__(self, channel, settings, globalDict, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.channel = channel
        self.settings = settings
        self.globalDict = globalDict
        self.column = enum('enabled', 'amplitude', 'duration')
        self.dataLookup = {
            (QtCore.Qt.CheckStateRole, self.column.enabled): lambda row: QtCore.Qt.Checked if self.segmentList[row]['enabled'] else QtCore.Qt.Unchecked,
            (QtCore.Qt.DisplayRole, self.column.amplitude): lambda row: self.segmentList[row]['amplitude'],
            (QtCore.Qt.DisplayRole, self.column.duration): lambda row: self.segmentList[row]['duration'],
            (QtCore.Qt.EditRole, self.column.amplitude): lambda row: self.segmentList[row]['amplitude'],
            (QtCore.Qt.EditRole, self.column.duration): lambda row: self.segmentList[row]['duration']
            }
        self.setDataLookup = {
            (QtCore.Qt.CheckStateRole, self.column.enabled): lambda index, value: self.setEnabled(index, value),
            (QtCore.Qt.EditRole, self.column.amplitude): lambda index, value: self.setValue(index, value, 'amplitude'),
            (QtCore.Qt.EditRole, self.column.duration): lambda index, value: self.setValue(index, value, 'duration')
            }
        self.flagsLookup = {
            self.column.enabled: QtCore.Qt.ItemIsEnabled|  QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable,
            self.column.amplitude: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable,
            self.column.duration: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
            }

    @QtCore.pyqtProperty(list)
    def segmentList(self):
        return self.settings.channelSettingsList[self.channel]['segmentList']

    def flags(self, index):
        return self.flagsLookup[index.column()]

    def setEnabled(self, index, value):
        row = index.row()
        column = index.column()
        enabled = value==QtCore.Qt.Checked
        self.segmentList[row]['enabled'] = enabled
        self.dataChanged.emit(index, index)
        self.segmentChanged.emit(self.channel, row, column, enabled)
        self.settings.saveIfNecessary()
        return True

    def setValue(self, index, value, key):
        row = index.row()
        column = index.column()
        if value in self.globalDict:
            logging.getLogger(__name__).warning("'{0}' is already a global variable name".format(value))
            return False
        elif not isIdentifier(value):
            logging.getLogger(__name__).warning("'{0}' is not a valid variable name".format(value))
            return False
        else:
            self.segmentList[row][key] = value
            self.dataChanged.emit(index, index)
            self.segmentChanged.emit(self.channel, row, column, value)
            self.settings.saveIfNecessary()
            return True

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.segmentList)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 3

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None

    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)

    def headerData(self, section, orientation, role):
        if role==QtCore.Qt.DisplayRole:
            if orientation==QtCore.Qt.Vertical:
                return str(section)
            elif orientation==QtCore.Qt.Horizontal:
                if section==self.column.amplitude:
                    return 'Amplitude'
                elif section==self.column.duration:
                    return 'Duration'

    def addSegment(self):
        row = len(self.segmentList)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self.segmentList.append({
            'enabled':True,
            'amplitude':'v{0}'.format(row),
            'duration':'t{0}'.format(row)})
        self.settings.saveIfNecessary()
        self.endInsertRows()

    def removeSegment(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        del self.segmentList[row]
        self.settings.saveIfNecessary()
        self.endRemoveRows()

