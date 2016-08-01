#HeatingRate.py created 2015-08-06 13:18:27.682000
#
#Script for running the scans to measure a heating rate
#Global named 'tHeat' is scanned from 0 to 9 ms
#At each value, red sideband is scanned with scan 'rsb',
#and blue sideband is scanned with scan 'bsb'

setEvaluation('myEval1') #same evaluation for all
for heatingTime in range(10):
    setGlobal('tHeat', heatingTime, 'ms')
    setScan('rsb')
    setAnalysis('rsbFit')
    startScan()
    setScan('bsb')
    setAnalysis('bsbFit')
    startScan()
    