# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .DAQmxUtility import Mode
from .WaveformChassis import WaveformChassis
from .itfParser import itfParser


chassis = WaveformChassis()
itf = itfParser()

chassis.mode = Mode.Static
chassis.initFromFile(r'config\old_chassis.cfg')
print("read config")
itf.open(r'config\hoa_test.itf')
print("file opened")
itf.eMapFilePath = r'config\hoa_map.txt'
print("map file set")
for i in range(itf.getNumLines()):
    data = itf.eMapReadLine()
    print("data", data)
    print(type(data))
    chassis.writeAoBuffer(data)
print(itf.meta)    
chassis.close()
