# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from pulser.Encodings import encode, decode, decodeQ, EncodingError, Dimensions
from modules.quantity import Q
import unittest
import math

timestep = Q(5, 'ns')

legacy_encodings = {'AD9912_FRQ': (1e9 / 2 ** 48, 'Hz', Dimensions.frequency, 0xffffffffffff),
             'AD9910_FRQ': (1e9 / 2 ** 32, 'Hz', Dimensions.frequency, 0xffffffff),
             'AD9912_PHASE': (360. / 2 ** 14, '', Dimensions.dimensionless, 0x3fff),
             'AD9910_PHASE': (360. / 2 ** 16, '', Dimensions.dimensionless, 0xffff),
             'ADC_VOLTAGE': (5. / 2 ** 12, 'V', Dimensions.voltage, 0xfff),
             'ADCTI122S101_VOLTAGE': (3.33 / 2 ** 12, 'V', Dimensions.voltage, 0xfff),
             'DAC8568_VOLTAGE': (5.0 / 2 ** 16, 'V', Dimensions.voltage, 0xffff),
             'ADC7606_VOLTAGE': (5.0 / 2 ** 15, 'V', Dimensions.voltage, 0xffff),
             'CURRENT': (1, 'A', Dimensions.current, 0xffffffff),
             'VOLTAGE': (1, 'V', Dimensions.voltage, 0xffffffff),
             'TIME': (5, 'ns', Dimensions.time, 0xffffffffffff),
             None: (1, '', Dimensions.dimensionless, 0xffffffffffffffff),
             'None': (1, '', Dimensions.dimensionless, 0xffffffffffffffff)}


def legacy_encode(value, encoding):
    if isinstance(value, Q):
        if tuple(value.dimensionality) == Dimensions.time:
            result = int((value / timestep).round())
        else:
            step, unit, _, mask = legacy_encodings[encoding]
            if not unit and not value.dimensionless:
                result = int(round((value.m) / step)) & mask
            else:
                result = int(round((value.m_as(unit) if unit else value.m) / step)) & mask
    else:
        if encoding:
            step, unit, _, mask = legacy_encodings[encoding]
            result = int(round(value / step)) & mask
        else:
            result = int(value)
    return result


def legacy_decode(val, encoding):
    step, unit, _, _ = legacy_encodings[encoding]
    return Q(val * step, unit)


class EncodingsTest(unittest.TestCase):
    def testDDS(self):
        self.assertEqual(encode(Q(500, 'MHz'), 'AD9912_FRQ'), 0x800000000000)
        self.assertEqual(encode(Q(500, 'MHz'), 'AD9912_FRQ'), legacy_encode(Q(500, 'MHz'), 'AD9912_FRQ'))

    def testTime(self):
        self.assertEqual(encode(Q(100, 'ns')), 20)
        self.assertEqual(encode(Q(100, 'us')), 20000)
        self.assertEqual(encode(Q(200, 'us')), 40000)
        with self.assertRaises(EncodingError):
            encode(Q(-100, 'ns'))

    def testFallback(self):
        self.assertEqual(encode(256), 256)
        self.assertEqual(encode(72057594037927937), 72057594037927937)
        self.assertEqual(encode(Q(6.076, 'kHz')), 6)
        self.assertEqual(encode(0xffffffffffffffff), 0xffffffffffffffff)
        self.assertEqual(encode(-1), 0xffffffffffffffff)

    def testUnsigned64(self):
        self.assertEqual(encode(256, 'unsigned64'), 256)
        self.assertEqual(encode(72057594037927937, 'unsigned64'), 72057594037927937)
        self.assertEqual(encode(0xffffffffffffffff, 'unsigned64'), 0xffffffffffffffff)
        with self.assertRaises(EncodingError):
            self.assertEqual(encode(-1, 'unsigned64'), 0xffffffffffffffff)

    def testADC7606_VOLTAGE(self):
        for value in (Q(2.345, 'V'), Q(-2.345, 'V'), Q(0.2, 'V'), Q(-0.2, 'V'), Q(4.99, 'V'),):
            self.assertEqual(encode(value, 'ADC7606_VOLTAGE'), legacy_encode(value, 'ADC7606_VOLTAGE'))
        for value in (Q(5.01, 'V'), Q(-5.01, 'V')):
            with self.assertRaises(EncodingError):
                encode(value, 'ADC7606_VOLTAGE')

    def testOldADC7606_VOLTAGE(self):
        print(hex(legacy_encode(Q(6.85, 'V'), 'ADC7606_VOLTAGE')))
        print(hex(encode(Q(-3.15, 'V'), 'ADC7606_VOLTAGE')))

    def testDefaults(self):
        self.assertEqual(legacy_encode(Q(2000, 'Hz'), None), encode(Q(2000, 'Hz')))
        self.assertEqual(legacy_encode(12345, None), encode(12345, None))
        self.assertEqual(legacy_encode(12345, None), encode(12345))
        self.assertEqual(encode(18374687063787175937), 18374687063787175937)
        self.assertEqual(encode(0xffffffffffffffff), 0xffffffffffffffff)

    def testADC(self):
        self.assertEqual(encode(Q(-5, 'V'), 'ADC7606_VOLTAGE_OFFSET'), 0)
        self.assertEqual(encode(Q(0, 'V'), 'ADC7606_VOLTAGE_OFFSET'), 0x8000)
        self.assertEqual(encode(Q(4.9999, 'V'), 'ADC7606_VOLTAGE_OFFSET'), 0xffff)
        with self.assertRaises(EncodingError):
            self.assertEqual(encode(Q(5, 'V'), 'ADC7606_VOLTAGE_OFFSET'), 0xffff)

    def testADCDecode(self):
        self.assertEqual(decodeQ(0, 'ADC7606_VOLTAGE_OFFSET'), Q(-5, 'V'))
        self.assertEqual(decodeQ(0x8000, 'ADC7606_VOLTAGE_OFFSET'), Q(0, 'V'))
        self.assertEqual(decodeQ(0xffff, 'ADC7606_VOLTAGE_OFFSET'), Q(4.999847412109375, 'V'))
        self.assertEqual(decodeQ(32768.0, 'ADC7606_VOLTAGE_OFFSET'), Q(0, 'V'))

    def testNoneEncoding(self):
        self.assertEqual(encode(Q(-5, 'MHz')), 18446744073709551611)

    def testPhase(self):
        self.assertEqual(encode(Q(0), 'AD9912_PHASE'), 0)
        self.assertEqual(encode(Q(360), 'AD9912_PHASE'), 0)

if __name__ == "__main__":
    unittest.main()