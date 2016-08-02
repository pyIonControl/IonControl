# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools

from PyQt5 import QtCore, QtWidgets
import PyQt5.uic

from modules import CountrateConversion
from trace.pens import penicons
from modules.SequenceDict import SequenceDict
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from uiModules.MultiSelectDelegate import MultiSelectDelegate
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from dedicatedCounters.DedicatedCountersTableModel import DedicatedCounterTableModel
from modules.PyqtUtility import updateComboBoxItems
from modules.GuiAppearance import restoreGuiState, saveGuiState
from modules.Utility import unique
from modules.quantity import Q
from datetime import datetime, timedelta
import copy

import os

from modules.AttributeComparisonEquality import AttributeComparisonEquality

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/DedicatedCountersSettings.ui')
UiForm, UiBase = PyQt5.uic.loadUiType(uipath)

import pytz
def now():
    return datetime.now(pytz.utc)

class Settings(object):
    def __init__(self):
        self.counterMask = 0
        self.adcMask = 0
        self.integrationTime = Q(100, 'ms')
        self.displayUnit = CountrateConversion.DisplayUnit()
        self.unit = 0
        self.pointsToKeep = 400
        self.counterDict = dict(zip(list(['Count {0}'.format(i) for i in range(16)]), list(i for i in range(16))))
        self.adcDict = dict(zip(list(['ADC {0}'.format(i) for i in range(4)]), list(i for i in range(4))))
        self.plotDisplayData = SequenceDict()

        self.name = "DedicatedCounterSettings"

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
        self.__dict__.setdefault( 'pointsToKeep', 400 )
        self.__dict__.setdefault( 'counterDict', dict(zip(list(['Count {0}'.format(i) for i in range(16)])
                                                          , list(i for i in range(16)))) )
        self.__dict__.setdefault( 'adcDict', dict(zip(list(['ADC {0}'.format(i) for i in range(4)])
                                                      , list(i for i in range(4)))) )
        self.__dict__.setdefault( 'plotDisplayData', SequenceDict() )

        self.__dict__.setdefault( 'name', "DedicatedCounterSettings" )

class DedicatedCountersSettings(UiForm,UiBase ):
    valueChanged = QtCore.pyqtSignal(object)

    def __init__(self,config,plotDict,parent=None):
        UiForm.__init__(self)
        UiBase.__init__(self,parent)
        self.config = config
        self.plotDict = plotDict
        self.settings = self.config.get('DedicatedCounterSettings.Settings',Settings())
        self.settingsDict = self.config.get('DedicatedCounterSettings.Settings.dict', dict())
        self.currentSettingsName = self.config.get('DedicatedCounterSettings.SettingsName','')

    def setupUi(self, parent):
        UiForm.setupUi(self,parent)
        self.integrationTimeBox.setValue( self.settings.integrationTime )
        self.integrationTimeBox.valueChanged.connect( functools.partial(self.onValueChanged, 'integrationTime') )
        self.pointsToKeepBox.setValue( self.settings.pointsToKeep )
        self.pointsToKeepBox.valueChanged.connect( functools.partial(self.onValueChanged,'pointsToKeep') )
        self.displayUnitCombo.currentIndexChanged[int].connect( self.onIndexChanged )
        self.displayUnitCombo.setCurrentIndex(self.settings.unit)
        self.settings.displayUnit.unit = self.settings.unit

        # Added counter table to select which counters to plot
        self.DedicatedTableModel = DedicatedCounterTableModel( self.settings.counterDict
                                                               ,self.settings.adcDict,self.settings.plotDisplayData,self.plotDict)
        self.DedicatedTableModel.edited.connect( self.onSaveProfile )
        self.DedicatedTableModel.edited.connect( self.updateMask )
        self.DedicatedCounterTableView.setModel( self.DedicatedTableModel )
        self.comboBoxDelegate = ComboBoxDelegate()
        self.magnitudeSpinBoxDelegate = MagnitudeSpinBoxDelegate()
        self.multiSelectDelegate = MultiSelectDelegate()
        self.DedicatedCounterTableView.setItemDelegateForColumn( 0, self.multiSelectDelegate )
        self.DedicatedCounterTableView.setItemDelegateForColumn( 1, self.comboBoxDelegate )
        self.dropDedicatedCounterSettingButton.clicked.connect( self.onCounterRemoveSetting )
        self.addDedicatedCounterSettingButton.clicked.connect( self.DedicatedTableModel.addSetting )

        #Plot legend
        icons = penicons().penicons()
        for n in range(20):
            if n < 16:
                item = QtWidgets.QListWidgetItem(icons[n+1], "Count {0}".format(n))
            else:
                item = QtWidgets.QListWidgetItem(icons[n+1], "ADC {0}".format(n-16))
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.plotLegend.addItem(item)

        self.removeDedicatedCountersProfileButton.clicked.connect( self.onRemoveProfile )
        restoreGuiState( self, self.config.get('DedicatedCounterSettings.guiState') )
        # Added profiles
        self.profileDedicatedCountersComboBox.addItems( self.settingsDict.keys() )
        if self.currentSettingsName in self.settingsDict:
            self.profileDedicatedCountersComboBox.setCurrentIndex( self.profileDedicatedCountersComboBox.findText(self.currentSettingsName))
        else:
            self.currentSettingsName = str( self.profileDedicatedCountersComboBox.currentText() )
        self.profileDedicatedCountersComboBox.currentIndexChanged[str].connect(self.onLoadProfile)
        self.profileDedicatedCountersComboBox.lineEdit().editingFinished.connect( self.onSaveProfile )

        self.setProfile( self.currentSettingsName, self.settings )
        self.onSaveProfile()
    
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
        self.config['DedicatedCounterSettings.Settings'] = self.settings
        self.config['DedicatedCounterSettings.guiState'] = saveGuiState( self )
        self.config['DedicatedCounterSettings.Settings.dict'] = self.settingsDict
        self.config['DedicatedCounterSettings.SettingsName'] = self.currentSettingsName

    def saveable(self):
        name = str(self.profileDedicatedCountersComboBox.currentText())
        return name != '' and ( name not in self.settingsDict or not (self.settingsDict[name] == self.settings))

