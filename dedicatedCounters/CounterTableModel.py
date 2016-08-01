# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtCore,QtGui

from pulseProgram.ShutterDictionary import ShutterDictionary
from dedicatedCounters.CounterSetting import CounterSetting, counterDict

class AutoLoadCounterTableModel(QtCore.QAbstractTableModel):
    defaultBG = QtGui.QColor(QtCore.Qt.white)
    textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
    backgroundLookup = {True: textBG, False:defaultBG}
    headerDataLookup = ['Name', 'State', 'Min', 'Max']
    edited = QtCore.pyqtSignal()

    def __init__(self, counterDisplayData,globalDict, parent=None, *args):
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.counterDisplayData = counterDisplayData
        self.globalDict = globalDict
        self.shutterDict = ShutterDictionary()
        self.counterStates = ['Load', 'PeriodicCheck', 'Check', 'Trapped', 'WaitingForComeback', 'PostSequenceWait']
        self.dataLookup = {(QtCore.Qt.DisplayRole, 0): lambda row: self.counterDisplayData[row].name,
                           (QtCore.Qt.DisplayRole, 1): lambda row: ' | '.join(self.counterDisplayData[row].states),
                           (QtCore.Qt.DisplayRole, 2): lambda row: str(self.counterDisplayData[row].minValue.value),
                           (QtCore.Qt.DisplayRole, 3): lambda row: str(self.counterDisplayData[row].maxValue.value),
                           (QtCore.Qt.EditRole, 0): lambda row: self.counterDisplayData[row].name,
                           (QtCore.Qt.EditRole, 1): lambda row: self.counterDisplayData[row].states,
                           (QtCore.Qt.EditRole, 2): lambda row: self.counterDisplayData[row].minValue.string,
                           (QtCore.Qt.EditRole, 3): lambda row: self.counterDisplayData[row].maxValue.string,
                           (QtCore.Qt.BackgroundColorRole, 2): lambda row: self.backgroundLookup[self.counterDisplayData[row].minValue.hasDependency],
                           (QtCore.Qt.BackgroundColorRole, 3): lambda row: self.backgroundLookup[self.counterDisplayData[row].maxValue.hasDependency]}
        self.setDataLookup = {(QtCore.Qt.EditRole, 0): self.setCounterName,
                              (QtCore.Qt.EditRole, 1): self.setStateName,
                              (QtCore.Qt.EditRole, 2): self.setMinValue,
                              (QtCore.Qt.EditRole, 3): self.setMaxValue,
                              (QtCore.Qt.UserRole, 2): self.setMinValueStr,
                              (QtCore.Qt.UserRole, 3): self.setMaxValueStr,
                              }
        self.choiceLookup = {0: lambda row: sorted(counterDict.keys(), key=counterDict.get),
                             1: lambda row: self.counterStates}

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.counterDisplayData)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 4

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())

    def setMinValue(self, index, value):
        self.counterDisplayData[index.row()].minValue.value = value
        return True

    def setMaxValue(self, index, value):
        self.counterDisplayData[index.row()].maxValue.value = value
        return True

    def setMinValueStr(self, index, value):
        self.counterDisplayData[index.row()].minValue.string = value
        return True

    def setMaxValueStr(self, index, value):
        self.counterDisplayData[index.row()].maxValue.string = value
        return True

    def setCounterName(self, index, name):
        self.counterDisplayData[index.row()].name = name.strip()
        return True

    def setStateName(self, index, stateList):
        self.counterDisplayData[index.row()].states = stateList
        self.dataChanged.emit(index,index)
        return True

    def setData(self, index, value, role):
        result = self.setDataLookup.get((role, index.column()), lambda row, value: False)(index, value)
        if result:
            self.edited.emit()
        return result

    def flags(self, index):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headerDataLookup[section]

    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)

    def addSetting(self):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.counterDisplayData), len(self.counterDisplayData))
        self.counterDisplayData.append(CounterSetting(globalDict=self.globalDict))
        self.endInsertRows()
        self.edited.emit()
        return len(self.counterDisplayData) - 1

    def dropSetting(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.counterDisplayData.pop(row)
        self.endRemoveRows()
        self.edited.emit()
        return len(self.counterDisplayData) - 1

    def choice(self, index):
        return self.choiceLookup.get(index.column(), lambda row: [])(index.row())

    def setSettings(self, settings):
        self.beginResetModel()
        self.counterDisplayData = settings
        self.endResetModel()
