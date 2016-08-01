# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy as np

def createSineWave(amplitude, frequency, sampleRate, numSamples, phase = 0):
    #calculated params
    dt = 1 / np.float64(sampleRate)
    #print 'dt: ' + str(dt)
    totalTime = dt*numSamples
    #print 'total time: ' + str(totalTime)
    t = np.linspace(0, totalTime, numSamples)
    a = amplitude * np.sin(2*np.pi*frequency*t + phase)
    
    return {'time': t, 'amplitude': a}

