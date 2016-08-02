# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from .ExternalParameterBase import ExternalParameterBase
from multiprocessing.connection import Client

class LockOutputFrequency(ExternalParameterBase):

    className = "Digital Lock Output Frequency"
    _outputChannels = {"OutputFrequency": "MHz", "Harmonic": ""}

    def __init__(self, name, config, globalDict, instrument="localhost:16888"):
        logger = logging.getLogger(__name__)
        ExternalParameterBase.__init__(self, name, config, globalDict)
        logger.info( "trying to open '{0}'".format(instrument) )
        host, port = instrument.split(':')
        self.instrument = Client((host, int(port)), authkey=b"yb171")
        logger.info( "opened {0}".format(instrument) )
        self.setDefaults()
        self.initializeChannelsToExternals()
        
    def setValue(self, channel, v):
        self.instrument.send( ('set{0}'.format(channel), (v, ) ) )
        result = self.instrument.recv()
        if isinstance(result, Exception):
            raise result
        return result
        
    def getValue(self, channel):
        self.instrument.send( ('get{0}'.format(channel), tuple() ) )
        result = self.instrument.recv()
        if isinstance(result, Exception):
            raise result
        return result
        
    def close(self):
        del self.instrument
        
