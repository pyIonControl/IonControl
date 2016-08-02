# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore
from enum import Enum

from gui.ExpressionValue import ExpressionValue
from modules.quantity import Q
from modules.descriptor import SetterProperty

counterDict = dict(('Count {0}'.format(i), i) for i in range(16))

class CounterSetting(QtCore.QObject):
    valueChanged = QtCore.pyqtSignal(object, object, object, object)
    stateFields = ('name', 'states', 'minValue', 'maxValue')

    def __init__(self, name='Count 0', states=None, minValue=0, maxValue=Q(0), globalDict=None):
        super().__init__()
        self.name = name
        self.states = sorted(list(states)) if states is not None else list()
        self.minValue = minValue if isinstance(minValue, ExpressionValue) else ExpressionValue(name=name, globalDict=globalDict, value=minValue)
        self.maxValue = maxValue if isinstance(maxValue, ExpressionValue) else ExpressionValue(name=name, globalDict=globalDict, value=maxValue)
        self.minValue.valueChanged.connect(self.onValueChanged)
        self.maxValue.valueChanged.connect(self.onValueChanged)

    def onValueChanged(self, *args):
        self.valueChanged.emit(*args)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, newname):
        self._name = newname
        self._counter = counterDict[newname]

    @property
    def counter(self):
        return self._counter

    @property
    def counterMask(self):
        return 1 << self._counter

    @SetterProperty
    def globalDict(self, newglobaldict):
        self.minValue.globalDict = newglobaldict
        self.maxValue.globalDict = newglobaldict

    def __reduce__(self):
        return self.__class__, (self.name, self.states, self.minValue, self.maxValue)

    def __eq__(self, other):
        return (self.name, self.states, self.minValue, self.maxValue) == (other.name, other.states, other.minValue, other.maxValue)

    def __ne__(self, other):
        return not self == other

    def inRange(self, rate):
        return self.minValue.value <= rate <= self.maxValue.value

    def underRange(self, rate):
        return rate < self.minValue.value

    def overRange(self, rate):
        return self.maxValue.value < rate


AdjustType = Enum('AdjustType', 'Shutter Global Voltage_node', module=__name__)


class AdjustSetting:

    def __init__(self, adjType=None, name='', value=None, states=None, globalDict=None):
        self.adjType = adjType if adjType is not None else AdjustType.Shutter
        if isinstance(name, list):
            self._name = name
        else:
            self._name = [None, None, None, None]
            self.name = name
        self.states = sorted(list(states)) if states is not None else list()
        if isinstance(value, list):
            self._value = value
        else:
            self._value = [None, True, ExpressionValue(globalDict=globalDict), None]  # Unused, Shutter value, Global value, Voltage_node value
            if value is not None:
                self.value = value

    @property
    def name(self):
        return self._name[self.adjType.value]

    @name.setter
    def name(self, newvalue):
        self._name[self.adjType.value] = newvalue

    @property
    def value(self):
        return self._value[self.adjType.value]

    @value.setter
    def value(self, newvalue):
        self._value[self.adjType.value] = newvalue

    @property
    def displayValue(self):
        if self.adjType == AdjustType.Global:
            return str(self._value[self.adjType.value].value)
        if self.adjType == AdjustType.Voltage_node:
            return 'instant' if not self._value[self.adjType.value] else 'shuttle'
        return None

    @property
    def backgroundValue(self):
        if self.adjType in (AdjustType.Shutter, AdjustType.Voltage_node):
            return self.adjType, self._value[self.adjType.value]
        if self.adjType == AdjustType.Global:
            return self.adjType, self._value[self.adjType.value].hasDependency
        return None

    @SetterProperty
    def globalDict(self, globalDict):
        self._value[2].globalDict = globalDict

    def __reduce__(self):
        return self.__class__, (self.adjType, self.name, self._value, self.states)

    def __eq__(self, other):
        return (self.adjType, self.name, self.states, self.value) == (
                other.adjType, other.name, other.states, other.value)

    def __ne__(self, other):
        return not self == other
