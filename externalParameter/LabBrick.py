# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ctypes
from externalParameter.ExternalParameterBase import ExternalParameterBase
import logging
from modules.quantity import Q
from .qtHelper import qtHelper


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
            LabBrickDll.fnLMS_InitDevice(self.deviceID)
            self.minFrequency = Q(10 * LabBrickDll.fnLMS_GetMinFreq(self.deviceID), "Hz")
            self.maxFrequency = Q(10 * LabBrickDll.fnLMS_GetMaxFreq(self.deviceID), "Hz")
            self.minPower = LabBrickDll.fnLMS_GetMinPwr(self.deviceID) * 0.25  # this is in dBm
            self.maxPower = LabBrickDll.fnLMS_GetMaxPwr(self.deviceID) * 0.25  # this is in dBm
            #self._rfOn = bool(LabBrickDll.fnLMS_GetRF_On(self.deviceID))
            self._extTTL = bool(LabBrickDll.fnLMS_SetUseExternalPulseMod(self.deviceID))
            self._useInternalReference = bool(LabBrickDll.fnLMS_GetUseInternalRef(self.deviceID))
            self._power = LabBrickDll.fnLMS_GetAbsPowerLevel(self.deviceID)
            self._frequency = Q(10 * LabBrickDll.fnLMS_GetFrequency(self.deviceID), " Hz")
        except KeyError:
            raise LabBrickError("LabBrick Model '{}' serial number {} is not available".format(model, serial))

    def close(self):
        LabBrickDll.fnLMS_CloseDevice(self.deviceID)
        self.deviceID = None

    @property
    def extTTL(self):
        self._extTTL = bool(LabBrickDll.fnLMS_SetUseExternalPulseMod(self.deviceID))
        return self._extTTL

    @extTTL.setter
    def extTTL(self, external):
        LabBrickDll.fnLMS_SetUseExternalPulseMod(self.deviceID, external)
        return self._extTTL

    @property
    def rfOn(self):
        self._rfOn = bool(LabBrickDll.fnLMS_GetRF_On(self.deviceID))
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
        self._power = LabBrickDll.fnLMS_GetAbsPowerLevel(self.deviceID) / 4
        return self._power

    @power.setter
    def power(self, power_in_dBm):
        if self.minPower <= power_in_dBm <= self.maxPower:
            LabBrickDll.fnLMS_SetPowerLevel(self.deviceID, int(power_in_dBm * 4))
            self._power = power_in_dBm * 4
        else:
            raise LabBrickError("Labbrick: Power {} is out of range ({}, {})".format(power_in_dBm, self.minPower, self.maxPower))

    @property
    def frequency(self):
        self._frequency = Q(10 * LabBrickDll.fnLMS_GetFrequency(self.deviceID), " Hz")
        return self._frequency.simplify()

    @frequency.setter
    def frequency(self, frequency):
        if self.minFrequency <= frequency <= self.maxFrequency:
            LabBrickDll.fnLMS_SetFrequency(self.deviceID, int(frequency.m_as('Hz') / 10))
            self._frequency = frequency
        else:
            raise LabBrickError("Labbrick: Frequency {} is out of range ({}, {})".format(frequency, self.minFrequency, self.maxFrequency))


class LabBrickInstrument(ExternalParameterBase):
    className = "LabBrick"
    _outputChannels = {"frequency": "Hz", "power": ""}
    _inputChannels = {"frequency": "Hz", "power": ""}

    def __init__(self, name, config, globalDict, instrument):
        self.instrument = None
        ExternalParameterBase.__init__(self, name, config, globalDict)
        logger = logging.getLogger(__name__)
        logger.info("trying to open '{0}'".format(instrument))
        self.instrument = LabBrick(instrument)
        logger.info("opened {0}".format(instrument))
        self.initializeChannelsToExternals()
        self.qtHelper = qtHelper()
        self.newData = self.qtHelper.newData
        self.setDefaults()

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

    def setDefaults(self):
        ExternalParameterBase.setDefaults(self)
        self.settings.__dict__.setdefault('rfOn', True)
        self.settings.__dict__.setdefault('useInternalReference', True)

    def paramDef(self):
        superior = ExternalParameterBase.paramDef(self)
        superior.append({'name': 'rfOn', 'type': 'bool', 'value': self.instrument.rfOn if self.instrument else True})
        superior.append({'name': 'useInternalReference', 'type': 'bool', 'value': self.instrument.useInternalReference if self.instrument else True})
        return superior

    def update(self, param, changes):
        """
        update the parameter, called by the signal of pyqtgraph parametertree
        """
        for param, change, data in changes:
            if change == 'value':
                setattr(self.settings, param.name(), data)
                setattr(self.instrument, param.name(), data)
            elif change == 'activated':
                getattr(self, param.opts['field'])()
