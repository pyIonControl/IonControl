# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from pulseProgram.PulseProgramSourceEdit import PulseProgramSourceEdit
from PyQt5.Qsci import QsciScintilla

class MatplotWindow(QtWidgets.QDialog):
    def __init__(self, parent=None, exitSig=None):
        super().__init__(parent)
        if exitSig is not None:
            exitSig.connect(self.close)
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.button = QtGui.QPushButton('Plot')
        self.button.clicked.connect(self.replot)
        #setup editor
        self.textEdit = PulseProgramSourceEdit()
        self.textEdit.setupUi(self.textEdit, extraKeywords1=[], extraKeywords2=[])#scriptFunctions)
        self.textEdit.textEdit.currentLineMarkerNum = 9
        self.textEdit.textEdit.markerDefine(QsciScintilla.Background, self.textEdit.textEdit.currentLineMarkerNum) #This is a marker that highlights the background
        self.textEdit.textEdit.setMarkerBackgroundColor(QtGui.QColor(0xd0, 0xff, 0xd0), self.textEdit.textEdit.currentLineMarkerNum)
        self.plottedTraces = []
        self.traceind = 0
        self.code = ""
        self.header = """# Previous definitions:\n# import matplotlib.pyplot as plt\n# fig = plt.figure()\n# canvas = FigureCanvas(fig)\n\nax = fig.add_subplot(111)\n"""
        self.footer = """\ncanvas.draw()"""

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.textEdit)
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.styleNames = {k:v for k,v in enumerate(['lines', 'points', 'linespoints', 'lines_with_errorbars', 'points_with_errorbars', 'linepoints_with_errorbars'])}
        self.styleDict = {'lines': lambda trc: {'ls': '-' if trc.penList[trc.curvePen][0].style() == QtCore.Qt.SolidLine else '--'},
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
        self.plottedTraces.append(plottedtrace)
        plottedTraces = self.plottedTraces
        style = {'ls': 'None', 'color': tuple(self.translateColor(plottedtrace))}
        style.update(self.styleLookup(plottedtrace))
        ax = self.fig.add_subplot(111)
        ax.plot(plottedtrace.x, plottedtrace.y, **style)
        self.canvas.draw()
        styleStr = ', '.join([k+'='+str(v if not isinstance(v,str) else "'{}'".format(v)) for k,v in style.items()])
        self.code += """ax.plot(plottedTraces[{0}].x, plottedTraces[{0}].y, {1})\n""".format(self.traceind, styleStr)
        self.textEdit.setPlainText(self.header+self.code+self.footer)
        self.traceind += 1

    def replot(self):
        plt.clf()
        plottedTraces = self.plottedTraces
        canvas = self.canvas
        fig = self.fig
        d = dict(locals(), **globals()) #Executing in this scope allows a function defined in the script to call another function defined in the script
        self.code = self.textEdit.textEdit.text()
        exec(self.code, d, d) #run the script
