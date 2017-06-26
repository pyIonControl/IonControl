from PyQt5 import QtGui, QtCore
from pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject
from pyqtgraph import getConfigOption
from pyqtgraph import functions as fn
import numpy as np

__all__ = ['GSTGraphItem']


class GSTGraphItem(GraphicsObject):
    def __init__(self, **opts):
        """
        Valid keyword options are:
        x, y, max_x, colorscale

        x is a tuple (f1, f2, g, l) specifies the index into the GST set
        where f1 and f2 are the preparation and detection fiducial indices,
        g is the germ index and l the germ length

        max_x is a tuple (f1_max, f2_max, g_max, l_max) specifying the maximum of each index

        colorscale is a function returning a QColor for values in y

        y is the result

        Example uses:

            BarGraphItem(x=range(5), height=[1,5,2,4,3], width=0.5)


        """
        GraphicsObject.__init__(self)
        self.opts = dict(
            x=None,
            y=None,
            max_x=None,
            pen=None,
            colorscale=None,
        )
        self._shape = None
        self.picture = None
        self.setOpts(**opts)

    def setOpts(self, **opts):
        self.opts.update(opts)
        self.picture = None
        self._shape = None
        self.update()
        self.informViewBoundsChanged()

    def drawPicture(self):
        self.picture = QtGui.QPicture()
        self._shape = QtGui.QPainterPath()
        p = QtGui.QPainter(self.picture)

        pen = self.opts['pen']

        if pen is None:
            pen = getConfigOption('foreground')

        def asarray(x):
            if x is None or np.isscalar(x) or isinstance(x, np.ndarray):
                return x
            return np.array(x)

        x = asarray(self.opts.get('x'))
        y = asarray(self.opts.get('y'))
        colorscale = self.opts.get('colorscale')
        if colorscale is None:
            colorscale = lambda x: (1, 0, 0)
        x_max = asarray(self.opts.get('x_max'))
        if x_max is None:
            x_max = x.max(0)

        def plot_index(idx):
            f1, f2, l, g = idx
            f1_max, f2_max, l_max, g_max = x_max
            return l * (f1_max + 2) + f1, g * (f2_max + 2) + f2

        p.setPen(fn.mkPen(pen))
        for index, value in zip(x, y):
            c = QtGui.QColor(255,0,0)
            p.setBrush(QtGui.QBrush(c))
            rx, ry = plot_index(index)
            rect = QtCore.QRectF(rx - 0.5, ry - 0.5, 1, 1)
            p.drawRect(rect)
            self._shape.addRect(rect)

        p.end()
        self.prepareGeometryChange()

    def paint(self, p, *args):
        if self.picture is None:
            self.drawPicture()
        self.picture.play(p)

    def boundingRect(self):
        if self.picture is None:
            self.drawPicture()
        return QtCore.QRectF(self.picture.boundingRect())

    def shape(self):
        if self.picture is None:
            self.drawPicture()
        return self._shape
