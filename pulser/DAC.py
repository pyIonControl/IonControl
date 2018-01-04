# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import struct

from pulser.PulserHardwareClient import check
from modules.quantity import Q
from modules.Expression import Expression
from pulser.Encodings import encode, decode
from pulser.PulserConfig import DAADInfo
from gui.ExpressionValue import ExpressionValue
from modules.descriptor import SetterProperty


class DACException(Exception):
    pass


class DACChannelSetting(object):
    expression = Expression()
    def __init__(self, globalDict=None ):
        self._globalDict = None
        self._voltage = ExpressionValue(None, self._globalDict)
        self.enabled = False
        self.name = ""
        self.resetAfterPP = False
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('resetAfterPP', False)
        self.__dict__.setdefault('_globalDict', dict())

    def __getstate__(self):
        dictcopy = dict(self.__dict__)
        dictcopy.pop('_globalDict', None)
        return dictcopy
        
    @property
    def outputVoltage(self):
        return self._voltage.value if self.enabled else Q(0, 'V')

    @property
    def globalDict(self):
        return self._globalDict
    
    @globalDict.setter
    def globalDict(self, globalDict):
        self._globalDict = globalDict
        self._voltage.globalDict = globalDict
        
    @property
    def voltage(self):
        return self._voltage.value
    
    @voltage.setter
    def voltage(self, v):
        self._voltage.value = v
    
    @property
    def voltageText(self):
        return self._voltage.string
    
    @voltageText.setter
    def voltageText(self, s):
        self._voltage.string = s
        
    @SetterProperty
    def onChange(self, onChange):
        self._voltage.valueChanged.connect(onChange)


class CombineWrites:
    def __init__(self, dac):
        self.restoreValue = True
        self.dac = dac

    def __enter__(self):
        self.restoreValue = self.dac.autoFlush
        self.dac.autoFlush = False
        return self.dac

    def __exit__(self, exittype, value, traceback):
        self.dac.autoFlush = self.restoreValue
        self.dac.flush()


class DAC:
    def __init__(self, pulser):
        self.commandBuffer = list()
        self.autoFlush = True
        self.pulser = pulser
        config = self.pulser.pulserConfiguration()
        self.numChannels = config.dac.numChannels if config else 0
        self.dacInfo = config.dac if config else DAADInfo() 
        self.sendCommand(0, 7, 1) # enable internal reference
        self.sendCommand(0, 7, 1) # enable internal reference works if done twice, don't ask me why

    def rawToMagnitude(self, raw):
        return decode( raw, self.dacInfo.encoding )

    def setVoltage(self, channel, voltage, autoApply=False, applyAll=False):
        intVoltage = encode( voltage, self.dacInfo.encoding )
        code =  (2 if applyAll else 3) if autoApply else 0
        self.sendCommand(channel, code, intVoltage)
        return intVoltage

    def flush(self):
        self.pulser.setMultipleExtendedWireIn(self.commandBuffer)
        self.commandBuffer = list()

    def sendCommand(self, channel, cmd, data):
        logger = logging.getLogger(__name__)
        if self.pulser:
            self.commandBuffer.extend([(0x12, data),
                                       (0x1e, (1 << 14) | ((channel & 0xff) << 4) | (cmd & 0xf))])
            if self.autoFlush:
                self.flush()
        else:
            logger.warning( "Pulser not available" )
            
    def update(self, channelmask):
        pass
        
        
if __name__ == "__main__":
    ad = DAC(None)
    