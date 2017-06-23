# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import math

from modules import quantity
from modules.quantity import Q, ureg, value, is_Q
from enum import Enum

timestep = Q(5.0, 'ns')


class Dimensions:
    time = ureg.second.dimensionality
    frequency = ureg.Hz.dimensionality
    voltage = ureg.V.dimensionality
    current = ureg.A.dimensionality
    dimensionless = ureg.dimensionless.dimensionality


Representation = Enum('Representation', 'TwosComplement Offset')


class EncodingError(Exception):
    pass


class Encoding:
    def __init__(self, maxvalue=None, bits=16, unit='', signed=True, representation=Representation.TwosComplement,
                 step=None, periodic=False, maskbits=None):
        self.bits = bits
        self.unit = unit
        self.signed = signed
        self.periodic = periodic
        if maxvalue is None:
            self.step = value(step, unit)
            self.maxvalue = self.step * ((1 << (self.bits - 1) - 1) if signed else (1 << self.bits) - 1)
            self.minvalue = -self.step * ((1 << (self.bits - 1)) if signed else 0)
        else:
            self.maxvalue = value(maxvalue, unit)
            self.minvalue = -self.maxvalue if signed else 0
            self.step = (self.maxvalue - self.minvalue) / (1 << self.bits) if step is None else step
        self.mask = ((1 << maskbits) - 1) if maskbits is not None else ((1 << self.bits) - 1)
        self.offsetValue = self.minvalue if representation == Representation.Offset and signed else 0

    def encode(self, v):
        if is_Q(v) and v.dimensionless:
            v = v.m  # TODO: do we want to warn here?
        else:
            v = value(v, self.unit)
        if self.minvalue <= v < self.maxvalue:
            v += self.offsetValue
            return int(round(v / self.step)) & self.mask
        elif self.periodic and self.minvalue == 0:
            v += self.offsetValue
            return int(round((v % self.maxvalue) / self.step)) & self.mask
        else:
            raise EncodingError("Value {0} out of range {1}, {2}".format(v, Q(self.minvalue, self.unit), Q(self.maxvalue, self.unit)))

    def decode(self, v):
        return v * self.step + self.offsetValue

    def decodeMg(self, v):
        return Q(self.decode(v), self.unit)


class BinaryEncoding(Encoding):
    def __init__(self, maxvalue=None, bits=16, unit='', signed=True, representation=Representation.TwosComplement,
                 step=None):
        super().__init__(maxvalue, bits, unit, signed, representation, step)
        if self.step != 1:
            raise EncodingError("BinaryEncoding must have step == 1")

    def encode(self, v):
        if not is_Q(v):
            v = v + self.offsetValue
        elif not v.dimensionless:
            v = v.m + self.offsetValue
        else:
            v = value(v, self.unit) + self.offsetValue
        if type(v) != int:
            v = int(round(v))
        if self.minvalue <= v <= self.maxvalue:
            return v & self.mask
        else:
            raise EncodingError("Value {0} out of range {1}, {2}".format(v, Q(self.minvalue, self.unit), Q(self.maxvalue, self.unit)))


unsigned64 = BinaryEncoding((1 << 64) - 1, 64, step=1, signed=False)
signagnostic64 = BinaryEncoding((1 << 64) - 1, 64, step=1, signed=True)

EncodingDict = {'AD9912_FRQ': Encoding(Q(1, 'GHz'), 48, 'Hz', signed=False),
                'AD9912_FRQ_SIGN': Encoding(Q(1, 'GHz'), 48, 'Hz', signed=True, maskbits=64),
                'AD9910_FRQ': Encoding(Q(1, 'GHz'), 32, 'Hz', signed=False),
                'AD9912_PHASE': Encoding(Q(360), 14, '', signed=False, periodic=True),
                'AD9910_PHASE': Encoding(Q(360), 16, '', signed=False, periodic=True),
                'ADC_VOLTAGE': Encoding(Q(5, 'V'), 12, 'V', signed=False),
                'ADCTI122S101_VOLTAGE': Encoding(Q(3.33, 'V'), 12, 'V', signed=False),
                'DAC8568_VOLTAGE': Encoding(Q(5, 'V'), 16, 'V', signed=False),
                'DAC5791_VOLTAGE': Encoding(Q(5, 'V'), 20, 'V', signed=True),
                'ADC7762_VOLTAGE': Encoding(Q(5, 'V'), 24, 'V', signed=True),
                'ADC7606_VOLTAGE': Encoding(Q(5, 'V'), 16, 'V', signed=True),
                'ADC7606_VOLTAGE_OFFSET': Encoding(Q(5, 'V'), 16, 'V', signed=True,
                                                   representation=Representation.Offset),
                Dimensions.time: Encoding(bits=48, unit='ns', signed=False, step=timestep),
                'None': signagnostic64,
                'TIME': Encoding(bits=48, unit='ns', signed=False, step=timestep),
                'unsigned64': unsigned64,
                'signed64': BinaryEncoding((1 << 63) - 1, 64, step=1, signed=True),
                'unsigned32': BinaryEncoding((1 << 32) - 1, 32, step=1, signed=False),
                'signed32': BinaryEncoding((1 << 31) - 1, 32, step=1, signed=True),
                'unsigned16': BinaryEncoding((1 << 16) - 1, 16, step=1, signed=False),
                'signed16': BinaryEncoding((1 << 15) - 1, 16, step=1, signed=True)}


def encodingValid(encodingname):
    return (not encodingname) or encodingname in EncodingDict


def encode(val, encoding=None):
    try:
        return EncodingDict[encoding].encode(val)
    except KeyError:
        if encoding:
            raise EncodingError("Undefined encoding '{0}'".format(encoding))
        if isinstance(val, ureg.Quantity):
            return EncodingDict.get(val.dimensionality, signagnostic64).encode(val)
        return signagnostic64.encode(val)


def decode(val, encoding):
    try:
        return EncodingDict[encoding].decode(val)
    except KeyError:
        return val


def decodeMg(val, encoding):
    try:
        return EncodingDict[encoding].decodeMg(val)
    except KeyError:
        return Q(val)

decodeQ = decodeMg