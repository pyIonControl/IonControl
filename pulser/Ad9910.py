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

class Ad9910Exception(Exception):
    pass

class Ad9910:
    channels = 2
    def __init__(self, pulser):
        self.pulser = pulser
        self.frequency = [None]*self.channels
        self.phase = [None]*self.channels
        self.amplitude = [None]*self.channels

    def rawToMagnitude(self, raw):
        return Q(1000, ' MHz') * (raw / float(2**32))

    def setFrequency(self, channel, frequency, even=False):
        intFrequency = int(round(2**32 * frequency.m_as('GHz'))) & 0xffffffff
        self.sendCommand(channel+6, 0, intFrequency)
        return intFrequency
    
    def setFrequencyRaw(self, channel, intFrequency):
        self.sendCommand(channel+6, 0, intFrequency)
        return intFrequency        
    
    def setPhase(self, channel, phase):
        intPhase = int(round(2**16 * phase.m_as('rad')/(2*math.pi))) # AD9910 has 16 bit phase.
        self.sendCommand(channel+6, 1, intPhase & 0xffff)
    
    def setAmplitude(self, channel, amplitude):
        intAmplitude = int(round((amplitude*16.)/(2**14-1)*(2**14))) # AD9910 has 14 bit amplitude, uses a "scale factor." To use it like the AD9912s,I am scaling the typical 0-1023 range by *16.
        self.sendCommand(channel+6, 2, intAmplitude & 0x3fff )
        
    def setRampStep(self, channel, rampType, rampStepUp, rampStepDown):
        if (rampType==0): # frequency ramp sent in MHz
            intRampStepUp = int(round(2**32 * rampStepUp/1000.)) & 0xffffffff # assuming fsysclk is 1GHz, convert rampStep to GHz see AD9910 datasheet
            intRampStepDown = int(round(2**32 * rampStepDown/1000.)) & 0xffffffff
        elif (rampType==1): # phase ramp sent in deg
            intRampStepUp = int(round(rampStepUp*(2**29)/45)) & 0xffffffff # for rad would use stepRad*2^31/pi
            intRampStepDown = int(round(rampStepDown*(2**29)/45)) & 0xffffffff
        else: # amplitude scan sent in 0-1023 arb DDS units
            intRampStepUp = int(round(rampStepUp*16/(2**14-1)*2**32)) & 0xffffffff
            intRampStepDown = int(round(rampStepDown*16/(2**14-1)*2**32)) & 0xffffffff
        intRampStepUp = int(round(rampStepUp)) & 0xffffffff
        intRampStepDown = int(round(rampStepDown)) & 0xffffffff
        intRampCombined = ((intRampStepDown << 32) | intRampStepUp) # down,up
        self.sendCommand(channel+6, 3, intRampCombined )
        
    def setRampTimeStep(self, channel, negSlopeRate, posSlopeRate):
        intNegSlopeRate = int(round(negSlopeRate/4.)) & 0xffff
        intPosSlopeRate = int(round(posSlopeRate/4.)) & 0xffff
        intSlopeCombined = ((intNegSlopeRate << 16) | intPosSlopeRate)
        self.sendCommand(channel+6, 4, intSlopeCombined)
        
    def setRampLimits(self, channel, rampType, rampMin, rampMax):
        if (rampType==0): # frequency ramp
            intRampMin = int(round(2**32 * rampMin)) & 0xffffffff
            intRampMax = int(round(2**32 * rampMax)) & 0xffffffff
        elif (rampType==1): # phase ramp
            intRampMin = int(round(2**16 * rampMin/(2*math.pi))) & 0xffffffff
            intRampMax = int(round(2**16 * rampMax/(2*math.pi))) & 0xffffffff
        else: # amplitude scan
            intRampMin = int(round(rampMin/1023.0*(2**14))) & 0xffffffff
            intRampMax = int(round(rampMax/1023.0*(2**14))) & 0xffffffff
        intLimitsCombined = ((intRampMax << 32) | intRampMin)
        self.sendCommand(channel+6, 5, intLimitsCombined)
        
    def setCFR2register(self, channel, rampEnable, rampDestination, noDwellHigh, noDwellLow):
        intRampEnable = int(rampEnable) & 0x1
        intRampDestination = int(rampDestination) & 0x3
        intNoDwellHigh = int(noDwellHigh) & 0x1
        intNoDwellLow = int(noDwellLow) & 0x1
        intCFR2Combined = (intRampDestination << 3) | (intRampEnable << 2) | (intNoDwellHigh << 1) | (intNoDwellLow)
        self.sendCommand(channel+6, 6, intCFR2Combined)
        
        
    def sendCommand(self, channel, cmd, data):
        logger = logging.getLogger(__name__)
        if self.pulser:
            check( self.pulser.SetWireInValue(0x03, (channel & 0xf)<<4 | (cmd & 0xf) ), "Ad9910" ) 
            self.pulser.WriteToPipeIn(0x84, bytearray(struct.pack('=HQ', 0x12, data)) )
            self.pulser.UpdateWireIns()
            check( self.pulser.ActivateTriggerIn(0x40, 1), "Ad9910 trigger") # Currently I am setting 9910s as channels 7&8 (6&7 starting from 0)
            self.pulser.UpdateWireIns()
        else:
            logger.error( "Pulser not available" )
        
    def update(self, channelmask):
        logger = logging.getLogger(__name__)
        if self.pulser:
            check( self.pulser.SetWireInValue(0x08, channelmask & 0xff), "Ad9910 apply" )
            self.pulser.UpdateWireIns()
            self.pulser.ActivateTriggerIn(0x41, 2)
        else:
            logger.error( "Pulser not available" )
        
    def reset(self, mask):
        logger = logging.getLogger(__name__)
        if self.pulser:
            #if mask & 0x3: check( self.pulser.ActivateTriggerIn(0x42,0), "DDS AD9910 Reset board 0" )
            #if mask & 0xc: check( self.pulser.ActivateTriggerIn(0x42,1), "DDS AD9910 Reset board 1" )
            #if mask & 0x30: check( self.pulser.ActivateTriggerIn(0x42,2), "DDS AD9910 Reset board 2" )
            check( self.pulser.ActivateTriggerIn(0x42, 3), "DDS AD9910 Reset board" )
        else:
            logger.error( "Pulser not available" )

        
