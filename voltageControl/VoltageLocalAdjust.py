# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore
import PyQt5.uic

from modules.SequenceDict import SequenceDict
from .VoltageLocalAdjustTableModel import VoltageLocalAdjustTableModel   #@UnresolvedImport
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from externalParameter.VoltageOutputChannel import VoltageOutputChannel
from _collections import defaultdict
from modules.Observable import Observable
from gui.ExpressionValue import ExpressionValue
import os.path
from modules.Utility import unique
import hashlib
import numpy
from _functools import partial
import copy
from modules.quantity import is_Q

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/VoltageLocalAdjust.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class Settings:
    def __init__(self):
        self.gain = 1.0
        self.gainCache = dict()
    
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault( 'gainCache', dict() )
        
class LocalAdjustRecord(object):
    def __init__(self, name="", path=None, gain=0, globalDict=None):
        self.name = name
        self.path = path
        self.gain = gain if isinstance(gain, ExpressionValue) else ExpressionValue(name, globalDict, gain)
        self._updateGainValue()
        self._solution = None
        self.solutionPath = None
        self.solutionHash = hash(None)
        self.gain.valueChanged.connect(self._updateGainValue)
        
    def __getstate__(self):
        return (self.name, self.path, self.gain)

    def __setstate__(self, state):
        self.name, self.path, self.gain = state
        self.solution = None
        self.solutionPath = None
        self.solutionHash = hash(None)
        self.gain.valueChanged.connect(self._updateGainValue)
        self._updateGainValue()

    def _updateGainValue(self):
        self.gainValue = float(self.gain.value)

    @property
    def filename(self):
        return os.path.split(self.path)[1] if self.path else ""
    
    @property
    def globalDict(self):
        return self.gain.globalDict
    
    @globalDict.setter
    def globalDict(self, globalDict):
        self.gain.globalDict = globalDict
    
    def __hash__(self):
        return hash( (self.solutionHash, self.gain) )

    def __lt__(self, other):
        return self.name < other.name
    
    @property
    def solution(self):
        return self._solution
    
    @solution.setter
    def solution(self, sol):
        self._solution = sol
        if self._solution:
            hash( tuple( (hashlib.sha256(a.view(numpy.uint8)).hexdigest() for a in self._solution) ) )
        else:
            self.solutionHash = hash(self._solution)
            
class VoltageLocalAdjust(Form, Base ):
    updateOutput = QtCore.pyqtSignal(object, object)
    outputChannelsChanged = QtCore.pyqtSignal(object)
    filesChanged = None
    _channelParams = {}

    def __init__(self, config, globalDict, parent=None):
        Form.__init__(self)
        Base.__init__(self, parent)
        self.config = config
        self.configname = 'VoltageLocalAdjust.Settings'
        self.settings = self.config.get(self.configname, Settings())
        self.localAdjustList = self.config.get( self.configname+".local", list() )
        for record in self.localAdjustList:
            record.globalDict = globalDict
            #record.gain.recalculate(forceUpdate=True)
            try:
                record.gain.valueChanged.connect( partial( self.onValueChanged, record ), QtCore.Qt.UniqueConnection)
            except:
                pass
        self.channelDict = dict( ((record.name, record) for record in self.localAdjustList) )
        self.historyCategory = 'VoltageLocalAdjust'
        self.adjustHistoryName = None
        self.globalDict = globalDict
        self.savedValue = defaultdict( lambda: None )
        self.displayValueObservable = defaultdict( lambda: Observable() )

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.tableModel = VoltageLocalAdjustTableModel( self.localAdjustList, self.channelDict, self.globalDict )
        self.filesChanged = self.tableModel.filesChanged
        self.tableView.setModel( self.tableModel )
        self.tableView.setSortingEnabled(True)   # triggers sorting
        self.delegate =  MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(1, self.delegate)
        self.addButton.clicked.connect( self.onAdd )
        self.removeButton.clicked.connect( self.onRemove )
        
    def onValueChanged(self, record, name, value, string, origin):
        if origin=='recalculate':
            self.tableModel.valueRecalcualted(record)
        record.gain._value = float( record.gain._value )
        self.updateOutput.emit(self.localAdjustList, 0)

    def onAdd(self):
        newrecord = self.tableModel.add( LocalAdjustRecord(globalDict=self.globalDict) )
        try:
            newrecord.gain.valueChanged.connect( partial( self.onValueChanged, newrecord ), QtCore.Qt.UniqueConnection )
        except:
            pass
    
    def onRemove(self):
        for index in sorted(unique([ i.row() for i in self.tableView.selectedIndexes() ]), reverse=True):
            self.tableModel.drop(index)
        
    def saveConfig(self):
        self.config[self.configname] = self.settings
        self.config[self.configname+".local"] = self.localAdjustList
        
    def setValue(self, channel, value):
        self.channelDict[channel].gain.value = value
        self.channelDict[channel].gain.setDefaultFunc()
        return True

    def getValue(self, channel):
        return self.channelDict[channel].gain.value

    def currentValue(self, channel):
        return self.channelDict[channel].gain.value
    
    def saveValue(self, channel):
        self.savedValue[channel] = (self.channelDict[channel].gain._string, self.channelDict[channel].gain._value)

    def restoreValue(self, channel):
        if self.savedValue[channel] is not None:
            string, value = self.savedValue[channel]
            if string is not None:
                self.channelDict[channel].gain.string = string
            else:
                self.channelDict[channel].gain.value = value
        return True
    
    def strValue(self, channel):
        adjust = self.channelDict[channel].gain
        return adjust.string if adjust.hasDependency else None
    
    def setStrValue(self, channel, value):
        pass
    
    def outputChannels(self):
        self._outputChannels = dict(((record.name, VoltageOutputChannel(self, None, record.name, self.globalDict)) for record in self.localAdjustList))
        return self._outputChannels
        
