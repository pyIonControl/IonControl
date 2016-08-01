# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import time
from numpy import linspace, roll
import sys
import os

topPath = os.path.abspath('..')
sys.path.insert(0, topPath)

from .WaveformChassis import WaveformChassis
from . import DAQmxUtility as dutil
from PyDAQmx import DAQError

test = WaveformChassis()
test.triggerType = dutil.TriggerType.Hardware
#configPath = topPath + '\\config\\example.cfg'
configPath = topPath + '\\config\\sana118.cfg'
print(configPath)
#slots = range(2, 19)
#[slots.remove(x) for x in [8,9,10,14]]
#slots = [2, 3, 4, 5]
#aoDevsAndChnls = ['PXI1Slot{0}/ao0:7'.format(x) for x in slots]
#doDevsAndChnls = ['PXI1Slot{0}/port0/line0:7'.format(x) for x in slots]
#syncSlot = raw_input('Please choose a NiSync slot [1-18]: ')

#if int(syncSlot) > 2:
#    test.timing.pxiStarSlots = 17
#else:
#    test.timing.pxiStarSlots = 6

#niSyncDev = 'PXI1Slot' + syncSlot
modeString = ''

while(modeString != 'Stop'):

    modeString = input('Which Mode?\n')

    if modeString == 'Static':
        #################### Static Mode ####################
        print('Starting Static Mode')
        try:
            test.mode = dutil.Mode.Static
            #test.init(aoDevsAndChnls, doDevsAndChnls, niSyncDev)
            test.initFromFile(configPath)
            print(test._getPauseTriggerSource())
            sineBuffer = test.createAoSineBuffer()
            doTestBuffer = test.createDoTestBuffer()
            linearBuffer = linspace(-10, 10, test.getNumAoChannels())
            for i in linearBuffer:
                test.writeAoBuffer(linearBuffer)
                #test.writeDoBuffer(doTestBuffer)
                test.start()
                test.waitUntilDone()
                test.stop()
                linearBuffer = roll(linearBuffer, 1)
                
        finally:
            test.close()
        print('Static Mode Complete')

    elif modeString=='Finite':
        #################### Finite Mode ####################
        print('Starting Finite Mode.')
        try:
            test.mode = dutil.Mode.Finite
            test.pauseTriggerOn()
            samples = input('How many samples: ') 
            test.samplesPerChannel = int(samples)
            test.sampleRate = 100000
            #test.init(aoDevsAndChnls, doDevsAndChnls, niSyncDev)
            test.initFromFile(configPath)
            print(test._getPauseTriggerSource())
            sineBuffer = test.createAoSineBuffer()
            doTestBuffer = test.createDoTestBuffer()
            input('Press enter to start...')
            for i in range(1):
                test.writeAoBuffer(sineBuffer)
                #test.writeDoBuffer(doTestBuffer)
                test.start()
                print(test.done)
                while not test.done:
                    pass
                print(test.done)
                test.waitUntilDone()
                test.stop()
            
        finally:
            test.close()

        print('Finite Mode Complete')

    elif modeString=='Continuous':
        ##################### Continuous Mode ####################
        print('Starting Continuous Mode')
        try:
            test.mode = dutil.Mode.Continuous
            #test.init(aoDevsAndChnls, doDevsAndChnls, niSyncDev)
            test.pauseTriggerOn()
            test.initFromFile(configPath)
            print(test._getPauseTriggerSource())
            sineBuffer = test.createAoSineBuffer()
            doTestBuffer = test.createDoTestBuffer()
            test.writeAoBuffer(sineBuffer)
            #test.writeDoBuffer(doTestBuffer)
            test.start()
            input("Please press enter to stop continuous mode...")
            test.stop()
        finally:
            test.close()
        print('Continuous Mode Complete.')

    elif modeString=='Stop':
        pass
    
    else:
        print('Mode Not Recognized.')
