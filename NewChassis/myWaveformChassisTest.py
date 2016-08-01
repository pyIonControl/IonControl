# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .WaveformChassis import WaveformChassis
from .DAQmxUtility import Mode

configFile = 'c:/Workspace/Chassis.git/config/sana118.cfg'
itfFile = 'c:/Workspace/Chassis.git/config/voltage_test.itf'
eMapFile = 'c:/Workspace/Chassis.git/config/test_map.txt'

try:
    wc = WaveformChassis()
    wc.mode = Mode.Finite
    wc.itf.eColHeader = 'e{0:02d}'
    wc.eMapPath = eMapFile
    wc.initFromFile(configFile)
    wc.loadItf(itfFile)
    wc.stepItf(0, 2)
finally:
    pass
    #wc.close()
