# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import math
import struct

from pulser.PulserHardwareClient import check
from modules.quantity import Q


class Ad9912Exception(Exception):
    pass


class CombineWrites:
    def __init__(self, ad9912):
        self.ad9912 = ad9912
        self.restoreValue = True

    def __enter__(self):
        self.restoreValue = self.ad9912.autoFlush
        self.ad9912.autoFlush = False
        return self.ad9912

    def __exit__(self, exittype, value, traceback):
        self.ad9912.autoFlush = self.restoreValue
        self.ad9912.flush()


class Ad9912:
    def __init__(self, pulser):
        self.pulser = pulser
        self.autoFlush = True
        self.commandBuffer = list()

    def rawToMagnitude(self, raw):
        return Q(1000, ' MHz') * (raw / float(2**48))

    def setSquareEnabled(self, channel, enable):
        self.sendCommand(channel, 3, 1 if enable else 0)

    def setFrequency(self, channel, frequency):
        intFrequency = int(round(2**48 * frequency.m_as('GHz'))) & 0xffffffffffff
        self.sendCommand(channel, 0, intFrequency)
        return intFrequency
    
    def setFrequencyRaw(self, channel, intFrequency):
        self.sendCommand(channel, 0, intFrequency)
        #self.sendCommand(channel, 0, intFrequency >> 16 )
        #self.sendCommand(channel, 4, intFrequency & 0xffff ) # Frequency fine
        return intFrequency        
    
    def setPhase(self, channel, phase):
        intPhase = int(round(2**14 * float(phase)/(2*math.pi)))
        self.sendCommand(channel, 1, intPhase & 0x3fff )
    
    def setAmplitude(self, channel, amplitude):
        intAmplitude = int(round(amplitude))
        self.sendCommand(channel, 2, intAmplitude & 0x3ff )

    def flush(self):
        if self.commandBuffer:
            self.pulser.setMultipleExtendedWireIn(self.commandBuffer)
            self.commandBuffer = list()

    def sendCommand(self, channel, cmd, data):
        if self.pulser:
            self.commandBuffer.extend([(0x12, data),
                                       (0x1e, (1 << 15) | (channel & 0xff) << 4 | (cmd & 0xf))])
            if self.autoFlush:
                self.flush()
        else:
            logging.getLogger(__name__).warning("Pulser not available")
        
    def update(self, channelmask):
        logger = logging.getLogger(__name__)
        if self.pulser:
            self.pulser.WriteToPipeIn(0x84, bytearray(struct.pack('=HQ', 0x11, channelmask)) )
            self.pulser.ActivateTriggerIn(0x41, 2)
        else:
            logger.warning( "Pulser not available" )
        
    def reset(self, mask):
        logger = logging.getLogger(__name__)
        if self.pulser:
            check(  self.pulser.SetWireInValue(0x04, mask&0xffff ), "AD9912 reset mask" )
            self.pulser.UpdateWireIns()
            check( self.pulser.ActivateTriggerIn(0x42, 0), "DDS Reset" )
        else:
            logger.warning( "Pulser not available" )

