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

from .itfParser import itfParser
from .WaveformChassis import WaveformChassis
from .DAQmxUtility import Mode

try:
    # Create the chassis and itf objects.
    chassis = WaveformChassis()
    itf = itfParser()

    # Set the chassis mode to static
    chassis.mode = Mode.Static

    # Setup file paths.
    configPath = topPath + '\\config'
    configFile = configPath + '\\example.cfg'
    itfFile = configPath + '\\voltage_test.txt'
    eMapFile = configPath + '\\thunderbird_map.txt'
    chassis.initFromFile(configFile)
    itf.open(itfFile)
    itf.eMapFilePath = eMapFile

    #  Run the lines in the itf file.
    for i in range(itf.getNumLines()):
        data = itf.eMapReadLine()
        chassis.writeAoBuffer(data)

finally:
    chassis.close()
