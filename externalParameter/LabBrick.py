# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ctypes
from externalParameter.ExternalParameterBase import ExternalParameterBase
import logging

LabBrickDll = ctypes.WinDLL("dll/vnx_fmsynth.dll")

class LabBrickError(Exception):
    pass

class LabBrick(object):
    def open(self, instrument, HWType=HWTYPE_TDC001):
        if APTDll.APTInit()!=0:
            raise APTException("APT Dll initialization failed")
        plNumUnits = ctypes.c_long()
        if APTDll.GetNumHWUnitsEx( HWType, ctypes.byref(plNumUnits)) !=0 or plNumUnits.value==0:
            raise APTException("APT No Hardware devices found")
        self.plSerialNumber = ctypes.c_long()
        APTDll.GetHWSerialNumEx( HWTYPE_TDC001, 0, ctypes.byref(self.plSerialNumber))
        logging.getLogger(__name__).info("Found APT device serial number {0}".format(self.plSerialNumber.value))
        if APTDll.InitHWDevice( self.plSerialNumber )!=0:
            raise APTException("Device initialization failed serial number {0}".format(self.plSerialNumber.value))
        self._minpos = ctypes.c_float()
        self._maxpos = ctypes.c_float()
        self._pitch = ctypes.c_float()
        self._units = ctypes.c_long()
        APTDll.MOT_GetStageAxisInfo( self.plSerialNumber, ctypes.byref(self._minpos), ctypes.byref(self._maxpos), ctypes.byref(self._units), ctypes.byref(self._pitch) )
        logging.getLogger(__name__).info("APT min {0} max{1} units {2} pitch {3}".format(self._minpos.value, self._maxpos.value, self._units.value, self._pitch.value))

    def homeSearch(self):
        pass

    @property
    def minPos(self):
        return self._minpos.value

    @property
    def maxPos(self):
        return self._maxpos.value

    @property
    def position(self):
        pos = ctypes.c_float()
        APTDll.MOT_GetPosition(self.plSerialNumber, ctypes.byref(pos))
        return pos.value

    @position.setter
    def position(self, pos):
        wait = ctypes.c_bool(False)
        pos = ctypes.c_float(pos)
        if APTDll.MOT_MoveAbsoluteEx(self.plSerialNumber, pos, wait)!=0:
            raise APTException( "Error setting position")

    def motionRunning(self):
        status = ctypes.c_ulong()
        APTDll.MOT_GetStatusBits(self.plSerialNumber, ctypes.byref(status))
        #print "running", hex(status.value), hex(status.value & 0x30)
        return bool(status.value & 0x30)

    def close(self):
        APTDll.APTCleanUp()
