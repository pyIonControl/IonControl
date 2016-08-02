# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os

topPath = os.path.abspath('..')
sys.path.insert(0, topPath)

from .pCounter import pCounter

def printAllData(data, mean, stdDev):
    print('data: ' + str(data))
    print('mean: ' + str(mean))
    print('stdDev: ' + str(stdDev))
    print('samplesRead: ' + str(cntr._samplesRead))

try:
    cntr = pCounter()
    # cntr.enableStartTrigger = True
    cntr.timeout = 10
    cntr.samples = 10
    #cntr.sampleRate = 100000
    cntr.sampleRate = 10
    cntr.clockSourceTerm = 'PFI12'
    cntr.edgeCntrTerm = 'PFI0'
    print('acqTime: ' + str(cntr.acqTime))
    print('binTime: ' + str(cntr.binTime))
    print('samples: ' + str(cntr.samples))
    print('sampleRate: ' + str(cntr.sampleRate))
    configPath = topPath + '\\config\\example.cfg'
    print(configPath)
    cntr.initFromFile(configPath)
    print('edgeCounter: ' +cntr.edgeCounter)
    print('clockCounter: ' +cntr.clockCounter)

    cntr.start()
    data, mean, stdDev = cntr.read()
    cntr.stop()
    printAllData(data, mean, stdDev)

    data, mean, stdDev = cntr.measure()
    printAllData(data, mean, stdDev)

finally:
    cntr.close()
