# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .digPulseSequencer import DDSRioPulseSequencer
from time import sleep

try:
    iterations = 5
    for i in range(iterations):
        #rioPS = DDSRioPulseSequencer(clientType = 'tcp',
        #        address = '192.168.10.10', port = 6431)
        rioPS = DDSRioPulseSequencer(clientType = 'serial',
                device = 'COM3', verbosity = 0)
        dataDict = {2: ((0, 0.01), (0.02, 0)), 8: ((0, 0.01), (0.02, 0))}
        rioPS.sampleRate = 1e3
        rioPS.writeDelayWidth(dataDict)
        print(rioPS.digBuff.data)
        rioPS.repeats = 69
        rioPS.start()
        sleep(2)
        rioPS.rio.CNT.activeChannel = 0
        samplesAvail = rioPS.rio.CNT.samplesAvail
        print('\tsamplesAvail:{0}'.format(samplesAvail))
        if samplesAvail > 0:
            meas = rioPS.rio.CNT.Read()
            print('\tmeas: {0}'.format(meas))

finally:
    pass
    #rioPS.close()
    
