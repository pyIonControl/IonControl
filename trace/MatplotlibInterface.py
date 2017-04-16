# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

class MatplotWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.styleNames = {k:v for k,v in enumerate(['lines', 'points', 'linespoints', 'lines_with_errorbars', 'points_with_errorbars', 'linepoints_with_errorbars'])}
        self.styleDict = {'lines': lambda trc: {'ls': '-' if trc.penList[trc.curvePen][0].style is QtCore.Qt.SolidLine else '--'},
                          'points': lambda trc: {'marker': trc.penList[trc.curvePen][1] if trc.penList[trc.curvePen][1] != 't' else 'v', 'fillstyle': 'none' if trc.penList[trc.curvePen][3] is None else 'full'},
                          'linespoints': lambda trc: {**self.styleDict['lines'](trc),**self.styleDict['points'](trc)},
                          'lines_with_errorbars': lambda trc: self.styleDict['lines'](trc),
                          'points_with_errorbars': lambda trc: self.styleDict['points'](trc),
                          'linepoints_with_errorbars': lambda trc: self.styleDict['linespoints'](trc)}

    def styleLookup(self, plottedtrace):
        return self.styleDict[self.styleNames.get(plottedtrace.style, 'lines')](plottedtrace)

    def translateColor(self, plottedtrace):
        return (i/255 for i in plottedtrace.penList[plottedtrace.curvePen][4])

    def plot(self, plottedtrace):
        style = self.styleLookup(plottedtrace)
        ax = self.fig.add_subplot(111)
        ax.plot(plottedtrace.x, plottedtrace.y, color=self.translateColor(plottedtrace), **style)
        self.canvas.draw()

