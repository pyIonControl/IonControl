# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import math
import os

import PyQt5.uic
from PyQt5 import QtCore

from modules.RunningStat import RunningStat
from modules.quantity import is_Q

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/DedicatedDisplay.ui')
DedicatedDisplayForm, DedicatedDisplayBase = PyQt5.uic.loadUiType(uipath)


class Settings:
    def __init__(self):
        self.average = False
        self.precision = [None] * 4

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('precision', [None] * 4)


class DedicatedDisplay(DedicatedDisplayForm, DedicatedDisplayBase ):
    def __init__(self, config, name, parent=None):
        DedicatedDisplayForm.__init__(self)
        DedicatedDisplayBase.__init__(self, parent)
        self.config = config
        self.name = name
        self._values = [0]*8
        self.configName = "DedicatedDisplay." + self.name
        self.settings = self.config.get(self.configName, Settings())
        self.stat = [RunningStat()] * 4

    def setupUi(self, parent):
        DedicatedDisplayForm.setupUi(self, parent)
        self.averageCheck.setChecked(self.settings.average)
        self.averageCheck.stateChanged.connect(self.onAverageChanged)
        self.labelWidgets = (self.label0, self.label1, self.label2, self.label3)
        for label, prec in zip(self.labelWidgets, self.settings.precision):
            label.precision = prec
            
    def onAverageChanged(self, state ):
        self.settings.average = state == QtCore.Qt.Checked
        self.stat = [RunningStat()] * 4
        if not self.settings.average:
            self.numPointsLabel.setText("")
        else:
            self.numPointsLabel.setText("{0} points".format(self.stat[0].count))
            
    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        if self.settings.average:
            for stat, value in zip(self.stat, values):
                stat.add(value)
            for index, label in enumerate([self.label0, self.label1, self.label2, self.label3]):
                if self.stat[index].count == 0:
                    self._values[index] = None
                    label.setText("None")
                else:
                    if is_Q(self.stat[index].mean):
                        self._values[index] = self.stat[index].mean
                        label.value = self._values[index].m  # TODO: needs fixing
                    else:
                        self._values[index] = self.stat[index].mean
                        label.precision = int(math.ceil(-math.log10(self.stat[index].stddev))) if self.stat[index].stddev else 0
                        label.value = self._values[index]
            self.numPointsLabel.setText("{0} points".format(self.stat[0].count))
        else:
            for value, label in zip(values, self.labelWidgets):
                label.value = value
            self._values = values

    def saveConfig(self):
        self.settings.precision = [label.precision for label in self.labelWidgets]
        self.config[self.configName] = self.settings
