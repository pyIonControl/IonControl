# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import namedtuple

from externalParameter.ExternalParameterBase import ExternalParameterBase
import logging
from modules.quantity import Q
from .qtHelper import qtHelper

import grpc
from externalParameter.labbricksproto_pb2 import DeviceRequest, DeviceSetIntRequest, DeviceSetBoolRequest
from externalParameter.labbricksproto_pb2_grpc import LabbricksStub
from ProjectConfig.Project import currentProject
Servers = dict()

RemoteLabBrickConfig = namedtuple("RemoteLabBrickConfig", "name url auth clientKey clientCertificate rootCertificate")

class LabBrickError(Exception):
    pass


class RemoteLabBrick(object):
    @staticmethod
    def collectInformation():
        instrumentMap = dict()
        for name, cfg in Servers.items():
            try:  # try without authentication
                if cfg.auth:
                    creds = grpc.ssl_channel_credentials(root_certificates=open(cfg.rootCertificate, 'rb').read(),
                                                         private_key=open(cfg.clientKey, 'rb').read(),
                                                         certificate_chain=open(cfg.clientCertificate, 'rb').read())
                    channel = grpc.secure_channel(cfg.url, creds)
                else:
                    channel = grpc.insecure_channel(cfg.url)
                stub = LabbricksStub(channel)
                r = DeviceRequest()
                for info in stub.DeviceInfo(r):
                    instrumentMap[(name, info.ModelName, info.SerialNumber)] = cfg
            except grpc.RpcError as e:
                raise AttributeError("connection to Labbricks server {} failed with error {}".format(cfg.url, e))
        return instrumentMap

    def __init__(self, instrument):
        self.name, self.model, serial = instrument.split("_")
        self.serial = int(serial)
        self.instrumentMap = self.collectInformation()
        self.cfg = self.instrumentMap[(self.name, self.model, self.serial)]
        self.deviceInfo = None
        self.deviceState = None
        self.channel = None
        self.stub = None
        self._getInfo()

    def _getInfo(self):
        self._open()
        r = DeviceRequest()
        r.ModelName = self.model
        r.SerialNumber = self.serial
        for info in self.stub.DeviceInfo(r):
            self.minFrequency = Q(10 * info.MinFreq, "Hz")
            self.maxFrequency = Q(10 * info.MaxFreq, "Hz")
            self.minPower = info.MinPwr * 0.25  # this is in dBm
            self.maxPower = info.MaxPwr * 0.25  # this is in dBm
            self.deviceInfo = info
        for state in self.stub.DeviceState(r):
            self.deviceState = state

    def _open(self):
        if self.channel is None or self.channel._channel.check_connectivity_state(True) > 2:
            try:
                cfg = self.cfg
                if cfg.auth:
                    creds = grpc.ssl_channel_credentials(root_certificates=open(cfg.rootCertificate, 'rb').read(),
                                                         private_key=open(cfg.clientKey, 'rb').read(),
                                                         certificate_chain=open(cfg.clientCertificate, 'rb').read())
                    self.channel = grpc.secure_channel(cfg.url, creds)
                else:
                    self.channel = grpc.insecure_channel(cfg.url)
                self.stub = LabbricksStub(self.channel)
            except KeyError:
                raise LabBrickError("LabBrick Model '{}' serial number {} is not available on server {}".format(self.model, self.serial, cfg.url))

    def close(self):
        pass

    def _getUpdatedState(self):
        self._open()
        r = DeviceRequest()
        r.ModelName = self.model
        r.SerialNumber = self.serial
        for state in self.stub.DeviceState(r):
            # self._power = state.PowerLevel
            # self._frequency = Q(10 * state.Frequency, " Hz")
            self.deviceState = state

    @property
    def rfOn(self):
        self._getUpdatedState()
        return self.deviceState.RFOn

    @rfOn.setter
    def rfOn(self, on):
        self._open()
        r = DeviceSetBoolRequest()
        r.ModelName = self.model
        r.SerialNumber = self.serial
        r.Data = on
        self.deviceState = self.stub.SetRFOn(r)

    @property
    def power(self):
        self._getUpdatedState()
        return self.deviceState.PowerLevel / 4

    @power.setter
    def power(self, power_in_dBm):
        if self.minPower <= power_in_dBm <= self.maxPower:
            self._open()
            r = DeviceSetIntRequest()
            r.ModelName = self.model
            r.SerialNumber = self.serial
            r.Data = int(power_in_dBm * 4)
            self.deviceState = self.stub.SetPower(r)
        else:
            raise LabBrickError("Labbrick: Power {} is out of range ({}, {})".format(power_in_dBm, self.minPower, self.maxPower))

    @property
    def frequency(self):
        self._getUpdatedState()
        return Q(10 * self.deviceState.Frequency, " Hz").simplify()

    @frequency.setter
    def frequency(self, frequency):
        if self.minFrequency <= frequency <= self.maxFrequency:
            self._open()
            r = DeviceSetIntRequest()
            r.ModelName = self.model
            r.SerialNumber = self.serial
            r.Data = int(frequency.m_as('Hz') / 10)
            self.deviceState = self.stub.SetFrequency(r)
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
