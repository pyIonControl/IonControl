# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
This is the main plotting element used in the control program. It adds the
coordinates of the cursor position as a second element also allows one to
copy the coordinates to the clipboard. It uses a custom version of PlotItem
which includes custom range options.

"""

import pyqtgraph as pg
from pyqtgraph.graphicsItems.LabelItem import LabelItem
from pyqtgraph.graphicsItems.ButtonItem import ButtonItem
from pyqtgraph.graphicsItems.PlotItem.PlotItem import PlotItem
from pyqtgraph.graphicsItems.ViewBox import ViewBox
from PyQt5 import QtWidgets, QtCore, QtGui
import math
import numpy
import itertools
from modules.round import roundToNDigits
import logging
from pyqtgraphAddons.DateAxisItem import DateAxisItem
from datetime import datetime
from pyqtgraph.graphicsItems.AxisItem import AxisItem
from uiModules.KeyboardFilter import KeyListFilter
from functools import partial
from uiModules.FilterROI import FilterROI

grid_opacity = 0.3
import os
icons_dir = os.path.join(os.path.dirname(__file__), '..', 'ui/icons/')
range_icon_file = icons_dir + 'unity-range'
holdZero_icon_file = icons_dir + 'hold-zero'

class CustomViewBox(ViewBox):
    """
    Override of pyqtgraph ViewBox class. Modifies setRange method to allow for autoranging while keeping the minimum at zero.
    
    Adds a variable "holdZero" which indicates whether the ViewBox should hold the minimum y value at zero while autoranging.
    If this variable is True, the setRange method forces the minimum y value to be zero. If it is False, the setRange method
    is identical to that of pyqtgraph.ViewBox.
    """    
    def __init__(self, *args, **kwds):
        super(CustomViewBox, self).__init__(*args, **kwds)
        self.holdZero = False
    
    def updateAutoRange(self):
        ## Break recursive loops when auto-ranging.
        ## This is needed because some items change their size in response 
        ## to a view change.
        if self._updatingRange:
            return
        
        self._updatingRange = True
        try:
            targetRect = self.viewRange()
            if not any(self.state['autoRange']):
                return
                
            fractionVisible = self.state['autoRange'][:]
            for i in [0, 1]:
                if isinstance(fractionVisible[i], bool):
                    fractionVisible[i] = 1.0

            childRange = None
            
            order = [0, 1]
            if self.state['autoVisibleOnly'][0] is True:
                order = [1, 0]

            args = {}
            for ax in order:
                if self.state['autoRange'][ax] is False:
                    continue
                if self.state['autoVisibleOnly'][ax]:
                    oRange = [None, None]
                    oRange[ax] = targetRect[1-ax]
                    childRange = self.childrenBounds(frac=fractionVisible, orthoRange=oRange)
                    
                else:
                    if childRange is None:
                        childRange = self.childrenBounds(frac=fractionVisible)
                
                ## Make corrections to range
                xr = childRange[ax]
                if xr is not None:
                    if self.state['autoPan'][ax]:
                        x = sum(xr) * 0.5
                        w2 = (targetRect[ax][1]-targetRect[ax][0]) / 2.
                        childRange[ax] = [x-w2, x+w2]
                    else:
                        padding = self.suggestPadding(ax)
                        wp = (xr[1] - xr[0]) * padding
                        if self.holdZero and ax == 1:
                            childRange[ax][0] = 0-wp
                        else:
                            childRange[ax][0] -= wp
                        childRange[ax][1] += wp
                    targetRect[ax] = childRange[ax]
                    args['xRange' if ax == 0 else 'yRange'] = targetRect[ax]
            if len(args) == 0:
                return
            args['padding'] = 0
            args['disableAutoRange'] = False
            self.setRange(**args)
        finally:
            self._autoRangeNeedsUpdate = False
            self._updatingRange = False

class CustomPlotItem(PlotItem):
    """
    Plot using pyqtgraph.PlotItem, with extra buttons.

    The added buttons are:
        -A unity range button which sets the y axis range to 1.
        -A hold zero button which keeps the y minimum at zero while autoranging.
    resizeEvent is extended to set the position of the two new buttons correctly.
    """
    def __init__(self, parent=None, **kargs):
        """
        Create a new CustomPlotItem. In addition to the ordinary PlotItem, adds buttons and uses the custom ViewBox.
        """
        cvb = CustomViewBox()
        if kargs.get('dateAxis', False):
            self.dateAxisItem = DateAxisItem('bottom')
            kargs['axisItems'] = {'bottom': self.dateAxisItem}
        super(CustomPlotItem, self).__init__(parent, viewBox = cvb, **kargs)
        self.unityRangeBtn = ButtonItem(imageFile=range_icon_file, width=14, parentItem=self)
        self.unityRangeBtn.setToolTip("Set y range to (0,1)")
        self.unityRangeBtn.clicked.connect(self.onUnityRange)
        self.holdZeroBtn = ButtonItem(imageFile=holdZero_icon_file, width=14, parentItem=self)
        self.holdZeroBtn.setToolTip("Keep 0 as minimum y value while autoranging")
        self.holdZeroBtn.clicked.connect(self.onHoldZero)
        self.autoBtn.setToolTip("Autorange x and y axes")
        self.showGrid(x = True, y = True, alpha = grid_opacity) #grid defaults to on
        self.allButtonsHidden = False

    def hideAllButtons(self, hide):
        self.allButtonsHidden = hide
        if self.allButtonsHidden:
            self.holdZeroBtn.hide()
            self.unityRangeBtn.hide()
            self.autoBtn.hide()
        else:
            self.holdZeroBtn.show()
            self.unityRangeBtn.show()
            self.autoBtn.show()
        
    def resizeEvent(self, ev):
        """
        Set the button sizes appropriately.
        
        The code is borrowed from the same code applied to autoBtn in the parent method in PlotItem.py.
        """
        PlotItem.resizeEvent(self, ev)
        autoBtnRect = self.mapRectFromItem(self.autoBtn, self.autoBtn.boundingRect())
        unityRangeBtnRect = self.mapRectFromItem(self.unityRangeBtn, self.unityRangeBtn.boundingRect())
        holdZeroBtnRect= self.mapRectFromItem(self.holdZeroBtn, self.holdZeroBtn.boundingRect())
        yAuto = self.size().height() - autoBtnRect.height()
        yHoldZero = self.size().height() - holdZeroBtnRect.height()
        yUnityRange= self.size().height() - unityRangeBtnRect.height()
        self.autoBtn.setPos(-5, yAuto)
        self.unityRangeBtn.setPos(-5, yUnityRange-24) #The autoBtn height is 14, add 10 to leave a space
        self.holdZeroBtn.setPos(-5, yHoldZero-67) #Leave some space above the unity range button

    def onUnityRange(self):
        """Execute when unityRangeBtn is clicked. Set the yrange to 0 to 1."""
        self.vb.holdZero = False
        self.setYRange(0, 1)
        
    def onHoldZero(self):
        """Execute when holdZeroBtn is clicked. Autorange, but leave the y minimum at zero."""
        self.setYRange(0, 1) #This is a shortcut to turn off the autoranging, so that we can turn it back on with holdZero's value changed
        self.vb.holdZero = True
        super(CustomPlotItem, self).autoBtnClicked()
        self.autoBtn.show()

    def autoBtnClicked(self):
        """Execute when the the autoBtn is clicked. Set the holdZero variable to False."""
        self.setYRange(0, 1) #This is a shortcut to turn off the autoranging, so that we can turn it back on with holdZero's value changed
        self.vb.holdZero = False
        super(CustomPlotItem, self).autoBtnClicked()

    def updateButtons(self):
        """Overrides parent method updateButtons. Makes the autoscale button visible all the time.
        
        In the parent method, the auto button disappears when autoranging is enabled, or when the mouse moved off the plot window.
        I didn't like that feature, so this method disables it."""
        if hasattr(self, 'allButtonsHidden') and self.allButtonsHidden:
            self.autoBtn.hide()
        else:
            self.autoBtn.show()

class CoordinatePlotWidget(pg.GraphicsLayoutWidget):
    """This is the main widget for plotting data. It consists of a plot, a
       coordinate display, and custom buttons."""
    ROIBoundsSignal = QtCore.pyqtSignal(list, list, bool) #list of strings with trace creation dates
    #ROIBoundsCancel = QtCore.pyqtSignal() #list of strings with trace creation dates
    def __init__(self, parent=None, axisItems=None, name=None):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        super(CoordinatePlotWidget, self).__init__(parent)
        self.coordinateLabel = LabelItem(justify='right')
        self._graphicsView = self.addCustomPlot(row=0, col=0, colspan=2, axisItems=axisItems, name=name)
        self.addItem(self.coordinateLabel, row=1, col=1)
        self._graphicsView.scene().sigMouseMoved.connect(self.onMouseMoved)
        self.template = "<span style='font-size: 10pt'>x={0}, <span style='color: red'>y={1}</span></span>"
        self.mousePoint = None
        self.ROIEnabled = False
        self.filterType = True
        self.mousePointList = list()
        self._graphicsView.showGrid(x = True, y = True, alpha = grid_opacity) #grid defaults to on
        self.label_index = None

        # add option to set plot title to pyqtgraph's Plot Options context menu
        titleMenu = QtWidgets.QMenu(self._graphicsView.ctrlMenu)
        titleMenu.setTitle("Set Title")
        tlbl = QtWidgets.QLabel('Title:', self)
        thbox = QtWidgets.QHBoxLayout()
        titleMenuItem = QtGui.QWidgetAction(self._graphicsView.vb.menu.axes[0])
        titleWidget = QtWidgets.QLineEdit()
        titleWidget.textEdited.connect(self.onSetTitle)
        thbox.addWidget(tlbl)
        thbox.addWidget(titleWidget)
        twidgetContainer = QtWidgets.QWidget()
        twidgetContainer.setLayout(thbox)
        titleMenuItem.setDefaultWidget(twidgetContainer)
        titleMenu.addAction(titleMenuItem)
        self._graphicsView.ctrlMenu.titleMenuItem = titleMenuItem
        self._graphicsView.ctrlMenu.titleWidget = titleWidget
        self._graphicsView.ctrlMenu.addMenu(titleMenu)

        # modify pyqtgraph's X Axis context menu to allow for changes in xlabel
        xlbl = QtWidgets.QLabel('xLabel:', self)
        xhbox = QtWidgets.QHBoxLayout()
        xlabelMenuItem = QtGui.QWidgetAction(self._graphicsView.vb.menu.axes[0])
        xlabelWidget = QtWidgets.QLineEdit()
        xlabelWidget.textEdited.connect(self.onRelabelXAxis)
        xhbox.addWidget(xlbl)
        xhbox.addWidget(xlabelWidget)
        xwidgetContainer = QtWidgets.QWidget()
        xwidgetContainer.setLayout(xhbox)
        xlabelMenuItem.setDefaultWidget(xwidgetContainer)
        self._graphicsView.vb.menu.axes[0].addAction(xlabelMenuItem)
        self._graphicsView.vb.menu.axes[0].xlabelMenuItem = xlabelMenuItem
        self._graphicsView.vb.menu.axes[0].xlabelWidget = xlabelWidget

        # modify pyqtgraph's Y Axis context menu to allow for changes in ylabel
        ylbl = QtWidgets.QLabel('yLabel:', self)
        yhbox = QtWidgets.QHBoxLayout()
        ylabelMenuItem = QtGui.QWidgetAction(self._graphicsView.vb.menu.axes[0])
        ylabelWidget = QtWidgets.QLineEdit()
        ylabelWidget.textEdited.connect(self.onRelabelYAxis)
        yhbox.addWidget(ylbl)
        yhbox.addWidget(ylabelWidget)
        ywidgetContainer = QtWidgets.QWidget()
        ywidgetContainer.setLayout(yhbox)
        ylabelMenuItem.setDefaultWidget(ywidgetContainer)
        self._graphicsView.vb.menu.axes[1].addAction(ylabelMenuItem)
        self._graphicsView.vb.menu.axes[1].ylabelMenuItem = ylabelMenuItem
        self._graphicsView.vb.menu.axes[1].ylabelWidget = ylabelWidget

        action = QtWidgets.QAction("toggle time axis", self._graphicsView.ctrlMenu)
        action.triggered.connect( self.onToggleTimeAxis )
        self._graphicsView.ctrlMenu.addAction(action)
        self.timeAxis = False

        #filterAction = QtWidgets.QAction("Select Filter Region", self._graphicsView.ctrlMenu)
        #filterAction.triggered.connect( self.onFilterROI )
        #self._graphicsView.ctrlMenu.addAction(filterAction)

        self.acceptROI = KeyListFilter( [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return] )
        self.acceptROI.keyPressed.connect( self.getROICoords )
        self._graphicsView.installEventFilter(self.acceptROI)

        self.cancelROI = KeyListFilter( [QtCore.Qt.Key_Escape] )
        self.cancelROI.keyPressed.connect( self.removeROI )
        self._graphicsView.installEventFilter(self.cancelROI)

        self.toggleFilterType = KeyListFilter( [QtCore.Qt.Key_Space, QtCore.Qt.Key_T] )
        self.toggleFilterType.keyPressed.connect( partial(self.onChangeFilterType, None) )
        self._graphicsView.installEventFilter(self.toggleFilterType)

        self.setDisableFilterType = KeyListFilter( [QtCore.Qt.Key_D] )
        self.setDisableFilterType.keyPressed.connect( partial(self.onChangeFilterType, True) )
        self._graphicsView.installEventFilter(self.setDisableFilterType)

        self.setEnableFilterType = KeyListFilter( [QtCore.Qt.Key_E] )
        self.setEnableFilterType.keyPressed.connect( partial(self.onChangeFilterType, False) )
        self._graphicsView.installEventFilter(self.setEnableFilterType)

    @property
    def ROIColor(self):
        return "A00" if self.filterType else "0A0"

    def onChangeFilterType(self, ftype=None):
        if self.ROIEnabled:
            if ftype is None:
                self.filterType = not self.filterType
            else:
                self.filterType = ftype
            self.filtROI.setPen({'color': self.ROIColor, 'width': 2, 'style': QtCore.Qt.DashLine})

    def onFilterROI(self):
        if not self.ROIEnabled:
            self.ROIEnabled = True
            vR = self._graphicsView.vb.viewRange()
            meanY = (vR[1][1]+vR[1][0])/2
            meanX = (vR[0][1]+vR[0][0])/2
            deltaY = (vR[1][1]-vR[1][0])/4
            deltaX = (vR[0][1]-vR[0][0])/4
            lowerLeftCorner = [meanX-deltaX, meanY-deltaY]
            upperRightCorner = [2*deltaX, 2*deltaY]
            self.filtROI = FilterROI(self, lowerLeftCorner, upperRightCorner, removable=True)
            self.filtROI.handlePen = QtGui.QPen(QtGui.QColor(0,0,0))
            self.filtROI.handleSize = 5
            # next 3 lines are shorthand for constructing all scale handles on the ROI,
            # pos is the handle position, spos is the position about which the handle scales
            # if edge handles (as opposed to corner handles) need to be removed, get rid of .5 in the permutations call
            handleCoords = [(0,0), (1,1), *itertools.permutations([0, .5, 1], 2)]
            for pos, spos in map(lambda tp: [list(tp), list(map(lambda x: .5-1*(x-.5), tp))], handleCoords):
                self.filtROI.addScaleHandle(pos, spos).pen.setWidth(2)
            self.filtROI.setPen({'color': self.ROIColor, 'width': 2, 'style': QtCore.Qt.DashLine})
            self._graphicsView.addItem(self.filtROI)

    def getROICoords(self):
        if self.ROIEnabled:
            xbounds = [self.filtROI.pos()[0], self.filtROI.pos()[0] + self.filtROI.size()[0]]
            ybounds = [self.filtROI.pos()[1], self.filtROI.pos()[1] + self.filtROI.size()[1]]
            self._graphicsView.removeItem(self.filtROI)
            self.ROIBoundsSignal.emit(xbounds, ybounds, self.filterType)
            self.ROIEnabled = False
            self.filterType = True
            return self.filtROI.getSceneHandlePositions()

    def removeROI(self):
        if self.ROIEnabled:
            self.ROIBoundsSignal.emit([],[], False)
            self._graphicsView.removeItem(self.filtROI)
            self.ROIEnabled = False
            self.filterType = True

    def onToggleTimeAxis(self):
        self.setTimeAxis( not self.timeAxis )

    def onSetTitle(self, title):
        self._graphicsView.setTitle(title)

    def onRelabelXAxis(self, xlabel):
        self._graphicsView.setLabel('bottom', text = "{0}".format(xlabel))

    def onRelabelYAxis(self, ylabel):
        self._graphicsView.setLabel('left', text = "{0}".format(ylabel))

    def setTimeAxis(self, timeAxis=False):
        if timeAxis:
            dateAxisItem = DateAxisItem(orientation='bottom') 
            originalAxis = self._graphicsView.getAxis('bottom')
            dateAxisItem.linkToView(self._graphicsView.vb)
            self._graphicsView.axes['bottom']['item'] = dateAxisItem
            self._graphicsView.layout.removeItem(originalAxis)
            del originalAxis
            self._graphicsView.layout.addItem(dateAxisItem, 3, 1)
            self.timeAxis = True
            dateAxisItem.setZValue(-1000)
            dateAxisItem.setFlag(dateAxisItem.ItemNegativeZStacksBehindParent)
            dateAxisItem.linkedViewChanged(self._graphicsView.vb)
        else:
            axisItem = AxisItem(orientation='bottom') 
            originalAxis = self._graphicsView.getAxis('bottom')
            axisItem.linkToView(self._graphicsView.vb)
            self._graphicsView.axes['bottom']['item'] = axisItem
            self._graphicsView.layout.removeItem(originalAxis)
            del originalAxis
            self._graphicsView.layout.addItem(axisItem, 3, 1)
            self.timeAxis = False
            axisItem.setZValue(-1000)
            axisItem.setFlag(axisItem.ItemNegativeZStacksBehindParent)
            axisItem.linkedViewChanged(self._graphicsView.vb)
        
    def setPrintView(self, printview=True):
        self._graphicsView.hideAllButtons(printview)
        if printview:
            self.coordinateLabel.hide()
        else:
            self.coordinateLabel.show()
        
    def autoRange(self):
        """Set the display to autorange."""
        self._graphicsView.vb.enableAutoRange(axis=None, enable=True)
        
    def addCustomPlot(self, row=None, col=None, rowspan=1, colspan=1, **kargs):
        """This is a duplicate of addPlot from GraphicsLayout.py. The only change
        is CustomPlotItem instead of PlotItem."""
        plot = CustomPlotItem(**kargs)
        self.addItem(plot, row, col, rowspan, colspan)
        return plot
            
    def onMouseMoved(self, pos):
        """Execute when mouse is moved. If mouse is over plot, show cursor
           coordinates on coordinateLabel."""
        if self._graphicsView.sceneBoundingRect().contains(pos):
            if self.timeAxis:
                try:
                    self.mousePoint = self._graphicsView.vb.mapSceneToView(pos)
                    logY = self._graphicsView.ctrl.logYCheck.isChecked()
                    y = self.mousePoint.y() if not logY else pow(10, self.mousePoint.y())
                    vR = self._graphicsView.vb.viewRange()
                    deltaY = vR[1][1]-vR[1][0] if not logY else pow(10, vR[1][1])-pow(10, vR[1][0]) #Calculate x and y display ranges
                    precy = int( math.ceil( math.log10(abs(y/deltaY)) ) + 3 ) if y!=0 and deltaY>0 else 1
                    roundedy = roundToNDigits(y, precy )
                    try:
                        currentDateTime = datetime.fromtimestamp(self.mousePoint.x())
                        self.coordinateLabel.setText( self.template.format( str(currentDateTime), repr(roundedy) ))
                    except OSError:
                        pass  # datetime concersion at mouse point failed
                except ValueError:
                    pass
            else:
                try:
                    self.mousePoint = self._graphicsView.vb.mapSceneToView(pos)
                    logY = self._graphicsView.ctrl.logYCheck.isChecked()
                    logX = self._graphicsView.ctrl.logXCheck.isChecked()
                    y = self.mousePoint.y() if not logY else pow(10, self.mousePoint.y())
                    x = self.mousePoint.x() if not logX else pow(10, self.mousePoint.x())
                    if self.label_index is None:
                        vR = self._graphicsView.vb.viewRange()
                        deltaY = vR[1][1]-vR[1][0] if not logY else pow(10, vR[1][1])-pow(10, vR[1][0]) #Calculate x and y display ranges
                        deltaX = vR[0][1]-vR[0][0] if not logX else pow(10, vR[0][1])-pow(10, vR[0][0])
                        precx = int( math.ceil( math.log10(abs(x/deltaX)) ) + 3 ) if x!=0 and deltaX>0 else 1
                        precy = int( math.ceil( math.log10(abs(y/deltaY)) ) + 3 ) if y!=0 and deltaY>0 else 1
                        roundedx, roundedy = roundToNDigits( x, precx), roundToNDigits(y, precy )
                        self.coordinateLabel.setText( self.template.format( repr(roundedx), repr(roundedy) ))
                    else:
                        self.coordinateLabel.setText(self.label_index.get((round(x), round(y)), ''))
                except numpy.linalg.linalg.LinAlgError:
                    pass
                    
            
    def onCopyLocation(self, which):
        text = {'x': ("{0}".format(self.mousePoint.x())),
                'y': ("{0}".format(self.mousePoint.y())) }.get(which, "{0}, {1}".format(self.mousePoint.x(), self.mousePoint.y()))
        QtWidgets.QApplication.clipboard().setText(text)
        
#    def mouseDoubleClickEvent(self, ev):
#        pg.GraphicsLayoutWidget.mouseDoubleClickEvent(self,ev)
#        print "CoordinatePlotWidget mouseDoubleClicked"
#        #self.onMouseClicked(ev)
        
    def copyPointsToClipboard(self, modifiers):
        logger = logging.getLogger(__name__)
        logger.debug( "copyPointsToClipboard" )
        if modifiers & QtCore.Qt.ControlModifier:
            if modifiers & QtCore.Qt.ShiftModifier:
                QtWidgets.QApplication.clipboard().setText(" ".join(["{0}".format(p.x()) for p in self.mousePointList]))
            elif modifiers & QtCore.Qt.AltModifier:
                QtWidgets.QApplication.clipboard().setText(" ".join(["{0}".format(p.y()) for p in self.mousePointList]))
            else:
                QtWidgets.QApplication.clipboard().setText(" ".join(["{0} {1}".format(p.x(), p.y()) for p in self.mousePointList]))
        
    def keyReleaseEvent(self, ev):
        logger = logging.getLogger(__name__)
        logger.debug(  "Key released {0} {1}".format( ev.key(), ev.modifiers() ) )
        { 67: self.copyPointsToClipboard }.get(ev.key(), lambda x:None)(ev.modifiers())
        
    def mouseReleaseEvent(self, ev):
        pg.GraphicsLayoutWidget.mouseReleaseEvent(self, ev)
        if ev.modifiers()&QtCore.Qt.ShiftModifier:
            self.mousePointList.append(self.mousePoint)
        else:
            self.mousePointList = [self.mousePoint]

    def autoRangeEnabled(self):
        return self._graphicsView.vb.autoRangeEnabled()

    def enableAutoRange(self, axes=None, enable=True, x=None, y=None):
        self._graphicsView.vb.enableAutoRange(axes, enable, x, y)

    def autoRange(self, padding=None, items=None, item=None):
        self._graphicsView.vb.autoRange(padding, items, item)

if __name__ == '__main__':
    icons_dir = '../ui/icons/'
    range_icon_file = icons_dir + 'unity-range'
    holdZero_icon_file = icons_dir + 'hold-zero'
    import sys    
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOption('background', 'w') #set background to white
    pg.setConfigOption('foreground', 'k') #set foreground to black
    MainWindow = QtWidgets.QMainWindow()
    myPlotWidget = CoordinatePlotWidget()
    MainWindow.setCentralWidget(myPlotWidget)
    pi = myPlotWidget.getItem(0, 0)
    pi.plot(x = [3, 4, 5, 6], y = [9, 16, 25, 36])

    MainWindow.show()
    sys.exit(app.exec_())
    