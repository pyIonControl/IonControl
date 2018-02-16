# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from externalParameter.ExternalParameterBase import ExternalParameterBase
import logging
from modules.quantity import Q
from .qtHelper import qtHelper

import grpc
from externalParameter.labbricksproto_pb2 import DeviceRequest, DeviceSetIntRequest, DeviceSetBoolRequest
from externalParameter.labbricksproto_pb2_grpc import LabbricksStub

Servers = dict()

class LabBrickError(Exception):
    pass


class RemoteLabBrick(object):
    @staticmethod
    def collectInformation():
        instrumentMap = dict()
        for name, url in Servers.items():
            channel = grpc.insecure_channel(url)
            stub = LabbricksStub(channel)
            r = DeviceRequest()
            for info in stub.DeviceInfo(r):
                instrumentMap[(name, info.ModelName, info.SerialNumber)] = (url, info.ModelName, info.SerialNumber)
        return instrumentMap

    def __init__(self, instrument):
        self.name, self.model, serial = instrument.split("_")
        self.serial = int(serial)
        self.instrumentMap = self.collectInformation()
        self.server, _, _ = self.instrumentMap[(self.name, self.model, self.serial)]
        self.deviceInfo = None
        self.deviceState = None
        try:
            channel = grpc.insecure_channel(self.server)
            stub = LabbricksStub(channel)
            r = DeviceRequest()
            r.ModelName = self.model
            r.SerialNumber = self.serial
            for info in stub.DeviceInfo(r):
                self.minFrequency = Q(10 * info.MinFreq, "Hz")
                self.maxFrequency = Q(10 * info.MaxFreq, "Hz")
                self.minPower = info.MinPwr * 0.25  # this is in dBm
                self.maxPower = info.MaxPwr * 0.25  # this is in dBm
                self.deviceInfo = info
            for state in stub.DeviceState(r):
                self.deviceState = state
        except KeyError:
            raise LabBrickError("LabBrick Model '{}' serial number {} is not available on server {}".format(model, serial, server))

    def close(self):
        pass

    def _getUpdatedState(self):
        channel = grpc.insecure_channel(self.server)
        stub = LabbricksStub(channel)
        r = DeviceRequest()
        r.ModelName = self.model
        r.SerialNumber = self.serial
        for state in stub.DeviceState(r):
            # self._power = state.PowerLevel
            # self._frequency = Q(10 * state.Frequency, " Hz")
            self.deviceState = state

    @property
    def rfOn(self):
        self._getUpdatedState()
        return self.deviceState.RFOn

    @rfOn.setter
    def rfOn(self, on):
        channel = grpc.insecure_channel(self.server)
        stub = LabbricksStub(channel)
        r = DeviceSetBoolRequest()
        r.ModelName = self.model
        r.SerialNumber = self.serial
        r.Data = on
        self.deviceState = stub.SetRFOn(r)

    @property
    def power(self):
        self._getUpdatedState()
        return self.deviceState.PowerLevel / 4

    @power.setter
    def power(self, power_in_dBm):
        if self.minPower <= power_in_dBm <= self.maxPower:
            channel = grpc.insecure_channel(self.server)
            stub = LabbricksStub(channel)
            r = DeviceSetIntRequest()
            r.ModelName = self.model
            r.SerialNumber = self.serial
            r.Data = int(power_in_dBm * 4)
            self.deviceState = stub.SetPower(r)
        else:
            raise LabBrickError("Labbrick: Power {} is out of range ({}, {})".format(power_in_dBm, self.minPower, self.maxPower))

    @property
    def frequency(self):
        self._getUpdatedState()
        return Q(10 * self.deviceState.Frequency, " Hz").simplify()

    @frequency.setter
    def frequency(self, frequency):
        if self.minFrequency <= frequency <= self.maxFrequency:
            channel = grpc.insecure_channel(self.server)
            stub = LabbricksStub(channel)
            r = DeviceSetIntRequest()
            r.ModelName = self.model
            r.SerialNumber = self.serial
            r.Data = int(frequency.m_as('Hz') / 10)
            self.deviceState = stub.SetFrequency(r)
        else:
            raise LabBrickError("Labbrick: Frequency {} is out of range ({}, {})".format(frequency, self.minFrequency, self.maxFrequency))


class RemoteLabBrickInstrument(ExternalParameterBase):
    className = "RemoteLabBrick"
    _outputChannels = {"frequency": "Hz", "power": ""}
    _inputChannels = {"frequency": "Hz", "power": ""}

    def __init__(self, name, config, globalDict, instrument):
        self.instrument = None
        ExternalParameterBase.__init__(self, name, config, globalDict)
        logger = logging.getLogger(__name__)
        logger.info("trying to open '{0}'".format(instrument))
        self.instrument = RemoteLabBrick(instrument)
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
        map = RemoteLabBrick.collectInformation()
        return ["{}_{}_{}".format(name, model, serial) for name, model, serial in map.keys()]

    def close(self):
        del self.instrument

    def setDefaults(self):
        ExternalParameterBase.setDefaults(self)
        self.settings.__dict__.setdefault('rfOn', True)

    def paramDef(self):
        superior = ExternalParameterBase.paramDef(self)
        superior.append({'name': 'rfOn', 'type': 'bool', 'value': self.instrument.rfOn if self.instrument else True})
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
