import numpy
from pygsti import logl_terms, logl_max_terms

from pyqtgraphAddons.GSTGraphItem import GSTGraphItem


class QubitPlotSettings:
    def __init__(self):
        self.gateSet = None


class PlottedStructure:
    def __init__(self, traceCollection, qubitData, graphicsView, windowName):
        self.qubitData = qubitData
        self.traceCollection = traceCollection
        self.curvePen = 0
        self.name = 'Qubit'
        self.windowName = windowName
        self._graphicsView = graphicsView
        self._gstGraphItem = None
        lengths = sorted(set([k[0] for k in self.qubitData.plaquettes.keys()]))
        germs = sorted(set([k[1] for k in self.qubitData.plaquettes.keys()]))
        self._lookup = dict()
        self.gateSet = self.qubitData.target_gateset
        for (l, g), p in self.qubitData.plaquettes.items():
            l_id = lengths.index(l)
            g_id = germs.index(g)
            for r, c, s in p:
                self._lookup[(l_id, g_id, r, c)] = s
        self._x, self._plot_s = list(zip(*sorted(self._lookup.items())))
        self._plot_s_idx = [self.qubitData.gatestring_list.index(s) for s in self._plot_s]

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._log_likelihood

    @property
    def plaquettes(self):
        return self.qubitData.plaquettes

    @property
    def gateSet(self):
        return self._gateSet

    @gateSet.setter
    def gateSet(self, gateSet):
        self._gateSet = gateSet
        self._spamLabels = self._gateSet.get_spam_labels()  # this list fixes the ordering of the spam labels
        self._spam_lbl_rows = {sl: i for (i, sl) in enumerate(self._spamLabels)}
        self._probs = numpy.empty((len(self._spamLabels), len(self.qubitData.gatestring_list)), 'd')
        self._evaltree = self._gateSet.bulk_evaltree(self.qubitData.gatestring_list)
        self._gateSet.bulk_fill_probs(self._probs, self._spam_lbl_rows, self._evaltree, (-1e6, 1e6))

    def _assemble_data(self):
        l = logl_terms(self._gateSet, None, gatestring_list=self.qubitData.gatestring_list, evalTree=self._evaltree,
                       probs=self._probs, countVecMx=self.qubitData.countVecMx, totalCntVec=self.qubitData.totalCntVec)
        l_max = logl_max_terms(None, gatestring_list=self.qubitData.gatestring_list,
                               countVecMx=self.qubitData.countVecMx, totalCntVec=self.qubitData.totalCntVec)
        self._log_likelihood = numpy.sum(2 * (l_max - l), axis=0)
        self._y = [self._log_likelihood[i] for i in self._plot_s_idx]

    def plot(self, penindex=-1, style=None):
        if self._graphicsView is not None:
            self._assemble_data()
            self.removePlots()
            self._gstGraphItem = GSTGraphItem(x=self._x, y=self._y)
            self._graphicsView.setAspectLocked()
            self._graphicsView.addItem(self._gstGraphItem)

    def replot(self):
        if self._gstGraphItem is not None:
            self._assemble_data()
            self._gstGraphItem.setData(self._x, self._y)

    def removePlots(self):
        if self._gstGraphItem:
            self._graphicsView.removeItem(self._gstGraphItem)
            self._gstGraphItem = None


