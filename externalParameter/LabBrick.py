# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ctypes
from externalParameter.ExternalParameterBase import ExternalParameterBase
import logging
from modules.quantity import Q


def loadDll(path):
    global LabBrickDll
    LabBrickDll = ctypes.WinDLL(path)


class LabBrickError(Exception):
    pass


class LabBrick(object):
    @staticmethod
    def collectInformation():
        numDevices = LabBrickDll.fnLMS_GetNumDevices()
        data = (ctypes.c_uint * numDevices)()
        LabBrickDll.fnLMS_GetDevInfo(data)
        instrumentMap = dict()
        for deviceID in data:
            serial = LabBrickDll.fnLMS_GetSerialNumber(deviceID)
            s = ctypes.create_unicode_buffer(32)
            LabBrickDll.fnLMS_GetModelNameW(deviceID, s)
            model = s.value
            instrumentMap[(model, serial)] = tuple([deviceID, serial, model])
        return instrumentMap

    def __init__(self, instrument):
        model, serial = instrument.split("_")
        serial = int(serial)
        self.instrumentMap = self.collectInformation()
        try:
            self.deviceID, self.serial, self.model = self.instrumentMap[(model, serial)]
            self.minFrequency = Q(10 * LabBrickDll.fnLMS_GetMinFreq(self.deviceID), "Hz")
            self.maxFrequency = Q(10 * LabBrickDll.fnLMS_GetMaxFreq(self.deviceID), "Hz")
            self.minPower = LabBrickDll.fnLMS_GetMinPwr(self.deviceID) * 0.25  # this is in dBm
            self.maxPower = LabBrickDll.fnLMS_GetMaxPwr(self.deviceID) * 0.25  # this is in dBm
            self._rfOn = bool(LabBrickDll.fnLMS_GetRFOn(self.deviceID))
            self._useInternalReference = bool(LabBrickDll.fnLMS_GetUseInternalRef(self.deviceID))
            self._power = LabBrickDll.fnLMS_GetAbsPowerLevel(self.deviceID)
            self._frequency = Q(10 * LabBrickDll.fnLMS_GetFrequency(self.deviceID), " Hz")
        except KeyError:
            raise LabBrickError("LabBrick Model '{}' serial number {} is not available".format(model, serial))

    def close(self):
        LabBrickDll.fnLMS_CloseDevice(self.deviceID)
        self.deviceID = None

    @property
    def rfOn(self):
        self._rfOn = bool(LabBrickDll.fnLMS_GetRFOn(self.deviceID))
        return self._rfOn

    @rfOn.setter
    def rfOn(self, on):
        LabBrickDll.fnLMS_SetRFOn(self.deviceID, on)
        self._rfOn = on

    @property
    def useInternalReference(self):
        self._useInternalReference = bool(LabBrickDll.fnLMS_GetUseInternalRef(self.deviceID))
        return self._useInternalReference

    @useInternalReference.setter
    def useInternalReference(self, useInternal):
        LabBrickDll.fnLMS_SetUseInternalRef(self.deviceID, useInternal)
        self._useInternalReference = useInternal

    @property
    def power(self):
        self._power = LabBrickDll.fnLMS_GetAbsPowerLevel(self.deviceID)
        return self._power

    @power.setter
    def power(self, power_in_dBm):
        if self.minPower <= power_in_dBm <= self.maxPower:
            LabBrickDll.fnLMS_SetPowerLevel(self.deviceID, power_in_dBm * 4)
            self._power = power_in_dBm * 4
        else:
            raise LabBrickError("Labbrick: Power {} is out of range ({}, {})".format(power_in_dBm, self.minPower, self.maxPower))

    @property
    def frequency(self):
        self._frequency = Q(10 * LabBrickDll.fnLMS_GetFrequency(self.deviceID), " Hz")
        return self._frequency

    @frequency.setter
    def frequency(self, frequency):
        if self.minFrequency <= frequency <= self.maxFrequency:
            LabBrickDll.fnLMS_SetFrequency(self.deviceID, frequency.m_as('Hz') / 10)
            self._frequency = frequency
        else:
            raise LabBrickError("Labbrick: Frequency {} is out of range ({}, {})".format(frequency, self.minFrequency, self.maxFrequency))


class LabBrickInstrument(ExternalParameterBase):
    className = "LabBrick"
    _outputChannels = {"frequency": "Hz", "power": ""}
    _inputChannels = {"frequency": "Hz", "power": ""}

    def __init__(self, name, config, globalDict, instrument):
        logger = logging.getLogger(__name__)
        ExternalParameterBase.__init__(self, name, config, globalDict)
        logger.info("trying to open '{0}'".format(instrument))
        self.instrument = LabBrick(instrument)
        logger.info("opened {0}".format(instrument))
        self.setDefaults()
        self.initializeChannelsToExternals()

    def setValue(self, channel, v):
        setattr(self.instrument, channel, v)
        return v

    def getValue(self, channel):
        return getattr(self.instrument, channel)

    def getExternalValue(self, channel):
        return getattr(self.instrument, channel)

    @staticmethod
    def connectedInstruments():
        map = LabBrick.collectInformation()
        return ["{}_{}".format(model, serial) for model, serial in map.keys()]

    def close(self):
        del self.instrument
