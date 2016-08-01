#manualScan.py created 2015-10-08 13:41:25.695000

#Manual scan is intended to be used for a scan in which the computer does not have
#control over what's being scanned, for example a manual micrometer. The list of values
#that the micrometer will be scanned over is determined ahead of time. The scan used
#here should be just a step-in-place for a fixed number of points, and the analysis
#should just an average of those points. At each position, the script runs the scan, plots the
#point, and then pauses. At this time you move the micrometer to the next position,
#and then unpause the script.

xValues = [0.1, 0.2, 0.3, 0.4, 0.5] #micrometer values that will be scanned
traceName = 'myManualScan'
plotName = 'Manual Scan' #name of plot to use
addPlot(plotName) #add a plot to use. This is unnecessary if using an existing plot.
createTrace(traceName, plotName, xUnit='mm', xLabel='Micrometer Position') #create the trace to use to plot the data
setScan('myScan')
setEvaluation('myEvaluation')
setAnalysis('myAnalysis')
for x in xValues: #loop through the micrometer positions
    startScan() #run the first scan
    y = getAnalysis()['myAnalysis']['b'] #Get the analysis, which in this case should just be an average
    plotPoint(x, y, traceName) #plot the point
    pauseScript() #pause the script. Move the micrometer, then unpause the script.