import os
import sys

import AnalogOutput as ao
import DAQmxUtility as dutil


sys.path.insert(0, os.path.abspath('..'))

physicalChannel = 'PXI1Slot3/ao0:7'

#################### Static Mode ######################
print('Running Static Mode...')
test = ao.AnalogOutput()
test.mode = dutil.Mode.Static

try:
    test.init(physicalChannel)
    print("Number of Channels: " + str(test.numChannels))
    print("Samples Per Channel: {0}".format(test.samplesPerChannel))
    print("Sample Rate: {0}".format(test.sampleRate))
    testBuffer = test.createSineTestBuffer()
    test.writeToBuffer(testBuffer)
    test.start()
    test.waitUntilDone()
    test.stop()

finally:
    test.close()
    
print('Static Mode Complete')

################### Finite Mode ########################
print('Testing Finite Mode...')
test.mode = dutil.Mode.Finite
samples = input('How many samples: ')
test.samplesPerChannel = int(samples)

try:
    test.init(physicalChannel)
    print("Samples Per Channel: {0}".format(test.samplesPerChannel))
    print("Sample Rate: {0}".format(test.sampleRate))
    testBuffer = test.createSineTestBuffer()
    test.writeToBuffer(testBuffer)
    test.start()
    test.waitUntilDone()
    test.stop()

finally:
    test.close()
print('Finite Mode Complete')

################## Continuous Mode #####################
print('Testing Continuous Mode')
test.mode = dutil.Mode.Continuous
try:
    test.init(physicalChannel)
    test.writeToBuffer(testBuffer)
    test.start()
    input('Press enter to stop...')
    test.stop()
    
finally:
    test.close()
print('Continuous Mode Complete')
