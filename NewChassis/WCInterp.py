# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .WaveformChassis import WaveformChassis
import os

configDir = os.path.split(os.getcwd())[0] + '\\config'

wc = WaveformChassis()
wc.initFromFile(configDir + '\\sana118.cfg')
wc.eMapPath = configDir + '\\test_map.txt'
wc.loadItf(configDir + '\\voltage_test.txt')
#aoData = wc._fixOneSample(0, 3)
#newData = wc.interp(aoData, wc.samplesPerChannel*10)
wc.stepItfInterp(0, 3, 2000)
wc.close()
