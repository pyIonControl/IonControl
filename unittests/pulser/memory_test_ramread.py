# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import random
import unittest
import logging
import struct
import sys

from pulser.PulserHardwareServer import PulserHardwareServer, sliceview
from pppCompiler.pppCompiler import pppCompileString
from pulseProgram.PulseProgram import PulseProgram
from pulser.bitfileHeader import BitfileInfo

# firmware = r"C:\Users\pmaunz\PyCharmProjects\IonControl34\FPGA_Ions\IonControl-firmware-8Counters.bit"
firmware = r"C:\Users\plmaunz\Documents\Programming\IonControl-firmware\fpgafirmware.bit"

logging.basicConfig(format='%(levelname)s %(name)s(%(filename)s:%(lineno)d %(funcName)s) %(message)s',
                    level=logging.WARNING)

pppProgram = """
var index = 0
var max = {0}
var ramaddress = {1}
var x
parameter delay = 100 us

set_ram_address(ramaddress)
update(delay)
update()
while index<max:
    index += 1
    x = read_ram()
    write_pipe(x)
"""

def ppCompile(assemblercode):
    pp = PulseProgram()
    pp.debug = True
    pp.insertSourceString(assemblercode)
    pp.compileCode()
    pp.toBytecode()
    return pp.toBinary()


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

    def test_pipe(self):
        datalength = 2048
        memdata = [random.randint(0, sys.maxsize) for _ in range(datalength)]
        self.pulser.ppWriteRamWordList(memdata, 0)
        assemblercode = pppCompileString(pppProgram.format(datalength, 0))
        binarycode, binarydata = ppCompile(assemblercode)
        self.pulser.ppUploadCode(binarycode)
        self.pulser.ppUploadData(binarydata)
        self.pulser.ppStart()
        data = bytearray()
        while len(data) < datalength * 8:
            dataslice, overrun, externalStatus = self.pulser.ppReadWriteData(8)
            if dataslice is not None:
                data += dataslice
                print("{0} bytes".format(len(data)))
        worddata = [struct.unpack('Q', s)[0] for s in sliceview(data, 8)]
        print(memdata)
        print(worddata)
        self.assertEqual(worddata, memdata)


