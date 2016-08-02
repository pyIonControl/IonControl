# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from devices.ddsRio import ddsRio

myRio = ddsRio('serial', device='COM3')   # Open communication to the dds
myRio.DDS.activeBoard = 1                 # Set the active board to the AD9959
myRio.DDS.sysclk = 10e6                   # Set the system clock
myRio.DDS.activeChannel = 0               # Set the active channel to 0, which is default
myRio.DDS.freqMultiplier = 20             # Set the frequency multiplier to 20 for a 200MHz clock
myRio.DDS.SingleTone(1e6, 3)              # Tell the DDS to go to 1MHz in Single Tone Mode
myRio.close()                             # Close communication to the dds
