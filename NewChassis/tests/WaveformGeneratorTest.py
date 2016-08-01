# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy
import sys
import os

sys.path.insert(0, os.path.abspath('..'))

from WaveformGenerator import WaveformGenerator
import DAQmxUtility as dutil

test = WaveformGenerator()
doChannels = 'PXI1Slot2/port0/line0:7'
aoChannels = 'PXI1Slot2/ao0:7'

################### Static Mode ####################
print('Running Static Mode...')
test.mode = dutil.Mode.Static
test.samplesPerChannel = 1


try:
    test.init(aoChannels, doChannels)
    aoTestBuffer = test.ao.createSineTestBuffer()
    doTestBuffer = test.do.createTestBuffer()
    test.writeAoBuffer(aoTestBuffer)
    test.writeDoBuffer(doTestBuffer)
    test.start()
    test.waitUntilDone()
    test.stop()
    
finally:
    test.close()

print('Static Mode Complete.')


#################### Finite Mode ####################
print('Running Finite Mode')
test.mode = dutil.Mode.Finite
samples = input('How many samples: ')
test.samplesPerChannel = int(samples)
test.triggerType = dutil.TriggerType.Software

try:
    test.initFromFile('C:\\Users\\Public\\Documents\\experiments\\QGA\\config\\VoltageControl\\R444435.cfg')
    print(test.clkSource)
    test.samplesPerChannel = 1000
    aoTestBuffer = test.ao.createSineTestBuffer()
    doTestBuffer = test.do.createTestBuffer()
    #print 'AO Buffer: ' + str(aoTestBuffer)
    #print len(aoTestBuffer)
    #print 'DO Buffer: ' + str(doTestBuffer)
    aoSamplesWritten = test.writeAoBuffer(aoTestBuffer)
    doSamplesWritten = test.writeDoBuffer(doTestBuffer)
    print('AO Samples Written: ' + str(aoSamplesWritten))
    print('DO Samples Written: ' + str(doSamplesWritten))
    test.start()
    test.waitUntilDone()
    test.stop()
    
finally:
    test.close()
    
print('Finite Mode Complete')
input('Press Enter to Continue...')

#################### Continuous Mode ####################
print('Running Continuous Mode')
test.mode = dutil.Mode.Continuous
#test.samplesPerChannel = 8005
test.triggerType = dutil.TriggerType.Software

try:
    test.init(aoChannels, doChannels)
    aoTestBuffer = test.ao.createSineTestBuffer()
    doTestBuffer = test.do.createTestBuffer()
    test.writeAoBuffer(aoTestBuffer)
    test.writeDoBuffer(doTestBuffer)
    test.start()
    input('Press enter to continue...')
    test.stop()
finally:
    test.close()
    
print('Continuous Mode Complete.')
