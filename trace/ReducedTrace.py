import numpy
from collections import defaultdict

from modules.RunningStat import RunningStat


class ReducedTrace:
    def __init__(self, traceCollection, averageSameX=False, combinePoints=0, averageType=None,
                 xColumn=None, yColumn=None, topColumn=None, bottomColumn=None, heightColumn=None):
        self.traceCollection = traceCollection
        self._averageSameX = averageSameX
        self._combinePoints = combinePoints
        self._averageType = averageType
        self.xColumn = xColumn
        self.yColumn = yColumn
        self.bottomColumn = bottomColumn
        self.topColumn = topColumn
        self.heightColumn = heightColumn
        self.initCache()
        self.clearCache()

    def update(self, averageSameX=False, combinePoints=0, averageType=None):
        if self._averageSameX != averageSameX or self._combinePoints != combinePoints or self._averageType != averageType:
            self._averageSameX = averageSameX
            self._combinePoints = combinePoints
            self._averageType = averageType
            return True
        return False

    def clearCache(self):
        self._cachedLength = 0

    def initCache(self):
        self._x_cache = defaultdict(RunningStat)

    @property
    def x(self):
        return self.traceCollection[self.xColumn]

    @property
    def y(self):
        return self.traceCollection[self.yColumn]

    @property
    def plotData(self):
        if self._averageSameX:
            x, y = self.x, self.y
            for thisx, thisy in zip(x[self._cachedLength:], y[self._cachedLength:]):
                self._x_cache[thisx].add(thisy)
            self._cachedLength = len(x)
            pairs = [(myx, myy.mean) for myx, myy in sorted(self._x_cache.items())]
        else:
            pairs = sorted(zip(self.x, self.y), key=lambda x: x[0]) if len(self.x) > 0 else list(zip(self.x, self.y))
        if int(self._combinePoints):
            num_points = int(self._combinePoints)
            extra = len(pairs) % num_points
            if extra > 0:
                pairs.extend([(float('NaN'), float('NaN'))] * (num_points - extra))
            plotx, ploty = numpy.reshape(numpy.array(pairs).transpose(), (2, -1, num_points))
            plotx = numpy.nanmean(plotx, axis=1)
            ploty = numpy.nanmean(ploty, axis=1)
            return plotx, ploty
        else:
            return numpy.array(pairs).transpose()


