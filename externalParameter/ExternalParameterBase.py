# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import OrderedDict

from PyQt5 import QtCore
from pyqtgraph.parametertree import Parameter
import logging
from externalParameter.OutputChannel import OutputChannel,\
    SlowAdjustOutputChannel
from externalParameter.InputChannel import InputChannel
from .InstrumentSettings import InstrumentSettings

InstrumentDict = dict()

class InstrumentException(Exception):
    pass

class InstrumentMeta(type):
    def __new__(self, name, bases, dct):
        instrclass = super(InstrumentMeta, self).__new__(self, name, bases, dct)
        if name!='ExternalParameterBase':
            if 'className' not in dct:
                raise InstrumentException("Instrument class needs to have class attribute 'className'")
            InstrumentDict[dct['className']] = instrclass
        return instrclass
    
class ExternalParameterBase(object, metaclass=InstrumentMeta):
    _outputChannels = { None: None }    # a single channel with key None designates a device only supporting a single channel
    _inputChannels = dict()
    _channelParams = {None: ()}
    def __init__(self, name, deviceSettings, globalDict):
        self.name = name
        self.settings = deviceSettings
        self.setDefaults()
        self._parameter = Parameter.create(name='params', type='group', children=self.paramDef())
        try:
            self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        except:
            pass
        self.globalDict = globalDict
        self.createOutputChannels()

    def createOutputChannels(self):
        """create all output channels"""
        self.outputChannels = OrderedDict( [(channel, SlowAdjustOutputChannel(self, self.name, channel, self.globalDict, self.settings.channelSettings.get(channel, dict()), unit))
                                    for channel, unit in self._outputChannels.items()] )
        
    def lastOutputValue(self, channel):
        """return the last value written to channel""" 
        return self.outputChannels[channel].settings.value
        
    def initializeChannelsToExternals(self):
        """Initialize all channels to the values read from the instrument"""
        for cname in self._outputChannels.keys():
            self.outputChannels[cname].settings.value = self.getValue(cname)

    def dimension(self, channel):
        """return the dimension eg 'Hz' or 'V' for channel""" 
        return self._outputChannels[channel]

    def setParameters(self):
        pass
        
    @property
    def parameter(self):
        # re-create the parameters each time to prevent a exception that says the signal is not connected
        self._parameter = Parameter.create(name=self.name, type='group', children=self.paramDef())     
        self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        return self._parameter        
        
    def setDefaults(self, settings=None):
        if settings is None:
            settings = self.settings
        settings.__dict__.setdefault('channelSettings', dict())
        settings.__dict__.setdefault('setExternal', False)
        for cname in self._outputChannels:
            settings.channelSettings.setdefault(cname, InstrumentSettings())

    def initOutput(self):
        if self.settings.setExternal:
            for cname in self._outputChannels:
                self.setValue(cname, self.settings.channelSettings[cname].targetValue)
            self.setParameters()

    def setValue(self, channel, v):
        """write the value to the instrument"""
        return None
    
    def getValue(self, channel=None):
        """returns current value as read from instrument (if the instruments supports reading)"""
        return self.lastOutputValue(channel)
    
    def getExternalValue(self, channel=None):
        """
        if the value is determined externally, return the external value, otherwise return value
        """
        return self.getValue(channel)

    def paramDef(self):
        """
        return the parameter definition used by pyqtgraph parametertree to show the gui
        """
        return [{'name': 'setExternal', 'type': 'bool', 'value': self.settings.setExternal}]
        
    def update(self, param, changes):
        """
        update the parameter, called by the signal of pyqtgraph parametertree
        """
        logger = logging.getLogger(__name__)
        logger.debug( "ExternalParameterBase.update" )
        for param, change, data in changes:
            if change=='value':
                logger.debug( " ".join( [str(self), "update", param.name(), str(data)] ) )
                setattr( self.settings, param.name(), data)
            elif change=='activated':
                getattr( self, param.opts['field'] )()
            
    def close(self):
        pass
    
    def fullName(self, channel):
        return "{0}_{1}".format(self.name, channel) if channel is not None else self.name
    
    def useExternalValue(self, channel=None):
        return False
            
    def outputChannelList(self):
        return [(self.fullName(channelName), channel) for channelName, channel in self.outputChannels.items()]
    
    def inputChannelList(self):
        return [(self.fullName(channel), InputChannel(self, self.name, channel)) for channel in self._inputChannels.keys()]
        
    def getInputData(self, channel):
        return None
