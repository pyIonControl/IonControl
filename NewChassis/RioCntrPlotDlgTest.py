# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import Qt
import sys
from time import sleep
from devices.ddsRio import RioCntrPlotDlg
from .digPulseSequencer import DDSRioPulseSequencer

#Tell the script that it is a Qt.QApplication
app = Qt.QApplication(sys.argv)

#Setup the gate pulse needed to gate the counter
rioPS = DDSRioPulseSequencer(clientType = 'serial',
        device = 'COM3', verbosity = 0)
dataDict = {2: ((0, 0.01), (0.02, 0)), 8: ((0, 0.01), (0.02, 0))}
rioPS.sampleRate = 1e3
rioPS.writeDelayWidth(dataDict)
print(rioPS.digBuff.data)
rioPS.repeats = 69

#Create the RioCntrPlotDlg to show a Qt display when
#reading from the counter.
cntr = RioCntrPlotDlg(clientType = 'serial', device = 'COM3',
        chartHistoryLen = 100)
cntr.startTimer(10)
for i in range(3):
    print('i{0}'.format(i))
    rioPS.start()
    sleep(2)
    cntr.read()
app.exec_()
cntr.close()

