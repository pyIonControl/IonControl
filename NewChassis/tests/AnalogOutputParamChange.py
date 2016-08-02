# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys

import os

sys.path.insert(0, os.path.abspath('..'))

from AnalogOutput import AnalogOutput
from DAQmxUtility import Mode 
try:
    physicalChannel = 'PXI1Slot2/ao0:7'
    ao = AnalogOutput()
    ao.mode = Mode.Finite
    ao.samplesPerChannel = 1000
    ao.init(physicalChannel)
    testBuffer = ao.createSineTestBuffer()
    ao.writeToBuffer(testBuffer)
    ao.samplesPerChannel = 100
    ao.start()
    ao.waitUntilDone()
    ao.stop()

finally:
    ao.close()
