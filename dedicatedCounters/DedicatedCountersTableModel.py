# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtCore,QtGui
from modules import Expression
from pulseProgram.ShutterDictionary import ShutterDictionary
from itertools import filterfalse


class DedicatedCounterTableModel(QtCore.QAbstractTableModel):
    onColor =  QtGui.QColor(QtCore.Qt.green)
    offColor =  QtGui.QColor(QtCore.Qt.red)
    headerDataLookup = ['Counter', 'Plot']
    expression = Expression.Expression()
    edited = QtCore.pyqtSignal()
    def __init__(self, counterDict,adcDict,plotDisplayData,plotDict, parent=None, *args):
        """ variabledict dictionary of variable value pairs as defined in the pulse programmer file
            parameterdict dictionary of parameter value pairs that can be used to calculate the value of a variable
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.plotDisplayData = plotDisplayData
        self.counterDict = counterDict
        self.adcDict = adcDict
        self.counterChoiceDict = {}
        self.adcChoiceDict = {}
        self.counterChoiceDict.update(self.counterDict)
        self.counterChoiceDict.update(self.adcDict)
        self.shutterDict = ShutterDictionary()
        self.plotDict = plotDict
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda row: ' | '.join(self.plotDisplayData.at(row)),
                             (QtCore.Qt.DisplayRole, 1): lambda row: self.plotDisplayData.keyAt(row),
                             (QtCore.Qt.EditRole, 0):    lambda row: self.plotDisplayData.at(row),
                             (QtCore.Qt.EditRole, 1):    lambda row: self.plotDisplayData.keyAt(row),
                             }
        self.setDataLookup = { (QtCore.Qt.EditRole, 0): self.setCounterName,
                               (QtCore.Qt.EditRole, 1): self.setPlotName,
                               }
        self.choiceLookup = { 0: lambda row: sorted(self.counterChoiceDict.keys(), key=lambda name: self.adcDict[name]+16 if name.startswith('ADC') else self.counterDict[name]),
                              1: lambda row: filterfalse(lambda x: x=='Autoload', self.plotDict.keys()) }

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.plotDisplayData)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())

    def setCounterName(self, index, counterList):
        row=index.row()
        key=self.plotDisplayData.keyAt(row)
        self.plotDisplayData[key] = sorted(counterList, key=lambda name: self.adcDict[name]+16 if name.startswith('ADC') else self.counterDict[name])
        return True

    def setPlotName(self, index, name):
        try:
            strvalue = name.strip()
            row = index.row()
            self.plotDisplayData.renameAt(row, strvalue)
            self.edited.emit()
            return True
        except Exception:
            logger = logging.getLogger(__name__)
            logger.exception("No match for {0}".format(strvalue))
            return False

    def setData(self, index, value, role):
        result =  self.setDataLookup.get((role, index.column()), lambda row, value: False)(index, value)
        if result:
            self.edited.emit()
        return result

    def flags(self, index):
         return { 0: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable,
                  1: QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable}[index.column()]

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal):
                return self.headerDataLookup[section]

    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)

    def addSetting(self):
        if None not in self.plotDisplayData or len(self.plotDisplayData)==0:
            self.beginInsertRows(QtCore.QModelIndex(), len(self.plotDisplayData), len(self.plotDisplayData))
            self.plotDisplayData.setdefault(None, list())
            self.endInsertRows()
            self.edited.emit()
        return len(self.plotDisplayData) - 1

    def dropSetting(self, row):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        name = self.plotDisplayData.keyAt(row)
        self.plotDisplayData.pop(name)
        self.endRemoveRows()
        self.edited.emit()
        return len(self.plotDisplayData) - 1

    def choice(self, index):
        return self.choiceLookup.get(index.column(), lambda row: [])(index.row())

    def setSettings(self,plotDisplayData):
        self.beginResetModel()
        self.plotDisplayData = plotDisplayData
        self.endResetModel()