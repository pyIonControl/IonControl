# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os
import numpy

topPath = os.path.abspath('..')
if topPath not in sys.path:
    sys.path.insert(0, os.path.abspath('..'))

from .DigitalOutput import DigitalOutput
from .DAQmxUtility import Mode
from .digFreqGenerator import digFreqGenerator

channels = 'PXI1Slot9/port0/line0:7'
sampleClock = 'PXI1Slot9/ctr0'
do = None
clock = None

try:
    #First create the sample clock using a counter on the same card
    clock = digFreqGenerator()
    clock.frequency = float(input('Enter the frequency resolution: ')) 
    clock.init(sampleClock)
    clock.start()

    # Get the amount of time the signal will be high from the user.
    highTime = float(input('Enter the signal high time: '))
    # Create the digital output object
    do = DigitalOutput()
    # set the do object to finite mode
    do.mode = Mode.Finite
    # set the sample clock terminal to the coutner
    do.clkSource = 'Ctr0InternalOutput'
    # set the sample clock rate
    do.sampleClock = clock.frequency

    # create a list of samples
    data = []
    for i in range(int(do.sampleClock*highTime)):
        data.append(255)
    # make sure the samples start and end low
    data.append(0)
    data.insert(0, 0)

    # set the number of sample to the size of the data list, and change
    # the data to a numpy array of uint8's
    do.samplesPerChannel = len(data)
    data = numpy.uint8(data)
    print(data)

    # initialize the do object
    do.init(channels)
    # write the data to the do buffer
    do.writeToBuffer(data)
    # user presses enter to generate the signal
    input('Press Enter to Continue..')
    # start after user hits enter
    do.start()
    do.waitUntilDone()
    # stop immediately after generation
    do.stop()
finally:
    #stop and close the sample clock
    if clock:
        clock.stop()
        clock.close()
    #stop and close the do object
    if do:
        do.close()
