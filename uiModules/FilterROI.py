# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtCore
from pyqtgraph import ROI
from pyqtgraph.functions import mkPen
from functools import partial

class ROIMixin:
    """This mixin class is to modify pyqtgraph's ROI function in
       order to customize the context menu and display behavior"""
    def getMenu(self):
        if self.menu is None:
            self.menu = QtGui.QMenu()
            self.menu.setTitle("ROI")
            cancelAction = QtGui.QAction("Cancel filter (Esc)", self.menu)
            cancelAction.triggered.connect(self.plotWidget.removeROI)
            self.menu.addAction(cancelAction)
            acceptAction = QtGui.QAction("Apply filter (Enter)", self.menu)
            acceptAction.triggered.connect(self.plotWidget.getROICoords)
            self.menu.addAction(acceptAction)
            toggleAction = QtGui.QAction("Toggle inclusivity (Space)", self.menu)
            toggleAction.triggered.connect(partial(self.plotWidget.onChangeFilterType, None))
            self.menu.addAction(toggleAction)
        return self.menu

    def setMouseHover(self, hover):
        ## Inform the ROI that the mouse is(not) hovering over it
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.pen.setStyle(QtCore.Qt.SolidLine)
            self.currentPen = self.pen
        else:
            self.pen.setStyle(QtCore.Qt.DashLine)
            self.currentPen = self.pen
        self.update()

class FilterROI(ROIMixin, ROI):

    def __init__(self, plotwidget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plotWidget = plotwidget
