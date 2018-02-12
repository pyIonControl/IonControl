# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui

from notify.notification import NotificationSubscription


class NotificationTableModel(QtCore.QAbstractTableModel):
    getWavemeterData = QtCore.pyqtSignal(object)
    headerDataLookup = ['Name', 'Recipients', 'Subscriptions']

    def __init__(self, notificationCenter, parent=None, *args):
        """ datain: a list where each item is a row

        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.nc = notificationCenter
        self.ncs = notificationCenter.subscriptions
        self.lookup = dict()
        self.setDataLookup = {(QtCore.Qt.EditRole, 0): self.setName,
                              (QtCore.Qt.EditRole, 1): self.setRecipients,
                              (QtCore.Qt.EditRole, 2): self.setSubscriptions,
                              (QtCore.Qt.CheckStateRole, 0): self.setEnable, }
        self.dataLookup = {(QtCore.Qt.CheckStateRole, 0): lambda row: QtCore.Qt.Checked if self.ncs[row].enabled else QtCore.Qt.Unchecked,
                           (QtCore.Qt.DisplayRole, 0): lambda row: self.ncs[row].name,
                           (QtCore.Qt.DisplayRole, 1): lambda row: ", ".join(self.ncs[row].recipients) if self.ncs[row].recipients else None,
                           (QtCore.Qt.DisplayRole, 2): lambda row: " | ".join(self.ncs[row].subscriptions),
                           (QtCore.Qt.EditRole, 0): lambda row: self.ncs[row].name,
                           (QtCore.Qt.EditRole, 1): lambda row: ", ".join(self.ncs[row].recipients) if self.ncs[row].recipients else "",
                           (QtCore.Qt.EditRole, 2): lambda row: self.ncs[row].subscriptions }

    def choice(self, index):
        if index.column() == 2:
            return list(self.nc.origins)

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
        return result

    def setValue(self, index, value):
        pass

    def flags(self, index):
        if index.column() in [1, 2]:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        if index.column() in [0]:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def setName(self, index, value):
        self.ncs[index.row()].name = value
        return True

    def setSubscriptions(self, index, value):
        self.ncs[index.row()].subscriptions = set(value)
        return True

    def setRecipients(self, index, value):
        self.ncs[index.row()].recipients = [r.strip() for r in value.split(",")]
        return True

    def setEnable(self, index, value):
        self.ncs[index.row()].enabled = value == QtCore.Qt.Checked
        return True

    def addChannel(self):
        index = len(self.ncs)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        c = NotificationSubscription()
        self.ncs.append(c)
        self.endInsertRows()

    def removeChannel(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        self.ncs.pop(index)
        self.endRemoveRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.ncs)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 3

