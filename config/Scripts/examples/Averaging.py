#RamanPowerAveraging.py created 2016-05-17 08:42:48.007243

#Reimplementation of averaging functionality of repeat scan
#Each time a scan is completed, the new data associated with some specified
#evaluation is averaged into an average trace. The average trace is averaged
#into the existing average, and plotted to "Average Plot." This continues until
#the script is stopped.

traceName = 'RamanPowerScan_Average'

createTrace(traceName, 'Detection') #create a trace associated with the average
setScan('RamanPowerScan')
setEvaluation('Standard')
setAnalysis('NoAnalysis')

num = 1 #The loop counter
while True: #run until stopped. Could also change this to run for a fixed number of cycles.
    startScan()
    data = getAllData()['Detection'] #Returns all data associated with "Detection" once scan finishes.
    xdata = data[0]
    ydata = data[1]
    if num == 1:
        averagedYdata = ydata
    else:
        averagedYdata = ((num-1)*averagedYdata + ydata)/float(num)
    plotList(xdata, averagedYdata, traceName, overwrite=True) #plot the data
    num += 1
    if scriptIsStopped():#This conditional must be here for any infinite loop, otherwise it cannot be stopped!
        break