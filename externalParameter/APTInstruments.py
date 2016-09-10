# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ctypes

import logging
from externalParameter.ExternalParameterBase import ExternalParameterBase
from modules.quantity import Q

HWTYPE_BSC001 = 11  # // 1 Ch benchtop stepper driver
HWTYPE_BSC101 = 12  # // 1 Ch benchtop stepper driver
HWTYPE_BSC002 = 13  # // 2 Ch benchtop stepper driver
HWTYPE_BDC101 = 14  # // 1 Ch benchtop DC servo driver
HWTYPE_SCC001 = 21  # // 1 Ch stepper driver card (used within BSC102,103 units)
HWTYPE_DCC001 = 22  # // 1 Ch DC servo driver card (used within BDC102,103 units)
HWTYPE_ODC001 = 24  # // 1 Ch DC servo driver cube
HWTYPE_OST001 = 25  # // 1 Ch stepper driver cube
HWTYPE_MST601 = 26  # // 2 Ch modular stepper driver module
HWTYPE_TST001 = 29  # // 1 Ch Stepper driver T-Cube
HWTYPE_TDC001 = 31  # // 1 Ch DC servo driver T-Cube
HWTYPE_LTSXXX = 42  # // LTS300/LTS150 Long Travel Integrated Driver/Stages
HWTYPE_L490MZ = 43  # // L490MZ Integrated Driver/Labjack
HWTYPE_BBD10X = 44  # // 1/2/3 Ch benchtop brushless DC servo driver

APTDll = None


def loadDll(path):
    global APTDll
    APTDll = ctypes.WinDLL(path)


class APTError(Exception):
    pass


class APTInstrument(object):
    def open(self, instrument, HWType=HWTYPE_TDC001):
        if APTDll.APTInit() != 0:
            raise APTError("APT Dll initialization failed")
        plNumUnits = ctypes.c_long()
        if APTDll.GetNumHWUnitsEx(HWType, ctypes.byref(plNumUnits)) != 0 or plNumUnits.value == 0:
            raise APTError("APT No Hardware devices found")
        self.plSerialNumber = ctypes.c_long()
        APTDll.GetHWSerialNumEx(HWTYPE_TDC001, 0, ctypes.byref(self.plSerialNumber))
        logging.getLogger(__name__).info("Found APT device serial number {0}".format(self.plSerialNumber.value))
        if APTDll.InitHWDevice(self.plSerialNumber) != 0:
            raise APTError("Device initialization failed serial number {0}".format(self.plSerialNumber.value))
        self._minpos = ctypes.c_float()
        self._maxpos = ctypes.c_float()
        self._pitch = ctypes.c_float()
        self._units = ctypes.c_long()
        APTDll.MOT_GetStageAxisInfo(self.plSerialNumber, ctypes.byref(self._minpos), ctypes.byref(self._maxpos),
                                    ctypes.byref(self._units), ctypes.byref(self._pitch))
        logging.getLogger(__name__).info(
            "APT min {0} max{1} units {2} pitch {3}".format(self._minpos.value, self._maxpos.value, self._units.value,
                                                            self._pitch.value))

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
        if APTDll.MOT_MoveAbsoluteEx(self.plSerialNumber, pos, wait) != 0:
            raise APTError("Error setting position")

    def motionRunning(self):
        status = ctypes.c_ulong()
        APTDll.MOT_GetStatusBits(self.plSerialNumber, ctypes.byref(status))
        # print "running", hex(status.value), hex(status.value & 0x30)
        return bool(status.value & 0x30)

    def close(self):
        APTDll.APTCleanUp()


class APTRotation(ExternalParameterBase):
    className = "APT Rotation"
    _outputChannels = {None: ""}

    def __init__(self, name, config, globalDict, instrument="COM3"):
        logger = logging.getLogger(__name__)
        ExternalParameterBase.__init__(self, name, config, globalDict)
        logger.info("trying to open '{0}'".format(instrument))
        self.instrument = APTInstrument()
        self.instrument.open(instrument)
        self.instrument.homeSearch()
        logger.info("opened {0}".format(instrument))
        self.setDefaults()
        self.initializeChannelsToExternals()
        self.lastTargetValue = None
        if self.settings.limit > self.instrument.maxPos:
            self.settings.limit = Q(self.instrument.maxPos, '')

    def setDefaults(self):
        ExternalParameterBase.setDefaults(self)
        self.settings.__dict__.setdefault('limit', Q(360))  # if True go to the target value in one jump
        self.settings.__dict__.setdefault('belowMargin', Q(0))  # if True go to the target value in one jump

    def _setValue(self, channel, v):
        if v > self.settings.limit:
            v = self.setting.limit
        self.instrument.position = float(v)

    def getValue(self, channel):
        return Q(self.instrument.position)

    def paramDef(self):
        superior = ExternalParameterBase.paramDef(self)
        superior.append({'name': 'limit', 'type': 'magnitude', 'value': self.settings.limit})
        superior.append({'name': 'belowMargin', 'type': 'magnitude', 'value': self.settings.belowMargin,
                         'tip': 'if not zero: if coming from above always go that far below and then up'})
        return superior

    def close(self):
        self.instrument.close()
        del self.instrument

    def setValue(self, channel, value):
        reported = self.getValue(channel)
        if self.instrument.motionRunning():
            return reported, False
        if value != self.lastTargetValue:
            if self.lastTargetValue is None or value < self.lastTargetValue:
                self._setValue(channel, value - self.settings.belowMargin)
                self.lastTargetValue = value - self.settings.belowMargin
                return reported, False
            else:
                self._setValue(channel, value)
                self.lastTargetValue = value
        arrived = not self.instrument.motionRunning()
        if arrived:
            self.lastTargetValue = None  # setting it to None so we re-send the value if the user initiates a new write
        return reported, arrived


if __name__ == "__main__":
    a = APTRotation("APTRotation", dict(), "")
    print(a.getValue(None))
    a.setValue(None, 10)
    print(a.getValue(None))
    a.close()
