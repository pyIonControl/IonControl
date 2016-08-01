#StopAtThreshold.py created 2015-08-11 16:11:14.672000
#
#Example script for stopping at a given threshold.
#
#In this script, the data coming back from evaluation 'myEvalName' is
#continuously monitored, and if the y value goes above 0.3, the scan
#stops. This is admittedly somewhat contrived, but the point is to show
#usage of getData() to examine data during a running scan.

startScan(wait=False)
while scanRunning():
    data=getData()
    if data['myEvalName'][1] > 0.3:
        stopScan()
        break