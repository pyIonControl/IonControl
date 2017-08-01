from math import floor, ceil

import numpy
from pygsti import logl_terms, logl_max_terms

from modules.SequenceDict import SequenceDict
from pyqtgraphAddons.GSTGraphItem import GSTGraphItem
from trace.TraceCollection import StructurePlotting
from uiModules.ParameterTable import Parameter

class QubitPlotSettings:
    def __init__(self):
        self.gateSet = None


class PlottedStructureProperties:
    def __init__(self, gateset=None, axesIndex=(0, 1, 2, 3), collapse_minor=False, confidence_level=95):
        self.gateset = gateset
        self.axesIndex = axesIndex
        self.collapse_minor = collapse_minor
        self.confidence_level = confidence_level
        self.gate_noise = 0
        self.bright_error = 0
        self.dark_error = 0
        self.scale_threshold = 5

    def parameters(self):
        parameterDict = SequenceDict()
        parameterDict['scale_threshold'] = Parameter(name='scale_threshold', dataType='magnitude',
                                                      value=self.scale_threshold)
        parameterDict['confidence_level'] = Parameter(name='confidence_level', dataType='magnitude',
                                                      value=self.confidence_level)
        parameterDict['gate_noise'] = Parameter(name='gate_noise', dataType='magnitude',
                                                value=self.gate_noise)
        parameterDict['bright_error'] = Parameter(name='bright_error', dataType='magnitude',
                                                  value=self.bright_error)
        parameterDict['dark_error'] = Parameter(name='dark_error', dataType='magnitude',
                                                value=self.dark_error)
        return parameterDict

    def update(self, parameter):
        """update the parameter changed in the parameterTable"""
        setattr(self, parameter.name, parameter.value)


class PlottedStructure:
    def __init__(self, traceCollection, qubitDataKey=None, plot=None, windowName=None, properties=None, tracePlotting=None, name=None):
        self.qubitData = traceCollection.structuredData.get(qubitDataKey)
        self.traceCollection = traceCollection
        self.name = name or 'Qubit'
        self.windowName = windowName
        self._graphicsView = plot['view']
        self._graphicsWidget = plot['widget']
        self._gstGraphItem = None
        if tracePlotting is not None:
            self.tracePlotting = tracePlotting
            self.qubitData = self.traceCollection.structuredData.get(tracePlotting.key)
            self.name = tracePlotting.name
            self.windowName = tracePlotting.windowName
        elif self.traceCollection is not None:
            self.tracePlotting = StructurePlotting(key=qubitDataKey, name=self.name, windowName=self.windowName)
            self.traceCollection.addTracePlotting(self.tracePlotting)  # TODO check for reference
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
        self.labels = [str(s) for s in self._plot_s]
        self.properties = properties or PlottedStructureProperties()

    def setGraphicsView(self, graphicsView, name):
        if graphicsView['view']!=self._graphicsView:
            self.removePlots()
            self._graphicsView = graphicsView['view']
            self._graphicsWidget = graphicsView['widget']
            self._graphicsView.vb.menu.axes[0].xlabelWidget.setText('aa')#self._graphicsView.getLabel('bottom'))
            self.windowName = name
            self.tracePlotting.windowName = name
            self.plot()

    def default_color_scale(self, num):
        colors = [numpy.array((255, 255, 255)), numpy.array((0, 0, 0)), numpy.array((255, 0, 0))]
        num /= self.properties.scale_threshold
        if num < 0:
            return colors[0]
        if num + 1 > len(colors):
            return colors[-1]
        left = floor(num)
        right = ceil(num)
        minor = num - left
        return colors[left] * (1 - minor) + colors[right] * minor

    @property
    def curvePen(self):
        return 1 if self._gstGraphItem else 0

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
            if penindex != 0:
                self._gstGraphItem = GSTGraphItem(x=self._x, y=self._y, labels=self.labels, colorscale=self.default_color_scale)
                self._graphicsView.setAspectLocked()
                self._graphicsView.addItem(self._gstGraphItem)
                self._graphicsWidget.label_index = self._gstGraphItem.spatialIndex

    def replot(self):
        if self._gstGraphItem is not None:
            self._assemble_data()
            self._gstGraphItem.setData(self._x, self._y)

    def removePlots(self):
        if self._gstGraphItem:
            self._graphicsView.removeItem(self._gstGraphItem)
            self._gstGraphItem = None
            self._graphicsWidget.label_index = None
            self._graphicsView.setAspectLocked(False)

    def parameters(self):
        return self.properties.parameters()

    def update(self, parameter):
        self.properties.update(parameter)
        self.gateSet = self.qubitData.target_gateset.depolarize(gate_noise=self.properties.gate_noise)
        self.replot()

