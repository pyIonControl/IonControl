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

        self.exposureTime = Q(100, 'ms')
        self.EMGain = 0
        self.NumberOfExperiments = 100
        self.name = "CameraSettings"



    def __setstate__(self, state):
        """this function ensures that the given fields are present in the class object
        after unpickling. Only new class attributes need to be added here.
        """
        self.__dict__ = state
        self.__dict__.setdefault( 'exposureTime', Q(100, 'ms') )
        self.__dict__.setdefault( 'EMGain', 0)
        self.__dict__.setdefault('NumberOfExperiments', 200)
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


        self.settings.exposureTime = Parameter(name='exposuretime', dataType='magnitude', value=Q(5, 'ms'), tooltip="Exposure time")
        self.settings.EMGain = Parameter(name='EMGain', dataType='magnitude', value=0, tooltip="EM gain")
        self.settings.NumberOfExperiment = Parameter(name='experiments', dataType='magnitude', value=100, tooltip="Number of experiments")

        self.parameterDict = SequenceDict(
            [(self.settings.exposureTime.name, self.settings.exposureTime),
             (self.settings.EMGain.name, self.settings.EMGain),
             (self.settings.NumberofExperiment.name, self.settings.NumberofExperiment)]
        )

        self.ParameterTableModel = ParameterTableModel(parameterDict=self.parameterDict)


    def setupUi(self, parent):
        UiForm.setupUi(self,parent)

        # self.integrationTimeBox.setValue( self.settings.integrationTime )
        # self.integrationTimeBox.valueChanged.connect( functools.partial(self.onValueChanged, 'integrationTime') )
        # self.exposureTimeBox.setValue( self.settings.exposureTime1 )
        # self.exposureTimeBox.valueChanged.connect( functools.partial(self.onValueChanged,'exposureTime') )
        # self.EMGainBox.setValue(self.settings.EMGain1)
        # self.EMGainBox.valueChanged.connect(functools.partial(self.onValueChanged, 'EMGain'))

        self.ParameterTable = ParameterTable()
        self.ParameterTable.setupUi(parameterDict=self.parameterDict, globalDict=self.globalVariables)
        self.parameterView.setModel(self.ParameterTableModel)
        self.parameterView.resizeColumnToContents(0)

        self.delegate = MagnitudeSpinBoxDelegate(self.globalVariables)
        self.parameterView.setItemDelegateForColumn(1, self.delegate)
        if self.globalVariablesChanged:
            self.globalVariablesChanged.connect(partial(self.ParameterTableModel.evaluate, self.globalVariables))
        #self.ParameterTableModel.valueChanged.connect(partial(self.onDataChanged, self.ParameterTableModel.parameterDict))

    def onDataChanged(self,parameterDict):
        for key, param in self.parameterDict.items():
            print('{0}: {1}'.format(key, param.value))

    
    def onValueChanged(self, name, value):
        setattr(self.settings, name, value)
        self.valueChanged.emit( self.settings )


    def saveConfig(self):
        self.config['CameraSettings.Settings'] = self.settings
        #self.config['CameraSettings.guiState'] = saveGuiState( self ) #TODO
        self.config['CameraSettings.Settings.dict'] = self.settingsDict
        self.config['CameraSettings.SettingsName'] = self.currentSettingsName





