# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os

sys.path.insert(0, os.path.abspath('..'))

from . import Timing

#create the test object whcih will control the niSync card
test = Timing.Timing()

#write to the object's data to configure the niSync card
test.sampleRate = 100e3

try:
    #initialize will connect all clock and trigger terminals
    test.init('PXI1Slot14')

    print('A 100kHz signal is being output PFI0')

    while True:

        dataIn = input("Type Go to send a trigger or type Stop: ")
        if dataIn == 'Go':
            #send a trigger programatically
            test.sendSoftwareTrigger()
        elif dataIn == 'Stop':
            break
        else:
            print('Command not recognized...')
    


finally:
    #close when done with the object
    test.close()
