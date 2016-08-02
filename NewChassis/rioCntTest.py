# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .digPulseSequencer import DDSRioPulseSequencer
from numpy.random import rand

try:
    countsGenerated = []
    countsCounted = []
    iterations = 10
    for i in range(iterations):
        print('interation:{0}'.format(i))
        pulses = 0
        while pulses <= 0:
            pulses = int(rand() * 100)
        print('\tpulses: {0}'.format(pulses))
        countsGenerated.append(pulses)
        pulseWidth = 40e-9
        channel1 = []
        iDelay = pulseWidth
        for i in range(pulses):
            iDelay += pulseWidth*2
            width = i*pulseWidth
            channel1.append((iDelay, pulseWidth))

        gate1 = [(0, iDelay + (pulseWidth*2))]
        rioPS = DDSRioPulseSequencer(clientType = 'serial',
                device = 'COM1', verbosity = 0)
        rioPS.sampleRate = 2*(1/pulseWidth)
        dataDict = {0: channel1, 2: gate1}
        rioPS.writeDelayWidth(dataDict)
        rioPS.start()
        rioPS.rio.CNT.activeChannel = 1
        samplesAvail = rioPS.rio.CNT.samplesAvail
        print('\tsamplesAvail:{0}'.format(samplesAvail))
        if samplesAvail > 0:
            meas = rioPS.rio.CNT.Read()
        print('\tmeas: {0}'.format(meas))
        countsCounted.append(meas)

    print('countsGenerated:\n{0}'.format(countsGenerated))
    print('countsCounted:\n{0}'.format(countsCounted))
finally:
    pass
    #rioPS.close()
