# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
# This should be a live update of photon counts
from PyQt5 import QtGui, QtCore
import PyQt5.Qwt5 as Qwt
from PyQt5.Qwt5.anynumpy import *

import exptDevices as expt



class PmtXYPlot(Qwt.QwtPlot):

    def __init__(self):
        # Check syntax
        super(PmtXYPlot, self).__init__()
        
        # Counter
        self.ctr = expt.getNICounter(gateTime=100)

        self.setCanvasBackground(QtGui.QColor("white"))
        #self.alignScales()


        self.x = arange(0.0, 100.1, 1.)
        self.y = zeros(len(self.x), Float)

        self.setTitle("PMT Counts")
        self.curve = Qwt.QwtPlotCurve("Counts")
        self.curve.attach(self)

        self.curve.setSymbol(Qwt.QwtSymbol(
            Qwt.QwtSymbol.Ellipse,
            QtGui.QBrush(QtGui.QColor("black")),
            QtGui.QPen(QtGui.QColor("black")),
            QtCore.QSize(5, 5),
        ))

        self.setAxisTitle(Qwt.QwtPlot.xBottom, "Time (units)")
        self.setAxisTitle(Qwt.QwtPlot.yLeft, "Counts/bin")
        
        self.startTimer(10)


    def timerEvent(self, e):
        
        rawCounts, meanCounts, stdDev = self.ctr.measure()

        self.y = concatenate( (self.y[1:], self.y[:1]), 1)
        self.y[-1] = meanCounts

        self.curve.setData(self.x, self.y)
        self.replot()
    
    def close(self):
        self.ctr.close()


if __name__=="__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    demo = PmtXYPlot()
    demo.resize(500, 300)
    demo.show()
    sys.exit(app.exec_())
    demo.close()

        
