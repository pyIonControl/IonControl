# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import Qt
import PyQt5.Qwt5 as Qwt
from PyQt5.Qwt5.anynumpy import *
import sys

class AutoUpdatePlot(object):
    def __init__(self, *args, **kwargs):
        #super(AutoUpdatePlot, self).__init__()
        #self.app = Qt.QApplication(sys.argv)

        canvasBackground = kwargs.get('canvasBackground', Qt.Qt.white)
        self.chartHistoryLen = kwargs.get('chartHistoryLen', 10)
        chartTitle = kwargs.get('chartTitle', '')
        chartXAxisTitle = kwargs.get('chartXAxisTitle', 'X Values')
        chartYAxisTitle = kwargs.get('chartYAxisTitle', 'Y Values')
        winHorSize = kwargs.get('winHorSize', 500)
        winVertSize = kwargs.get('winVertSize', 300)
        winTitle = kwargs.get('winTitle', '')
        self.curves = {}

        self.dlg = Qt.QDialog(None)

        #Create a Qwt Plot
        self.plot = Qwt.QwtPlot(*args)
        self.plot.setCanvasBackground(canvasBackground)
        #self._alignScales()
        self.plot.setTitle(chartTitle)
        self.plot.insertLegend(Qwt.QwtLegend(), Qwt.QwtPlot.RightLegend);

        mY = Qwt.QwtPlotMarker()
        mY.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        mY.setLineStyle(Qwt.QwtPlotMarker.HLine)
        mY.setYValue(0.0)
        mY.attach(self.plot)

        self.plot.setAxisTitle(Qwt.QwtPlot.xBottom, chartXAxisTitle)
        self.plot.setAxisTitle(Qwt.QwtPlot.yLeft, chartYAxisTitle)
        layout = Qt.QVBoxLayout()
        layout.addWidget(self.plot)
        self.dlg.setLayout(layout)
        self.dlg.resize(winHorSize, winVertSize)
        self.dlg.setWindowTitle(winTitle)
        self.dlg.timerEvent = self.timerEvent
        self.dlg.show()

    def startTimer(self, value):
        return self.dlg.startTimer(value)

    def timerEvent(self, e):
        self.update('myCurve', random.rand())
        self.update('myCurve1', random.rand())

    def addCurve(self, curveTitle, **kwargs):
        curveColor = kwargs.get('curveColor', Qt.Qt.green)
        kwargs['curveTitle'] = curveTitle

        myCurve = myQwtCurve(self.plot, self.chartHistoryLen, **kwargs)
        self.curves[curveTitle] = myCurve

    def _alignScales(self):
        self.plot.canvas().setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Plain)
        self.plot.canvas().setLineWidth(1)
        for i in range(Qwt.QwtPlot.axisCnt):
            scaleWidget = self.plot.axisWidget(i)
            if scaleWidget:
                scaleWidget.setMargin(0)
            scaleDraw = self.plot.axisScaleDraw(i)
            if scaleDraw:
                scaleDraw.enableComponent(
                        Qwt.QwtAbstractScaleDraw.Backbone, False)

    def update(self, curveTitle, value):
        self.curves[curveTitle].update(value)
        self.plot.replot()


class myQwtCurve(object):
    def __init__(self, QwtPlot, chartHistoryLen, **kwargs):
        curveColor = kwargs.get('curveColor', Qt.Qt.green)
        curveTitle = kwargs.get('curveTitle', '')
        self.curveMovement = kwargs.get('curveMovement', 0)

        self.curve = Qwt.QwtPlotCurve(curveTitle)
        self.x = arange(0, chartHistoryLen, 1)
        self.y = zeros(len(self.x), Float)
        self.curve.attach(QwtPlot)
        self.curve.setPen(Qt.QPen(curveColor))
        self.curve.setSymbol(Qwt.QwtSymbol(
            Qwt.QwtSymbol.Ellipse,
            Qt.QBrush(curveColor),
            Qt.QPen(curveColor),
            Qt.QSize(5, 5),
        ))

    def update(self, value):
        if self.curveMovement == 0:
            self.y = concatenate((self.y[1:], self.y[:1]), 1)
            self.y[-1] = value
        elif self.curveMovement == 1:
            self.y = concatenate((self.y[:1], self.y[:-1]), 1)
            self.y[0] = value
        self.curve.setData(self.x, self.y)

if __name__ == '__main__':
    from time import sleep
    from numpy import random
    from threading import Thread
    demo = AutoUpdatePlot(chartTitle='myCurveTest',
            chartHistoryLen = 100,
            winTitle= 'myDialog')
    demo.addCurve('myCurve')
    demo.addCurve('myCurve1', curveColor=Qt.Qt.blue)
    demo.startTimer(10)
    demo.exec_()
    demo.stopTimer()
