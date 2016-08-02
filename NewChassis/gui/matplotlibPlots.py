# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_qt4agg \
        import FigureCanvasQTAgg as FigureCanvas
import numpy
from math import ceil, floor


class SingleLinePlot(object):
    def __init__(self, **kwargs):
        self.curveMovement = kwargs.get('curveMovement', 0)
        self.points = kwargs.get('points', 30)

        self._fig = plt.figure()
        self._axis1 = self._fig.add_subplot(111)
        #self._plot = FigureCanvas(self._fig)

    def init_plot(self):
        self.xdata = numpy.arange(0, self.points, 1)
        self.ydata1 = numpy.zeros(self.points, numpy.float32)

        self.clear()
        self._line1, = self._axis1.plot(self.xdata, self.ydata1, 'b-o')

    def clear(self):
        self._axis1.clear()
        self._axis1.set_ylabel('Counts', color='b')
        self._axis1.set_xlabel('Bins')

    def _updateDataCallback(self, *args):
        i = args[0]
        updateCallback = args[1]
        updateValue = updateCallback()
        if self.curveMovement == 0:
            self.ydata1 = numpy.concatenate((self.ydata1[1:],
                self.ydata1[:1]), 1)
            self.ydata1[-1] = updateValue
        elif self.curveMovement == 1:
            self.ydata1 = numpy.concatenate((self.ydata1[:1],
                self.ydata1[:-1]), 1)
            self.ydata1[0] = updateValue

        ylim = (floor(self.ydata1.min()), ceil(self.ydata1.max()))
        self._axis1.set_ylim(ylim)
        self._line1.set_ydata(self.ydata1)

    def animate(self, updateCallback, **kwargs):
        interval = kwargs.get('interval', 10)
        ani = animation.FuncAnimation(self._fig,
                self._updateDataCallback, None, None,
                (updateCallback, ), interval = interval,
                repeat = True)
        self._fig.show()

if __name__ == '__main__':
    def dataUpdate():
        return float(numpy.random.rand(1))

    test = SingleLinePlot(points = 100)
    test.init_plot()
    test.animate(dataUpdate, interval = 50)
