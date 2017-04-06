# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from trace import pens

from PyQt5 import QtCore
import numpy
from pyqtgraph.graphicsItems.ErrorBarItem import ErrorBarItem
from pyqtgraph.graphicsItems.PlotCurveItem import PlotCurveItem

from modules import enum
from trace.TraceCollection import TracePlotting
import time 
from modules import WeakMethod
from functools import partial
from collections import deque
from trace.pens import solidTransparentGrayPen, dashedTransparentGrayPen
import copy
from pyqtgraph import mkPen


def sort_lists_by(lists, key_list=0, desc=False):
    return list(zip(*sorted(zip(*lists), reverse=desc,
                 key=lambda x: x[key_list])))
    
class PlottedTrace(object):
    Styles = enum.enum('lines', 'points', 'linespoints', 'lines_with_errorbars', 'points_with_errorbars', 'linepoints_with_errorbars')
    PointsStyles = [ 1, 4 ]
    Types = enum.enum('default', 'steps')
    def __init__(self,Trace,graphicsView,penList=None,pen=0,style=None,plotType=None,
                 xColumn='x',yColumn='y',topColumn='top',bottomColumn='bottom',heightColumn='height',
                 rawColumn='raw', filtColumn='filt', tracePlotting=None, name="", xAxisLabel = None,
                 xAxisUnit = None, yAxisLabel = None, yAxisUnit = None, fill=True, windowName=None):
        self.category = None
        self.fill = fill
        if penList is None:
            penList = pens.penList
        self.penList = penList
        self._graphicsView = graphicsView
        if self._graphicsView is not None:
            if not hasattr(self._graphicsView, 'penUsageDict'):
                self._graphicsView.penUsageDict = [0]*len(pens.penList)
            self.penUsageDict = self._graphicsView.penUsageDict        # TODO circular reference
        self.trace = Trace
        self.curve = None
        self.auxiliaryCurves = deque()
        self.fitcurve = None
        self.errorBarItem = None
        self.auxiliaryErrorBarItem = None
        self.style = self.Styles.lines if style is None else style
        self.type = self.Types.default if plotType is None else plotType
        self.curvePen = 0
        self.name = name
        self.xAxisLabel = xAxisLabel
        self.xAxisUnit = xAxisUnit
        self.yAxisLabel = yAxisLabel
        self.yAxisUnit = yAxisUnit
        self.lastPlotTime = time.time()
        self.needsReplot = False
        #self.filt = None
        # we use pointers to the relevant columns in trace
        if tracePlotting is not None:
            self.tracePlotting = tracePlotting
            self._xColumn = tracePlotting.xColumn
            self._yColumn = tracePlotting.yColumn
            self._topColumn = tracePlotting.topColumn
            self._bottomColumn = tracePlotting.bottomColumn
            self._heightColumn = tracePlotting.heightColumn
            self._rawColumn = tracePlotting.rawColumn
            self._filtColumn = tracePlotting.filtColumn
            self.type = tracePlotting.type
            self.xAxisLabel = tracePlotting.xAxisLabel
            self.xAxisUnit = tracePlotting.xAxisUnit
            self.windowName = tracePlotting.windowName
        elif self.trace is not None:
            self._xColumn = xColumn
            self._yColumn = yColumn
            self._topColumn = topColumn
            self._bottomColumn = bottomColumn
            self._heightColumn = heightColumn
            self._rawColumn = rawColumn
            self._filtColumn = filtColumn
            self.tracePlotting = TracePlotting(xColumn=self._xColumn, yColumn=self._yColumn, topColumn=self._topColumn, bottomColumn=self._bottomColumn,   # TODO double check for reference
                                               heightColumn=self._heightColumn, rawColumn=self._rawColumn, filtColumn=self._filtColumn, name=name, type_=self.type, xAxisUnit=self.xAxisUnit,
                                               xAxisLabel=self.xAxisLabel, windowName=windowName )
            self.trace.addTracePlotting( self.tracePlotting )   # TODO check for reference
        self.windowName = windowName
        self.stylesLookup = { self.Styles.lines: partial( WeakMethod.ref(self.plotLines), errorbars=False),
                         self.Styles.points: partial( WeakMethod.ref(self.plotPoints), errorbars=False),
                         self.Styles.linespoints: partial( WeakMethod.ref(self.plotLinespoints), errorbars=False), 
                         self.Styles.lines_with_errorbars: partial( WeakMethod.ref(self.plotLines), errorbars=True),
                         self.Styles.points_with_errorbars: partial( WeakMethod.ref(self.plotPoints), errorbars=True),
                         self.Styles.linepoints_with_errorbars: partial( WeakMethod.ref(self.plotLinespoints), errorbars=True)}

    def setGraphicsView(self, graphicsView, name):
        if graphicsView!=self._graphicsView:
            self.removePlots()
            self._graphicsView = graphicsView
            self._graphicsView.vb.menu.axes[0].xlabelWidget.setText('aa')#self._graphicsView.getLabel('bottom'))
            self.windowName = name
            self.tracePlotting.windowName = name
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
        ra = self.trace.get(self._filtColumn, None)
        if ra is not None:
            return ra > 0
        return ra

    @filt.setter
    def filt(self, column):
        if self._filtColumn is None:
           self._filtColumn = self._yColumn+'_filt'
           self.tracePlotting.filtColumn = self._filtColumn
        self.trace[self._filtColumn] = column*1

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
                    self.errorBarItem = ErrorBarItem(x=(self.x), y=(self.y), height=(self.height),
                                                     pen=self.penList[penindex][0])
                    self._graphicsView.addItem(self.errorBarItem)
                else:
                    self.errorBarItem = ErrorBarItem(x=(self.x[self.filt]), y=(self.y[self.filt]), height=(self.height[self.filt]),
                                                     pen=self.penList[penindex][0])
                    self.auxiliaryErrorBarItem = ErrorBarItem(x=(self.x[~self.filt]), y=(self.y[~self.filt]), height=(self.height[~self.filt]),
                                                              pen=self.penList[penindex][5])
                    self._graphicsView.addItem(self.errorBarItem)
                    self._graphicsView.addItem(self.auxiliaryErrorBarItem)
            elif self.hasTopColumn and self.hasBottomColumn:
                if self.filt is None or all(self.filt):
                    self.errorBarItem = ErrorBarItem(x=(self.x), y=(self.y), top=(self.top), bottom=(self.bottom),
                                                     pen=self.penList[penindex][0])
                    self._graphicsView.addItem(self.errorBarItem)
                else:
                    self.errorBarItem = ErrorBarItem(x=(self.x[self.filt]), y=(self.y[self.filt]), top=(self.top[self.filt]), bottom=(self.bottom[self.filt]),
                                                               pen=self.penList[penindex][0])
                    self.auxiliaryErrorBarItem = ErrorBarItem(x=(self.x[~self.filt]), y=(self.y[~self.filt]), top=(self.top[~self.filt]), bottom=(self.bottom[~self.filt]),
                                                              pen=self.penList[penindex][5])
                    self._graphicsView.addItem(self.errorBarItem)
                    self._graphicsView.addItem(self.auxiliaryErrorBarItem)

    def findContiguousArrays(self, filt, extended=False):
        df = filt[0:-1]^filt[1::]
        rng = numpy.append(numpy.append(0.,numpy.array(range(1,len(filt)))[df]), len(filt))
        if extended:
            return [slice(int(rng[i]), int(min(rng[i+1]+1, len(filt)))) for i in range(len(rng)-1)]
        return [slice(int(rng[i]), int(rng[i+1])) for i in range(len(rng)-1)]

    def plotLines(self,penindex, errorbars=True ):
        if self._graphicsView is not None:
            if errorbars:
                self.plotErrorBars(penindex)
            if self.filt is None or all(self.filt):
                x, y = sort_lists_by((self.x, self.y), key_list=0) if len(self.x) > 0 else (self.x, self.y)
                self.curve = self._graphicsView.plot(numpy.array(x), numpy.array(y), pen=self.penList[penindex][0])
            else:
                x, y, filt = sort_lists_by((self.x, self.y, self.filt), key_list=0) if len(self.x) > 0 else (self.x, self.y, self.filt)
                self.curve = self._graphicsView.plot(numpy.array(x), numpy.array(y), pen=self.penList[penindex][0])
                contiguousSlices = self.findContiguousArrays(numpy.array(filt), extended=True)
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
            if errorbars:
                self.plotErrorBars(penindex)
            if self.filt is None or all(self.filt):
                self.curve = self._graphicsView.plot((self.x), (self.y), pen=None, symbol=self.penList[penindex][1],
                                                    symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
            else:
                self.curve = self._graphicsView.plot((self.x[self.filt]), (self.y[self.filt]), pen=None, symbol=self.penList[penindex][1],
                                                     symbolPen=self.penList[penindex][2], symbolBrush=self.penList[penindex][3])
                self.auxiliaryCurves.append(self._graphicsView.plot((self.x[~self.filt]), (self.y[~self.filt]), pen=None, symbol=self.penList[penindex][1],
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
                contiguousSlices = self.findContiguousArrays(numpy.array(filt))
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
        
    def replot(self):
        if self._graphicsView is not None:
            if len(self.x)>500 and time.time()-self.lastPlotTime<len(self.x)/500.:
                if not self.needsReplot:
                    self.needsReplot = True
                    QtCore.QTimer.singleShot(len(self.x)*2, self._replot) 
            else:
                self._replot()
            
    def _replot(self):
        if hasattr(self, 'curve') and self.curve is not None:
            if self.style not in self.PointsStyles and self.type==self.Types.default:
                x, y = sort_lists_by((self.x, self.y), key_list=0) if len(self.x) > 0 else (self.x, self.y)
                self.curve.setData( numpy.array(x), numpy.array(y) )
            else:
                self.curve.setData( (self.x), (self.y) )
        if hasattr(self, 'errorBarItem') and self.errorBarItem is not None:
            if self.hasHeightColumn:
                self.errorBarItem.setData(x=(self.x), y=(self.y), height=(self.height))
            else:
                self.errorBarItem.setOpts(x=(self.x), y=(self.y), top=(self.top), bottom=(self.bottom))
        if self.fitFunction is not None:
            if self.type==self.Types.default:
                self.replotFitFunction()
            elif self.type==self.Types.steps: 
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
        return self.tracePlotting.fitFunction if self.tracePlotting else None
    
    @fitFunction.setter
    def fitFunction(self, fitfunction):
        self.tracePlotting.fitFunction = fitfunction

#     def __del__(self):
#         super(PlottedTrace, self)__del__()

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
                
