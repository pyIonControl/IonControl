# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import random
import unittest
import logging

import sys

from pulser.PulserHardwareServer import PulserHardwareServer

# firmware = r"C:\Users\pmaunz\PyCharmProjects\IonControl34\FPGA_Ions\IonControl-firmware-8Counters.bit"
from pulser.bitfileHeader import BitfileInfo

firmware = r"C:\Users\pmaunz\Documents\Programming\IonControl-firmware\fpgafirmware.bit"

logging.basicConfig(format='%(levelname)s %(name)s(%(filename)s:%(lineno)d %(funcName)s) %(message)s',
                    level=logging.WARNING)


class TestPulserFirmware(unittest.TestCase):
    def setUp(self):
        self.pulser = PulserHardwareServer()
        boards = self.pulser.listBoards()
        serial = list(boards.values())[0].serial
        print("Using board {0} firmware {1}".format(serial, str(BitfileInfo(firmware))))
        self.pulser.openBySerial(serial)
        self.pulser.uploadBitfile(firmware)

    def tearDown(self):
        self.pulser.close()

    def test_memory_0(self):
        datalength = 128
        data = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data, 0)
        readdata = [0] * len(data)
        self.pulser.ppReadRamWordList(readdata, 0)
        self.assertEqual(data, readdata)

    def test_memory_1(self):
        datalength = 128
        data = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data, 87)
        readdata = [0] * len(data)
        self.pulser.ppReadRamWordList(readdata, 87)
        self.assertEqual(data, readdata)

    def test_memory_2(self):
        datalength = 8192
        data = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data, 87)
        readdata = [0] * len(data)
        self.pulser.ppReadRamWordList(readdata, 87)
        self.assertEqual(data, readdata)

    def test_memory_3(self):
        datalength = 8193
        data = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data, 87)
        readdata = [0] * len(data)
        self.pulser.ppReadRamWordList(readdata, 87)
        self.assertEqual(data, readdata)

    def test_memory_4(self):
        datalength = 2048
        data1 = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        data2 = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data1, 0)
        self.pulser.ppWriteRamWordList(data2, 8 * 2048)
        readdata = [0] * len(data2)
        self.pulser.ppReadRamWordList(readdata, 8 * 2048)
        self.assertTrue(readdata == data2)
        #self.assertEqual(data1, readdata)
        readdata = [0] * len(data1)
        self.pulser.ppReadRamWordList(readdata, 0)
        self.assertTrue(data1 == readdata)

    def test_memory_5(self):
        datalength = 2048
        data1 = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        data2 = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data1 + data2, 0)
        readdata = [0] * len(data2)
        self.pulser.ppReadRamWordList(readdata, 8 * 2048)
        self.assertTrue(readdata == data2)
        #self.assertEqual(data1, readdata)
        readdata = [0] * len(data1)
        self.pulser.ppReadRamWordList(readdata, 0)
        self.assertTrue(data1 == readdata)

    def test_memory_6(self):
        datalength = 1024 * 1024
        data1 = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        data2 = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(data1, 1024)
        self.pulser.ppWriteRamWordList(data2, 120 * 1024 * 1024)
        readdata = [0] * len(data2)
        self.pulser.ppReadRamWordList(readdata, 120 * 1024 * 1024)
        self.assertTrue(readdata == data2)
        #self.assertEqual(data1, readdata)
        readdata = [0] * len(data1)
        self.pulser.ppReadRamWordList(readdata, 1024)
        self.assertTrue(data1 == readdata)
