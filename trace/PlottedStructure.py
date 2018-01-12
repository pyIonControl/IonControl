import hashlib
import lxml.etree as ElementTree
from math import floor, ceil, sqrt

import numpy
from PyQt5 import QtCore
from pygsti.objects import POVM

from gateSequence.loglikelyhood import logl_terms, logl_max_terms
from pyqtgraph.parametertree.Parameter import Parameter

from modules.SQLiteLRUCache import SQLiteLRUCache
from pyqtgraphAddons.GSTGraphItem import GSTGraphItem


class QubitPlotSettings:
    def __init__(self):
        self.gateSet = None


def digest(bytes_obj):
    m = hashlib.sha256()
    m.update(bytes_obj)
    return m.hexdigest()


class PlottedStructureProperties:
    stateFields = ('gateset', 'axesIndex', 'collapse_minor', 'confidence_level', 'gate_noise', 'bright_error',
                   'dark_error', 'scale_threshold')
    xmlPropertFields = ('collapse_minor', 'confidence_level', 'gate_noise', 'bright_error',
                        'dark_error', 'scale_threshold')
    def __init__(self, gateset=None, axesIndex=(0, 1, 2, 3), collapse_minor=False, confidence_level=95):
        self.gateset = gateset
        self.axesIndex = axesIndex
        self.collapse_minor = collapse_minor
        self.confidence_level = confidence_level
        self.gate_noise = 0.
        self.bright_error = 0.
        self.dark_error = 0.
        self.scale_threshold = 5.

    def __getstate__(self):
        return {key: getattr(self, key) for key in self.stateFields}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def paramDef(self):
        return [{'name': 'scale threshold', 'type': 'magnitude', 'value': self.scale_threshold, 'field': 'scale_threshold'},
         {'name': 'confidence_level', 'type': 'magnitude', 'value': self.confidence_level, 'field': 'confidence_level'},
         {'name': 'gate_noise', 'type': 'magnitude', 'value': self.gate_noise,'field': 'gate_noise'},
         {'name': 'bright_error', 'type': 'magnitude', 'value': self.bright_error, 'field': 'bright_error'},
         {'name': 'dark_error', 'type': 'magnitude', 'value': self.bright_error, 'field': 'dark_error'}]

    def parameters(self):
        self._parameter = Parameter.create(name='Settings', type='group', children=self.paramDef())
        self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        return self._parameter

    def update(self, param, changes):
        """
        update the parameter, called by the signal of pyqtgraph parametertree
        """
        prop_changed = False
        for param, change, data in changes:
            if change == 'value':
                value = float(data.m_as(''))
                setattr(self, param.opts['field'], value)
                prop_changed = True
            elif change == 'activated':
                getattr(self, param.opts['field'])()
        return prop_changed

    def copy(self):
        p = PlottedStructureProperties()
        p.__setstate__(self.__getstate__())
        return p

    def toXML(self, element):
        e = ElementTree.SubElement(element, 'PlottedStructureProperties',
                               dict((name, str(getattr(self, name))) for name in self.xmlPropertFields))
        #sub = ElementTree.subElement(e, 'Properties')
        return e


class PlottedStructure:
    _evaltree_cache = SQLiteLRUCache(capacity=64, filename="evaltree.db")
    serializeFields = ('qubitDataKey', 'name', 'windowName', 'properties')
    xmlPropertFields = ('qubitDataKey', 'name', 'windowName')
    def __init__(self, traceCollection, qubitDataKey, plot=None, windowName=None, properties=None, tracePlotting=None, name=None):
        self.qubitDataKey = qubitDataKey
        self.name = name
        self.windowName = windowName
        self.properties = properties
        self.setup(traceCollection, plot)

    def setup(self, traceCollection, graphics, penList=None, pen=-1, windowName=None, name=None, properties=None):
        self.traceCollection = traceCollection
        self.qubitData = traceCollection.structuredData.get(self.qubitDataKey)
        self.name = name or self.name or 'Qubit'
        self.windowName = windowName or self.windowName
        self._graphicsView = graphics and graphics['view']
        self._graphicsWidget = graphics and graphics['widget']
        self._gstGraphItem = None
        lengths = sorted(set([k[0] for k in self.qubitData.plaquettes.keys()]))
        germs = sorted(set([k[1] for k in self.qubitData.plaquettes.keys()]))
        self._lookup = dict()
        for (l, g), p in self.qubitData.plaquettes.items():
            l_id = lengths.index(l)
            g_id = germs.index(g)
            for r, c, s in p:
                self._lookup[(l_id, g_id, r, c)] = s
        self._x, self._plot_s = list(zip(*sorted(self._lookup.items())))
        self._createIndex()
        self.labels = [str(s) for s in self._plot_s]
        self.properties = properties or self.properties or PlottedStructureProperties()
        self.traceCollection.addPlotting(self)
        self.updateGateSet()

    def _createIndex(self):
        d = {v:i for i,v in enumerate(self.qubitData.gatestring_list)}
        self._plot_s_idx = [d.get(s) for s in self._plot_s]

    def __getstate__(self):
        return {key: getattr(self, key) for key in PlottedStructure.serializeFields}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def toXML(self, element):
        e = ElementTree.SubElement(element, 'StructurePlotting',
                               dict((name, str(getattr(self, name))) for name in self.xmlPropertFields))
        self.properties.toXML(e)
        return e

    def setGraphicsView(self, graphicsView, name):
        if graphicsView['view']!=self._graphicsView:
            self.removePlots()
            self._graphicsView = graphicsView['view']
            self._graphicsWidget = graphicsView['widget']
            self._graphicsView.vb.menu.axes[0].xlabelWidget.setText('aa')#self._graphicsView.getLabel('bottom'))
            self.windowName = name
            self.tracePlotting.windowName = name
            self.plot()

    colors = [numpy.array((255, 255, 255)), numpy.array((0, 0, 0)), numpy.array((255, 0, 0))]
    def default_color_scale(self, num):
        num /= self.properties.scale_threshold
        if num < 0:
            return self.colors[0]
        if num + 1 > len(self.colors):
            return self.colors[-1]
        left = floor(num)
        right = ceil(num)
        minor = num - left
        return self.colors[left] * (1 - minor) + self.colors[right] * minor

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
        self._spamLabels = list(self._gateSet.povms['Mz'].keys())  # this list fixes the ordering of the spam labels
        self._spam_lbl_rows = {sl: i for (i, sl) in enumerate(self._spamLabels)}
        self._probs = numpy.empty((len(self._spamLabels), len(self.qubitData.gatestring_list)), 'd')
        try:
            m = hashlib.sha1()
            m.update(str(self._gateSet).encode())
            m.update((",".join([str(s) for s in self.qubitData.gatestring_list])).encode())
            evaltree_dependency_hash = m.hexdigest()
            self._evaltree = PlottedStructure._evaltree_cache[evaltree_dependency_hash]
        except KeyError:
            self._evaltree = self._gateSet.bulk_evaltree(self.qubitData.gatestring_list)
            PlottedStructure._evaltree_cache[evaltree_dependency_hash] = self._evaltree
        evalTree, lookup, outcome_lookup = self._evaltree
        self._gateSet.bulk_fill_probs(self._probs, evalTree, (-1e6, 1e6))

    def _assemble_data(self):
        evalTree, lookup, outcome_lookup = self._evaltree
        l = logl_terms(gatestring_list=self.qubitData.gatestring_list, lookup=lookup,
                       countVecMx=self.qubitData.countVecMx, totalCntVec=self.qubitData.totalCntVec,
                       probs=self._probs)
        l_max = logl_max_terms(gatestring_list=self.qubitData.gatestring_list,
                               countVecMx=self.qubitData.countVecMx, totalCntVec=self.qubitData.totalCntVec,
                               lookup=lookup)
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
        self._parameter = Parameter.create(name='Settings', type='group', children=self.properties.paramDef())
        self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        return self._parameter

    def updateGateSet(self):
        temp_gs = self.qubitData.target_gateset.depolarize(gate_noise=self.properties.gate_noise)
        temp_gs['Mz'] = POVM({'0': [1 / sqrt(2) * (1 - self.properties.bright_error), 0, 0,
                                          1 / sqrt(2) * (1 - self.properties.dark_error)],
                                    '1': [1 / sqrt(2) * (1 - self.properties.bright_error), 0, 0,
                                          -1 / sqrt(2) * (1 - self.properties.dark_error)]})
        self.gateSet = temp_gs

    def update(self, param, changes):
        if self.properties.update(param, changes):
            self.updateGateSet()
            self.replot()
