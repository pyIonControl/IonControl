# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import lxml.etree as ElementTree
from pyqtgraph.parametertree import Parameter

from trace import pens

from PyQt5 import QtCore
import numpy
from pyqtgraph.graphicsItems.ErrorBarItem import ErrorBarItem
from pyqtgraph.graphicsItems.PlotCurveItem import PlotCurveItem

from modules import enum
import time
from modules import WeakMethod
from functools import partial
from collections import deque

from trace.ReducedTrace import ReducedTrace
from trace.sortlists import sort_lists_by
from uiModules.MagnitudeParameter import MagnitudeParameter


class PlottedTraceProperties:
    stateFields = ('averageSameX', 'combinePoints', 'averageType')
    xmlPropertFields = ('averageSameX', 'combinePoints', 'averageType')
    def __init__(self, averageSameX=False, combinePoints=0, averageType=None):
        self.averageSameX = averageSameX
        self.combinePoints = combinePoints
        self.averageType = averageType

    def __getstate__(self):
        return {key: getattr(self, key) for key in self.stateFields}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def paramDef(self):
        return [{'name': 'average same x', 'type': 'bool', 'value': self.averageSameX, 'field': 'averageSameX'},
         {'name': 'combine Points', 'type': 'magnitude', 'value': self.combinePoints, 'field': 'combinePoints'},
         {'name': 'averageType', 'type': 'magnitude', 'value': self.averageType,'field': 'averageType'}]

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
                value = float(data.m_as('')) if isinstance(data, MagnitudeParameter) else data
                setattr(self, param.opts['field'], value)
                prop_changed = True
            elif change == 'activated':
                getattr(self, param.opts['field'])()
        return prop_changed

    def copy(self):
        p = PlottedTraceProperties()
        p.__setstate__(self.__getstate__())
        return p

    def toXML(self, element):
        e = ElementTree.SubElement(element, 'PlottedTraceProperties',
                               dict((name, str(getattr(self, name))) for name in self.xmlPropertFields))
        #sub = ElementTree.subElement(e, 'Properties')
        return e


class PlottedTrace(object):
    Styles = enum.enum('lines', 'points', 'linespoints', 'lines_with_errorbars', 'points_with_errorbars', 'linepoints_with_errorbars')
    PointsStyles = [ 1, 4 ]
    Types = enum.enum('default', 'steps')
    serializeFields = ('_xColumn','_yColumn','_topColumn', '_bottomColumn','_heightColumn', '_filtColumn', 'name',
                       'type', 'xAxisUnit', 'xAxisLabel', 'yAxisLabel', 'windowName', '_rawColumn', 'fill', 'style',
                       'type', '_fitFunction', 'properties')
    fieldReplacements = {'xColumn': '_xColumn',  'yColumn': '_yColumn', 'topColumn': '_topColumn',
                          'bottomColumn': '_bottomColumn', 'heightColumn': '_heightColumn',
                          'filtColumn': '_filtColumn', 'rawColumn': '_rawColumn'}
    def __init__(self, Trace=None, graphics=None, penList=None, pen=0, style=None, plotType=None,
                 xColumn='x', yColumn='y', topColumn='top', bottomColumn='bottom', heightColumn='height',
                 rawColumn='raw', filtColumn=None, name="", xAxisLabel=None,
                 xAxisUnit=None, yAxisLabel=None, yAxisUnit=None, fill=True, windowName=None,
                 averageSameX=False, combinePoints=0, averageType=None):
        self.properties = PlottedTraceProperties(averageSameX=averageSameX, combinePoints=combinePoints, averageType=averageType)
        self.trace = None
        self._xColumn = xColumn
        self._yColumn = yColumn
        self._topColumn = topColumn
        self._bottomColumn = bottomColumn
        self._heightColumn = heightColumn
        self._rawColumn = rawColumn
        self._filtColumn = filtColumn
        self.xAxisUnit = xAxisUnit
        self.xAxisLabel = xAxisLabel
        self.yAxisUnit = yAxisUnit
        self.yAxisLabel = yAxisLabel
        self.fill = fill
        self.style = self.Styles.lines if style is None else style
        self.type = self.Types.default if plotType is None else plotType
        self.setup(Trace, graphics, penList, pen, windowName, name)
        self._fitFunction = None

    def setup(self, traceCollection, graphics, penList=None, pen=-1, windowName=None, name=None, properties=None):
        self.category = None
        if penList is None:
            penList = pens.penList
        self.penList = penList
        self._graphicsView = graphics and graphics.get('view')
        if self._graphicsView is not None:
            if not hasattr(self._graphicsView, 'penUsageDict'):
                self._graphicsView.penUsageDict = [0]*len(pens.penList)
            self.penUsageDict = self._graphicsView.penUsageDict        # TODO circular reference
        self.curve = None
        self.auxiliaryCurves = deque()
        self.fitcurve = None
        self.errorBarItem = None
        self.auxiliaryErrorBarItem = None
        self.curvePen = 0
        self.name = name
        self.lastPlotTime = time.time()
        self.needsReplot = False
        # we use pointers to the relevant columns in trace
        self.windowName = windowName
        self.stylesLookup = {self.Styles.lines: partial(WeakMethod.ref(self.plotLines), errorbars=False),
                             self.Styles.points: partial(WeakMethod.ref(self.plotPoints), errorbars=False),
                             self.Styles.linespoints: partial(WeakMethod.ref(self.plotLinespoints), errorbars=False),
                             self.Styles.lines_with_errorbars: partial(WeakMethod.ref(self.plotLines), errorbars=True),
                             self.Styles.points_with_errorbars: partial(WeakMethod.ref(self.plotPoints),
                                                                        errorbars=True),
                             self.Styles.linepoints_with_errorbars: partial(WeakMethod.ref(self.plotLinespoints),
                                                                            errorbars=True)}
        if self.trace is None and traceCollection is not None:
            traceCollection.addPlotting(self)
        self.trace = traceCollection
        self._reducedTrace = ReducedTrace(traceCollection, self.properties.averageSameX, self.properties.combinePoints,
                                          self.properties.averageType,
                                          self._xColumn, self._yColumn, self._bottomColumn, self._topColumn,
                                          self._heightColumn)

    def __getstate__(self):
        return {key: getattr(self, key) for key in PlottedTrace.serializeFields}

    def __setstate__(self, state):
        self.__dict__.update({PlottedTrace.fieldReplacements.get(key, key): value for key, value in state.items()})
        self.__dict__.setdefault('_fitFunction', None)
        self.__dict__.setdefault('trace', None)
        self.__dict__.setdefault('yAxisLabel', None)
        self.__dict__.setdefault('properties', PlottedTraceProperties())
        self._reducedTrace = ReducedTrace(self.trace, self.properties.averageSameX, self.properties.combinePoints,
                                          self.properties.averageType,
                                          self._xColumn, self._yColumn, self._bottomColumn, self._topColumn,
                                          self._heightColumn)

    def toXML(self, element):
        e = ElementTree.SubElement(element, 'TracePlotting',
                               dict((name, str(getattr(self, name))) for name in self.serializeFields))
        if self.fitFunction:
            self.fitFunction.toXmlElement(e)
        self.properties.toXML(e)
        return e

    def setGraphicsView(self, graphicsView, name):
        graphicsView = graphicsView['view']
        if graphicsView!=self._graphicsView:
            self.removePlots()
            self._graphicsView = graphicsView
            self._graphicsView.vb.menu.axes[0].xlabelWidget.setText('aa')#self._graphicsView.getLabel('bottom'))
            self.windowName = name
            self.plot()

    @property
    def okToDelete(self):
        """A trace is OK to delete if it has been finalized"""
        return 'traceFinalized' in self.trace.description

    @property
    def traceCollection(self):
        """This is to make the code more readable while maintaining backwards compatibility. self.traceCollection is the same thing as self.trace."""
        return self.trace

    @traceCollection.setter
    def traceCollection(self, t):
        self.trace = t

    @property
    def hasTopColumn(self):
        return self._topColumn and self._topColumn in self.trace

    @property
    def hasBottomColumn(self):
        return self._bottomColumn and self._bottomColumn in self.trace

    @property
    def hasHeightColumn(self):
        return self._heightColumn and self._heightColumn in self.trace

    @property
    def hasRawColumn(self):
        return self._rawColumn and self._rawColumn in self.trace
        
    def timeintervalAppend(self, timeinterval, maxPoints=0):
        self.trace.timeintervalAppend(timeinterval, maxPoints)
        
    @property
    def timeinterval(self):
        return self.trace.timeinterval
        
    @timeinterval.setter
    def timeinterval(self, val):
        self.trace.timeinterval = val
        
    @property
    def x(self):
        return self.trace[self._xColumn]
    
    @x.setter
    def x(self, column):
        self.trace[self._xColumn] = column

    @property
    def y(self):
        return self.trace[self._yColumn]
    
    @y.setter
    def y(self, column):
        self.trace[self._yColumn] = column

    @property
    def top(self):
        return self.trace[self._topColumn]
    
    @top.setter
    def top(self, column):
        self.trace[self._topColumn] = column

    @property
    def bottom(self):
        return self.trace[self._bottomColumn]
    
    @bottom.setter
    def bottom(self, column):
        self.trace[self._bottomColumn] = column

    @property
    def height(self):
        return self.trace[self._heightColumn]
    
    @height.setter
    def height(self, column):
        self.trace[self._heightColumn] = column

    @property
    def raw(self):
        return self.trace[self._rawColumn]
    
    @raw.setter
    def raw(self, column):
        self.trace[self._rawColumn] = column

    @property
    def filt(self):
        return self.trace.get(self._filtColumn, None)

    @filt.setter
    def filt(self, column):
        if self._filtColumn is None:
           self._filtColumn = self._yColumn+'_filt'
        self.trace[self._filtColumn] = column

    @property
    def isPlotted(self):
        return self.curvePen>0
    
    @isPlotted.setter
    def isPlotted(self, plotted):
        if plotted != (self.curvePen>0):
            self.plot( -1 if plotted else 0 )

    def removePlots(self):
        if self._graphicsView is not None:
            if self.curve is not None:
                self._graphicsView.removeItem(self.curve)
                self.curve = None
                self.penUsageDict[self.curvePen] -= 1
            while self.auxiliaryCurves:
                self._graphicsView.removeItem(self.auxiliaryCurves.pop())
            if self.errorBarItem is not None:
                self._graphicsView.removeItem(self.errorBarItem)  
                self.errorBarItem = None
            if self.auxiliaryErrorBarItem is not None:
                self._graphicsView.removeItem(self.auxiliaryErrorBarItem)
                self.auxiliaryErrorBarItem = None
            if self.fitcurve is not None:
                self._graphicsView.removeItem(self.fitcurve)
                self.fitcurve = None
                
    def plotFitfunction(self, penindex):
        if self.fitFunction and self._graphicsView is not None:
            self.fitFunctionPenIndex = penindex
            self.fitx = numpy.linspace(numpy.nanmin(self.x), numpy.nanmax(self.x), 300)
            self.fity = self.fitFunction.value(self.fitx)
            if self.fitcurve is not None:
                self._graphicsView.removeItem(self.fitcurve)
            self.fitcurve = self._graphicsView.plot(self.fitx, self.fity, pen=self.penList[penindex][0])
 
    def replotFitFunction(self):
        if self.fitFunction and self._graphicsView is not None:
            self.fitx = numpy.linspace(numpy.nanmin(self.x), numpy.nanmax(self.x), 300)
            self.fity = self.fitFunction.value(self.fitx)
            if self.fitcurve is not None:
                self.fitcurve.setData( self.fitx, self.fity )
            else:
                self.__dict__.setdefault( 'fitFunctionPenIndex', self.curvePen )
                self.fitcurve = self._graphicsView.plot(self.fitx, self.fity, pen=self.penList[self.fitFunctionPenIndex][0])
 
    def plotStepsFitfunction(self, penindex):
        if self.fitFunction and self._graphicsView is not None:
            self.fitFunctionPenIndex = penindex
            self.fitx = numpy.linspace(numpy.nanmin(self.x)+0.5, numpy.nanmax(self.x)-1.5, len(self.x)-1 )
            self.fity = self.fitFunction.value(self.fitx)
            if self.fitcurve is not None:
                self._graphicsView.removeItem(self.fitcurve)
            self.fitcurve = self._graphicsView.plot(self.fitx, self.fity, pen=self.penList[penindex][0])
            
    def replotStepsFitFunction(self):
        if self.fitFunction and self._graphicsView is not None:
            self.fitx = numpy.linspace(numpy.nanmin(self.x)+0.5, numpy.nanmax(self.x)-1.5, len(self.x)-1 )
            self.fity = self.fitFunction.value(self.fitx)
            if self.fitcurve is not None:
                self.fitcurve.setData( self.fitx, self.fity )
            else:
                self.__dict__.setdefault( 'fitFunctionPenIndex', self.curvePen )
                self.fitcurve = self._graphicsView.plot(self.fitx, self.fity, pen=self.penList[self.fitFunctionPenIndex][0])

    def plotErrorBars(self, penindex):
        if self._graphicsView is not None:
            if self.hasHeightColumn:
                if self.filt is None or all(self.filt):
                    self.errorBarItem = ErrorBarItem(x=numpy.array(self.x),
                                                     y=numpy.array(self.y),
                                                     height=numpy.array(self.height),
                                                     pen=self.penList[penindex][0])
                    self._graphicsView.addItem(self.errorBarItem)
                else:
                    self.errorBarItem = ErrorBarItem(x=numpy.array(self.x)[numpy.array(self.filt)>0],
                                                     y=numpy.array(self.y)[numpy.array(self.filt)>0],
                                                     height=numpy.array(self.height)[numpy.array(self.filt)>0],
                                                     pen=self.penList[penindex][0])
                    self.auxiliaryErrorBarItem = ErrorBarItem(x=(numpy.array(self.x)[numpy.array(self.filt)<1]),
                                                              y=(numpy.array(self.y)[numpy.array(self.filt)<1]),
                                                              height=(numpy.array(self.height)[numpy.array(self.filt)<1]),
                                                              pen=self.penList[penindex][5])
                    self._graphicsView.addItem(self.errorBarItem)
                    self._graphicsView.addItem(self.auxiliaryErrorBarItem)
            elif self.hasTopColumn and self.hasBottomColumn:
                if self.filt is None or all(self.filt):
                    self.errorBarItem = ErrorBarItem(x=numpy.array(self.x),
                                                     y=numpy.array(self.y),
                                                     top=numpy.array(self.top),
                                                     bottom=numpy.array(self.bottom),
                                                     pen=self.penList[penindex][0])
                    self._graphicsView.addItem(self.errorBarItem)
                else:
                    self.errorBarItem = ErrorBarItem(x=(numpy.array(self.x)[numpy.array(self.filt)>0]),
                                                     y=(numpy.array(self.y)[numpy.array(self.filt)>0]),
                                                     top=(numpy.array(self.top)[numpy.array(self.filt)>0]),
                                                     bottom=(numpy.array(self.bottom)[numpy.array(self.filt)>0]),
                                                     pen=self.penList[penindex][0])
                    self.auxiliaryErrorBarItem = ErrorBarItem(x=(numpy.array(self.x)[numpy.array(self.filt)<1]),
                                                              y=(numpy.array(self.y)[numpy.array(self.filt)<1]),
                                                              top=(numpy.array(self.top)[numpy.array(self.filt)<1]),
                                                              bottom=(numpy.array(self.bottom)[numpy.array(self.filt)<1]),
                                                              pen=self.penList[penindex][5])
                    self._graphicsView.addItem(self.errorBarItem)
                    self._graphicsView.addItem(self.auxiliaryErrorBarItem)

    def findContiguousArrays(self, filt, extended=False):
        df = filt[:-1]^filt[1:]
        rng = numpy.append(numpy.append(0.,numpy.array(range(1,len(filt)))[df]), len(filt))
        if extended:
            return [slice(int(rng[i]), int(min(rng[i+1]+1, len(filt)))) for i in range(len(rng)-1)]
        return [slice(int(rng[i]), int(rng[i+1])) for i in range(len(rng)-1)]

    def plotLines(self,penindex, errorbars=True ):
        if self._graphicsView is not None:
            if self.properties.averageSameX or self.properties.combinePoints:
                x, y = self._reducedTrace.plotData
                self.curve = self._graphicsView.plot(x, y, pen=self.penList[penindex][0])
            else:
                if errorbars:
                    self.plotErrorBars(penindex)
                if self.filt is None or all(self.filt):
                    x, y = sort_lists_by((self.x, self.y), key_list=0) if len(self.x) > 0 else (self.x, self.y)
                    self.curve = self._graphicsView.plot(numpy.array(x), numpy.array(y), pen=self.penList[penindex][0])
                else:
                    x, y, filt = sort_lists_by((self.x, self.y, self.filt), key_list=0) if len(self.x) > 0 else (self.x, self.y, self.filt)
                    self.curve = self._graphicsView.plot(numpy.array(x), numpy.array(y), pen=self.penList[penindex][0])
                    contiguousSlices = self.findContiguousArrays(numpy.array(filt)>0, extended=True)
                    for cslice in contiguousSlices:
                        if not numpy.array(filt)[cslice][0]:
                            self.auxiliaryCurves.append(self._graphicsView.plot(numpy.array(x)[cslice], numpy.array(y)[cslice], pen=self.penList[penindex][5]))
            if self.xAxisLabel:
                if self.xAxisUnit:
                    self._graphicsView.setLabel('bottom', text = "{0} ({1})".format(self.xAxisLabel, self.xAxisUnit))
                else:
                    self._graphicsView.setLabel('bottom', text = "{0}".format(self.xAxisLabel))
            else:
                self._graphicsView.setLabel('bottom', text='')
                self._graphicsView.showLabel('bottom', show=False)
            if self.yAxisLabel:
                if self.yAxisUnit:
                    self._graphicsView.setLabel('left', text = "{0} ({1})".format(self.yAxisLabel, self.yAxisUnit))
                else:
                    self._graphicsView.setLabel('left', text = "{0}".format(self.yAxisLabel))
            else:
                self._graphicsView.setLabel('left', text='')
                self._graphicsView.showLabel('left', show=False)

    def plotPoints(self,penindex, errorbars=True ):
        if self._graphicsView is not None:
            if self.properties.averageSameX or self.properties.combinePoints:
                x, y = self._reducedTrace.plotData
                self.curve = self._graphicsView.plot(x, y, pen=None, symbol=self.penList[penindex][1],
                                                     symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
            else:
                if errorbars:
                    self.plotErrorBars(penindex)
                if self.filt is None or all(self.filt):
                    self.curve = self._graphicsView.plot((self.x), (self.y), pen=None, symbol=self.penList[penindex][1],
                                                        symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
                else:
                    self.curve = self._graphicsView.plot((numpy.array(self.x)[numpy.array(self.filt[:len(self.x)])>0]), (numpy.array(self.y)[numpy.array(self.filt[:len(self.y)])>0]), pen=None, symbol=self.penList[penindex][1],
                                                         symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
                    self.auxiliaryCurves.append(self._graphicsView.plot((numpy.array(self.x)[numpy.array(self.filt[:len(self.x)])<1]), (numpy.array(self.y)[numpy.array(self.filt[:len(self.y)])<1]), pen=None, symbol=self.penList[penindex][1],
                                                          symbolPen=self.penList[penindex][5], symbolBrush=self.penList[penindex][6]))
            if self.xAxisLabel:
                if self.xAxisUnit:
                    self._graphicsView.setLabel('bottom', text = "{0} ({1})".format(self.xAxisLabel, self.xAxisUnit))
                else:
                    self._graphicsView.setLabel('bottom', text = "{0}".format(self.xAxisLabel))
            else:
                self._graphicsView.setLabel('bottom', text='')
                self._graphicsView.showLabel('bottom', show=False)
            if self.yAxisLabel:
                if self.yAxisUnit:
                    self._graphicsView.setLabel('left', text = "{0} ({1})".format(self.yAxisLabel, self.yAxisUnit))
                else:
                    self._graphicsView.setLabel('left', text = "{0}".format(self.yAxisLabel))
            else:
                self._graphicsView.setLabel('left', text='')
                self._graphicsView.showLabel('left', show=False)

    def plotLinespoints(self,penindex, errorbars=True ):
        if self._graphicsView is not None:
            if self.properties.averageSameX or self.properties.combinePoints:
                x, y = self._reducedTrace.plotData
                self.curve = self._graphicsView.plot(x, y, pen=self.penList[penindex][0], symbol=self.penList[penindex][1],
                                                     symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
            else:
                if errorbars:
                    self.plotErrorBars(penindex)
                if self.filt is None or all(self.filt):
                    x, y = sort_lists_by( (self.x, self.y), key_list=0)
                    self.curve = self._graphicsView.plot( numpy.array(x), numpy.array(y), pen=self.penList[penindex][0], symbol=self.penList[penindex][1],
                                                          symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
                else:
                    x, y, filt = sort_lists_by((self.x, self.y, self.filt), key_list=0) if len(self.x) > 0 else (self.x, self.y, self.filt)
                    self.curve = self._graphicsView.plot( numpy.array(x), numpy.array(y), pen=self.penList[penindex][0], symbol=self.penList[penindex][1],
                                                          symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
                    contiguousSlices = self.findContiguousArrays(numpy.array(filt)>0)
                    for cslice in contiguousSlices:
                        if not numpy.array(filt)[cslice][0]:
                            self.auxiliaryCurves.append(self._graphicsView.plot( numpy.array(x)[cslice], numpy.array(y)[cslice], pen=self.penList[penindex][5], symbol=self.penList[penindex][1],
                                                          symbolPen=self.penList[penindex][5], symbolBrush=self.penList[penindex][6]))
            if self.xAxisLabel:
                if self.xAxisUnit:
                    self._graphicsView.setLabel('bottom', text = "{0} ({1})".format(self.xAxisLabel, self.xAxisUnit))
                else:
                    self._graphicsView.setLabel('bottom', text = "{0}".format(self.xAxisLabel))
            else:
                self._graphicsView.setLabel('bottom', text='')
                self._graphicsView.showLabel('bottom', show=False)
            if self.yAxisLabel:
                if self.yAxisUnit:
                    self._graphicsView.setLabel('left', text = "{0} ({1})".format(self.yAxisLabel, self.yAxisUnit))
                else:
                    self._graphicsView.setLabel('left', text = "{0}".format(self.yAxisLabel))
            else:
                self._graphicsView.setLabel('left', text='')
                self._graphicsView.showLabel('left', show=False)

    def plotSteps(self, penindex):
        if self._graphicsView is not None:
            mycolor = list(self.penList[penindex][4])
            mycolor[3] = 80
            self.curve = PlotCurveItem(self.x, self.y, stepMode=True, fillLevel=0 if self.fill else None, brush=mycolor if self.fill else None, pen=self.penList[penindex][0])
            if self.xAxisLabel:
                if self.xAxisUnit:
                    self._graphicsView.setLabel('bottom', text = "{0} ({1})".format(self.xAxisLabel, self.xAxisUnit))
                else:
                    self._graphicsView.setLabel('bottom', text = "{0}".format(self.xAxisLabel))
            else:
                self._graphicsView.setLabel('bottom', text='')
                self._graphicsView.showLabel('bottom', show=False)
            if self.yAxisLabel:
                if self.yAxisUnit:
                    self._graphicsView.setLabel('left', text = "{0} ({1})".format(self.yAxisLabel, self.yAxisUnit))
                else:
                    self._graphicsView.setLabel('left', text = "{0}".format(self.yAxisLabel))
            else:
                self._graphicsView.setLabel('left', text='')
                self._graphicsView.showLabel('left', show=False)
            self._graphicsView.addItem( self.curve )
            self.curvePen = penindex
    
    def plot(self,penindex=-1,style=None):
        if self._graphicsView is not None:
            self.style = self.style if style is None else style
            self.removePlots()
            penindex = { -2: self.__dict__.get('curvePen', 0),
                         -1: sorted(zip(self.penUsageDict, list(range(len(self.penUsageDict)))))[1][1] }.get(penindex, penindex)
            if penindex>0:
                if self.type==self.Types.default:
                    self.plotFitfunction(penindex)
                    self.stylesLookup.get(self.style, self.plotLines)(penindex)
                elif self.type ==self.Types.steps:
                    self.plotStepsFitfunction(penindex+1)
                    self.plotSteps(penindex)
                if self.xAxisLabel:
                    if self.xAxisUnit:
                        self._graphicsView.vb.menu.axes[0].xlabelWidget.setText('{0} ({1})'.format(self.xAxisLabel, self.xAxisUnit))#self._graphicsView.getLabel('bottom'))
                    else:
                        self._graphicsView.vb.menu.axes[0].xlabelWidget.setText(self.xAxisLabel)
                else:
                    self._graphicsView.vb.menu.axes[0].xlabelWidget.setText('')
                if self.yAxisLabel:
                    if self.yAxisUnit:
                        self._graphicsView.vb.menu.axes[1].ylabelWidget.setText('{0} ({1})'.format(self.yAxisLabel, self.yAxisUnit))#self._graphicsView.getLabel('bottom'))
                    else:
                        self._graphicsView.vb.menu.axes[1].ylabelWidget.setText(self.yAxisLabel)
                else:
                    self._graphicsView.vb.menu.axes[1].ylabelWidget.setText('')
                self._graphicsView.ctrlMenu.titleWidget.setText('')
                self._graphicsView.setTitle()
                self.penUsageDict[penindex] += 1
            self.curvePen = penindex
        
    def replot(self, forceNow=False):
        if self._graphicsView is not None:
            if not forceNow and len(self.x)>500 and time.time()-self.lastPlotTime<len(self.x)/500.:
                if not self.needsReplot:
                    self.needsReplot = True
                    QtCore.QTimer.singleShot(len(self.x)*2, self._replot) 
            else:
                self._replot()

    def _replot(self):
        if hasattr(self, 'curve') and self.curve is not None:
            if self.type == self.Types.default:
                x, y = self._reducedTrace.plotData
                self.curve.setData(numpy.array(x), numpy.array(y))
            else:
                self.curve.setData(self.x, self.y)
        if hasattr(self, 'errorBarItem') and self.errorBarItem is not None:
            if self.hasHeightColumn:
                self.errorBarItem.setData(x=numpy.array(self.x), y=numpy.array(self.y), height=numpy.array(self.height))
            else:
                self.errorBarItem.setOpts(x=numpy.array(self.x), y=numpy.array(self.y), top=numpy.array(self.top), bottom=numpy.array(self.bottom))
        if self.fitFunction is not None:
            if self.type == self.Types.default:
                self.replotFitFunction()
            elif self.type == self.Types.steps:
                self.replotStepsFitFunction()
        elif self.fitcurve is not None:
            self._graphicsView.removeItem(self.fitcurve)
            self.fitcurve = None
        self.lastPlotTime = time.time()
        self.needsReplot = False

    def setView(self, graphicsView ):
        self.removePlots()
        self._graphicsView = graphicsView
        self.plot(-1)
            
    @property
    def fitFunction(self):
        return self._fitFunction

    @fitFunction.setter
    def fitFunction(self, fitfunction):
        self._fitFunction = fitfunction

    def parameters(self):
        return Parameter.create(name='Settings', type='group', children=[])

    def parameters(self):
        self._parameter = Parameter.create(name='Settings', type='group', children=self.properties.paramDef())
        self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        return self._parameter

    def update(self, param, changes):
        if self.properties.update(param, changes):
            changed = self._reducedTrace.update(self.properties.averageSameX, self.properties.combinePoints, self.properties.averageType)
            if changed:
                self.replot(True)

if __name__=="__main__":
    from trace.TraceCollection import TraceCollection
    import gc
    import sys
    plottedTrace = PlottedTrace(TraceCollection(), None, pens.penList)
    print(sys.getrefcount(plottedTrace))
    plottedTrace = None
    del plottedTrace
    gc.collect()
    input("Press Enter")
                
