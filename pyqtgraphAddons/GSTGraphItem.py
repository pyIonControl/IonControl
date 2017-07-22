import numpy
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
            labels=None
        )
        self._shape = None
        self.picture = None
        self.setOpts(**opts)
        self.spatialIndex = dict()

    def setOpts(self, **opts):
        self.opts.update(opts)
        self.picture = None
        self._shape = None
        self.update()
        self.informViewBoundsChanged()

    def setData(self, x, y, labels=None):
        self.opts['x'] = x
        self.opts['y'] = y
        if labels is not None:
            self.opts['labels'] = labels
        self.update()
        self.drawPicture()

    def drawPicture(self):
        self.picture = QtGui.QPicture()
        self._shape = QtGui.QPainterPath()
        p = QtGui.QPainter(self.picture)
        self.spatialIndex.clear()

        pen = self.opts['pen']

        if pen is None:
            pen = getConfigOption('foreground')

        def asarray(x):
            if x is None or np.isscalar(x) or isinstance(x, np.ndarray):
                return x
            return np.array(x)

        x = asarray(self.opts.get('x'))
        y = asarray(self.opts.get('y'))
        labels = self.opts.get('labels')
        if labels is None:
            labels = x
        colorscale = self.opts.get('colorscale')
        if colorscale is None:
            colorscale = lambda x: (1, 0, 0)
        x_max = asarray(self.opts.get('x_max'))
        if x_max is None:
            x_max = numpy.array([z for z in x if z is not None]).max(0)

        def plot_index(idx):
            x1, y1, x2, y2 = idx
            x1_max, y1_max, x2_max, y2_max = x_max
            return x1 * (x2_max + 2) + x2, y1 * (y2_max + 2) + y2

        p.setPen(fn.mkPen(pen))
        for index, value, label in zip(x, y, labels):
            if x is not None:
                c = QtGui.QColor(*colorscale(value))
                p.setBrush(QtGui.QBrush(c))
                rx, ry = plot_index(index)
                rect = QtCore.QRectF(rx - 0.5, ry - 0.5, 1, 1)
                self.spatialIndex[(rx, ry)] = "{}  {:.3f}".format(label, value)
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
