#HeatingRateWithNbar.py created 2015-08-06 13:18:27.682000
#
#Script for measuring a heating rate and plotting nbar
#Global named 'tHeat' is scanned from 0 to 9 ms
#At each value, red sideband is scanned with scan 'rsb',
#and blue sideband is scanned with scan 'bsb'. The peak
#values are determined, and nbar is calculated.

setEvaluation('myEval1') #same evaluation for all
traceName = 'nbar'
plotName = 'nbar'
addPlot(plotName) #add new plot for plotting nbar, (ignored if already exists)
createTrace(traceName, plotName, xUnit='ms', xLabel='heating time', comment='nbar vs heating time')
for heatingTime in range(10):
    setGlobal('tHeat', heatingTime, 'ms')
    setScan('rsb')
    setAnalysis('rsbFit')
    startScan()
    rsbFitResults = getAnalysis()
    rsbPeak = rsbFitResults['rsbFit']['A'] #A should contain the peak value parameter
    setScan('bsb')
    setAnalysis('bsbFit')
    startScan()
    bsbFitResults = getAnalysis()
    bsbPeak = bsbFitResults['bsbFit']['A']
    ratio = rsbPeak/bsbPeak
    nbar = ratio/(1-ratio)
    plotPoint(heatingTime, nbar, traceName) #plot result