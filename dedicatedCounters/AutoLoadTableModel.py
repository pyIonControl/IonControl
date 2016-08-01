# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtCore,QtGui

from dedicatedCounters.CounterSetting import AdjustSetting, AdjustType


class AutoLoadSettingsTableModel(QtCore.QAbstractTableModel):
    colorLookup = {None: None,
                   (AdjustType.Shutter, True): QtGui.QColor(QtCore.Qt.green),
                   (AdjustType.Shutter, False): QtGui.QColor(QtCore.Qt.red),
                   (AdjustType.Global, True): QtGui.QColor(QtCore.Qt.green).lighter(175),
                   (AdjustType.Global, False): QtGui.QColor(QtCore.Qt.white),
                   (AdjustType.Voltage_node, True): QtGui.QColor(QtCore.Qt.blue).lighter(175),
                   (AdjustType.Voltage_node, False): QtGui.QColor(QtCore.Qt.yellow).lighter(175)
                   }
    headerDataLookup = ['Type', 'Name', 'Value', 'States']
    typeDataLookup = [e.name.replace('_', ' ') for e in AdjustType]
    edited = QtCore.pyqtSignal()

    def __init__(self, adjustDisplayData, shuttlingNodes, globalDict, shutterDict, stateDict, parent=None, *args):
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.adjustDisplayData = adjustDisplayData
        self.globalDict = globalDict
        self.shutterDict = shutterDict
        self.nodeList = shuttlingNodes
        if self.nodeList and ' ' in self.nodeList:
            self.nodeList.remove('')
        self.stateDict = stateDict
        self.dataLookup = {(QtCore.Qt.DisplayRole, 0): lambda row: self.adjustDisplayData[row].adjType.name.replace('_', ' '),
                           (QtCore.Qt.DisplayRole, 1): lambda row: self.adjustDisplayData[row].name,
                           (QtCore.Qt.DisplayRole, 2): lambda row: self.adjustDisplayData[row].displayValue,
                           (QtCore.Qt.BackgroundColorRole, 2): lambda row: self.colorLookup[self.adjustDisplayData[row].backgroundValue],
                           (QtCore.Qt.DisplayRole, 3): lambda row: ' | '.join(self.adjustDisplayData[row].states),
                           (QtCore.Qt.ToolTipRole, 3): lambda row: ' | '.join(self.adjustDisplayData[row].states),
                           (QtCore.Qt.EditRole, 0): lambda row: self.adjustDisplayData[row].adjType.name.replace('_', ' '),
                           (QtCore.Qt.EditRole, 1): lambda row: self.adjustDisplayData[row].name,
                           (QtCore.Qt.EditRole, 2): lambda row: self.adjustDisplayData[row].value.string,
                           (QtCore.Qt.EditRole, 3): lambda row: self.adjustDisplayData[row].states,
                           }
        self.setDataLookup = {(QtCore.Qt.EditRole, 0): self.setDataType,
                              (QtCore.Qt.EditRole, 1): self.setDataName,
                              (QtCore.Qt.EditRole, 2): self.setDataValue,
                              (QtCore.Qt.UserRole, 2): self.setDataValueStr,
                              (QtCore.Qt.EditRole, 3): self.setStateName,
                              }
        self.choiceLookup = {0: lambda row: self.typeDataLookup,
                             1: lambda row: (lambda: None, lambda: sorted(self.shutterDict.values()), lambda: sorted(self.globalDict.keys()), lambda: self.nodeList)[self.adjustDisplayData[row].adjType.value](),
                             3: lambda row: self.stateDict.keys()}

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.adjustDisplayData)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())

    def setDataValue(self, index, value):
        self.adjustDisplayData[index.row()].value.value = value
        return True

    def setDataValueStr(self, index, value):
        self.adjustDisplayData[index.row()].value.string = value
        return True

    def setDataName(self, index, name):
        self.adjustDisplayData[index.row()].name = name
        return True

    def setDataType(self, index, value):
        self.adjustDisplayData[index.row()].adjType = AdjustType[value.replace(' ', '_')]
        return True

    def setStateName(self, index, stateList):
        self.adjustDisplayData[index.row()].states = stateList
        self.dataChanged.emit(index, index)
        return True

    def setData(self, index, value, role):
        result = self.setDataLookup.get((role, index.column()), lambda row, value: False)(index, value)
        if result:
            self.edited.emit()
        return result

    def onClicked(self, index):
        elem = self.adjustDisplayData[index.row()]
        if index.column() == 2 and elem.adjType in (AdjustType.Shutter, AdjustType.Voltage_node):
            elem.value = not elem.value
            self.dataChanged.emit(index, index)
            self.edited.emit()

    def flags(self, index):
        if index.column() == 2 and self.adjustDisplayData[index.row()].adjType in (AdjustType.Shutter, AdjustType.Voltage_node):
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headerDataLookup[section]

    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)

    def getVariables(self):
        return self.adjustDisplayData

    def addSetting(self):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.adjustDisplayData), len(self.adjustDisplayData))
        self.adjustDisplayData.append(AdjustSetting(globalDict=self.globalDict))
        self.endInsertRows()
        self.edited.emit()
        return len(self.adjustDisplayData) - 1

    def dropSetting(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        name = self.adjustDisplayData.pop(row).name
        self.endRemoveRows()
        self.edited.emit()
        return name

    def choice(self, index):
        return self.choiceLookup.get(index.column(), lambda row: [])(index.row())

    def setSettings(self, adjustDisplayData):
        self.beginResetModel()
        self.adjustDisplayData = adjustDisplayData
        self.endResetModel()
