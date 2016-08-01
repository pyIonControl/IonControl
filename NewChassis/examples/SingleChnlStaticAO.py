# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os
from time import sleep
import numpy as np

sys.path.insert(0, os.path.abspath('..'))

import AnalogOutput as ao
import DAQmxUtility as dutil

physicalChannel = 'PXI1Slot2/ao0'

#################### Static Mode ######################
test = ao.AnalogOutput()
test.mode = dutil.Mode.Static

try:
    test.init(physicalChannel)
    print("Number of Channels: " + str(test.numChannels))
    print("Samples Per Channel: {0}".format(test.samplesPerChannel))
    #testBuffer = test.createSineTestBuffer()
    for i in np.arange(-10, 10.1, 0.5):
        testBuffer = np.array((i,))
        print(testBuffer)
        test.writeToBuffer(testBuffer)
        sleep(0.100)

finally:
    test.close()
