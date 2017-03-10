# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools
from functools import partial

from PyQt5 import QtCore, QtWidgets
import PyQt5.uic

from modules import CountrateConversion
from trace.pens import penicons
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from uiModules.MultiSelectDelegate import MultiSelectDelegate
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from dedicatedCounters.DedicatedCountersTableModel import DedicatedCounterTableModel
from modules.PyqtUtility import updateComboBoxItems
from modules.GuiAppearance import restoreGuiState, saveGuiState
from modules.Utility import unique

from datetime import datetime, timedelta
import copy

import os

from uiModules.ParameterTable import ParameterTable, Parameter,ParameterTableModel
from pulseProgram import VariableTableModel,VariableDictionary
from modules.SequenceDict import SequenceDict
from modules.quantity import Q

from modules.AttributeComparisonEquality import AttributeComparisonEquality

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/CameraSettings.ui')
UiForm, UiBase = PyQt5.uic.loadUiType(uipath)

import pytz
def now():
    return datetime.now(pytz.utc)

class Settings(object):
    def __init__(self):

        self.integrationTime = Q(100, 'ms')
        self.displayUnit = CountrateConversion.DisplayUnit()
        self.unit = 0
        self.exposureTime = 100
        self.EMGain = 0

        self.plotDisplayData = SequenceDict()

        self.name = "CameraSettings"



    def __setstate__(self, state):
        """this function ensures that the given fields are present in the class object
        after unpickling. Only new class attributes need to be added here.
        """
        self.__dict__ = state
        self.__dict__.setdefault( 'counterMask', 0 )
        self.__dict__.setdefault( 'adcMask', 0 )
        self.__dict__.setdefault('integrationTime', Q(100, 'ms'))
        self.__dict__.setdefault( 'displayUnit', CountrateConversion.DisplayUnit() )
        self.__dict__.setdefault( 'unit', 0 )
        self.__dict__.setdefault( 'exposureTime', 307 )
        self.__dict__.setdefault( 'EMgain', 13)

        self.__dict__.setdefault( 'name', "CameraSettings" )

class CameraSettings(UiForm,UiBase):
    valueChanged = QtCore.pyqtSignal(object)

    def __init__(self,config,globalVariablesUi,parent=None):
        UiForm.__init__(self)
        UiBase.__init__(self,parent)
        self.config = config
        self.settings = self.config.get('CameraSettings.Settings',Settings())
        self.settingsDict = self.config.get('CameraSettings.Settings.dict', dict())
        self.currentSettingsName = self.config.get('CameraSettings.SettingsName','')

        self.globalVariables = globalVariablesUi.globalDict
        self.globalVariablesChanged = globalVariablesUi.valueChanged
        self.globalVariablesUi = globalVariablesUi



        self.a = Parameter(name='exposuretime', dataType='magnitude', value=Q(100, 'ms'), tooltip="Exposure time")
        self.b = Parameter(name='EMGain', dataType='magnitude', value=0, tooltip="EM gain")
        self.c = Parameter(name='experiments', dataType='magnitude', value=100, tooltip="Number of experiments")

        self.parameterDict = SequenceDict(
            [(self.a.name, self.a),
             (self.b.name, self.b),
             (self.c.name, self.c)]
        )

        self.ParameterTableModel = ParameterTableModel(parameterDict=self.parameterDict)



    def setupUi(self, parent):
        UiForm.setupUi(self,parent)
        self.integrationTimeBox.setValue( self.settings.integrationTime )
        self.integrationTimeBox.valueChanged.connect( functools.partial(self.onValueChanged, 'integrationTime') )
        self.exposureTimeBox.setValue( self.settings.exposureTime )
        self.exposureTimeBox.valueChanged.connect( functools.partial(self.onValueChanged,'exposureTime') )
        self.EMGainBox.setValue(self.settings.EMGain)
        self.EMGainBox.valueChanged.connect(functools.partial(self.onValueChanged, 'EMGain'))

        self.displayUnitCombo.currentIndexChanged[int].connect( self.onIndexChanged )
        self.displayUnitCombo.setCurrentIndex(self.settings.unit)
        self.settings.displayUnit.unit = self.settings.unit

        self.ParameterTable = ParameterTable()
        self.ParameterTable.setupUi(parameterDict=self.parameterDict, globalDict=self.globalVariables)
        if self.globalVariablesChanged:
            self.globalVariablesChanged.connect(self.ParameterTableModel.evaluate)
        self.parameterView.setModel(self.ParameterTableModel)
        self.parameterView.resizeColumnToContents(0)
        # self.parameterView.clicked.connect(self.onVariableViewClicked)

        self.ParameterTableModel.valueChanged.connect(partial(self.onDataChanged, self.ParameterTableModel.parameterDict))



    def onDataChanged(self,parameterDict):
        for key, param in self.parameterDict.items():
            print('{0}: {1}'.format(key, param.value))



    def onLoadProfile(self, name):
        name = str(name)
        if name in self.settingsDict and name!=self.currentSettingsName:
            self.setProfile( name, copy.deepcopy( self.settingsDict[name] ) )

    def onSaveProfile(self):
        name = str(self.profileDedicatedCountersComboBox.currentText())
        isNew = name not in self.settingsDict
        self.settingsDict[name] = copy.deepcopy( self.settings )
        if isNew:
            updateComboBoxItems( self.profileDedicatedCountersComboBox, sorted(self.settingsDict.keys()), name)

    def onRemoveProfile(self):
        name = str(self.profileDedicatedCountersComboBox.currentText())
        if name in self.settingsDict:
            self.settingsDict.pop(name)
            updateComboBoxItems( self.profileDedicatedCountersComboBox, sorted(self.settingsDict.keys()))
            name = str(self.profileComboBox.currentText())
            self.onLoadProfile(name)

    def setProfile(self, name, profile):
        self.settings = profile
        self.currentSettingsName = name
        self.displayUnitCombo.setCurrentIndex(self.settings.unit)
        self.DedicatedTableModel.setSettings(self.settings.plotDisplayData)
        self.valueChanged.emit( self.settings )

    def onCounterRemoveSetting(self):
        for index in sorted(unique([ i.row() for i in self.DedicatedCounterTableView.selectedIndexes() ]),reverse=True):
            self.DedicatedTableModel.dropSetting(index)
        self.onSaveProfile()

    def updateMask(self):
        self.settings.counterMask = 0
        self.settings.adcMask = 0
        self.plotDisplayData = self.settings.plotDisplayData
        for plot, counters in self.plotDisplayData.items():
            for counter in counters:
                if counter in self.settings.counterDict:
                    num = self.settings.counterDict[counter]
                    if not (self.settings.counterMask & (1 << num)):
                        self.settings.counterMask |= (1 << num)
                elif counter in self.settings.adcDict:
                    num = self.settings.adcDict[counter]
                    if not (self.settings.adcMask & (1 << num)):
                        self.settings.adcMask |= (1 << num)

        self.valueChanged.emit( self.settings )
        self.onSaveProfile()

    def onIndexChanged(self, index):
        self.settings.displayUnit.unit = index
        self.settings.unit = index
        self.valueChanged.emit( self.settings)
    
    def onValueChanged(self, name, value):
        setattr(self.settings, name, value)
        self.valueChanged.emit( self.settings )

    def saveConfig(self):
        self.config['CameraSettings.Settings'] = self.settings
        #self.config['CameraSettings.guiState'] = saveGuiState( self ) #TODO
        self.config['CameraSettings.Settings.dict'] = self.settingsDict
        self.config['CameraSettings.SettingsName'] = self.currentSettingsName

    def saveable(self):
        name = str(self.profileDedicatedCountersComboBox.currentText())
        return name != '' and ( name not in self.settingsDict or not (self.settingsDict[name] == self.settings))




