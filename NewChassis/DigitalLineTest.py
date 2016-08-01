# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os

topPath = os.path.abspath('..')
if topPath not in sys.path:
    sys.path.insert(0, os.path.abspath('..'))

from .DigitalOutput import DigitalOutput
from .DAQmxUtility import Mode

physicalChannel = 'PXI1Slot3/port0/line4'

try:
    do = DigitalOutput()
    do.mode = Mode.Static
    do.init(physicalChannel)
    while True:
        inData = input('Write High, Low, or Stop: ')
        if inData == 'High':
            do.writeStatic(True)
        elif inData == 'Low':
            do.writeStatic(False)
        elif inData == 'Stop':
            break
        else:
            print('Input not recognized.')


finally:
    do.close()
