# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtCore, QtWidgets
from modules.AttributeComparisonEquality import AttributeComparisonEquality
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from pulseProgram.PulseProgramSourceEdit import PulseProgramSourceEdit
from PyQt5.Qsci import QsciScintilla
from modules.DataDirectory import DataDirectory
from pathlib import Path
from collections import OrderedDict

class Settings(AttributeComparisonEquality):
    def __init__(self, plotName=None, fileTypes=None, saveCode=True):
        self.plotName = plotName or "Matplot"
        self.fileTypes = fileTypes or []
        self.saveCode = saveCode

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('plotName', "Matplot")
        self.__dict__.setdefault('fileTypes', [])
        self.__dict__.setdefault('saveCode', True)

class MatplotWindow(QtWidgets.QDialog):
    def __init__(self, parent=None, config=None, exitSig=None):
        super().__init__(parent)
        if exitSig is not None:
            exitSig.connect(self.close)
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.plotbutton = QtGui.QPushButton('Replot')
        self.plotbutton.setToolTip('Regenerate the plot from the console code.')
        self.savebutton = QtGui.QPushButton('Save')
        self.plotbutton.clicked.connect(self.replot)
        self.savebutton.clicked.connect(self.savePlot)

        self.config = config
        self.configname = "MatplotLib"
        self.settings = self.config.get(self.configname+".settings", Settings())

        self.filenamePattern = self.settings.plotName
        self.filename = None
        self.filepath = None

        self.textEdit = PulseProgramSourceEdit()
        self.textEdit.setupUi(self.textEdit, extraKeywords1=[], extraKeywords2=[])
        self.textEdit.textEdit.currentLineMarkerNum = 9
        self.textEdit.textEdit.markerDefine(QsciScintilla.Background, self.textEdit.textEdit.currentLineMarkerNum)
        self.textEdit.textEdit.setMarkerBackgroundColor(QtGui.QColor(0xd0, 0xff, 0xd0), self.textEdit.textEdit.currentLineMarkerNum)
        self.plottedTraces = []
        self.traceind = 0
        self.code = ""
        self.header = """# Previous definitions:\n# import matplotlib.pyplot as plt\n# fig = plt.figure()\n# canvas = FigureCanvas(fig)\n\nplt.clf()\nax = fig.add_subplot(111)\n"""
        self.footer = """\nplt.tight_layout()\ncanvas.draw()"""

        self.savebutton.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.savebutton.setToolTip('<b>Right click for more options</b>\n\n<i>Saving plots with this button provides\nbetter quality figures, as they are saved\nnatively with matplotlib instead of\nthrough the Qt backend.<\i>')
        self.saveCode = QtWidgets.QAction("Save code", self)
        self.saveCode.setCheckable(True)
        self.saveCode.setChecked(self.settings.saveCode)
        self.savebutton.addAction(self.saveCode)

        self.allowedFileTypes = plt.gcf().canvas.get_supported_filetypes()
        self.fCheckWidgets = OrderedDict(sorted({key:QtWidgets.QCheckBox('{}'.format(key)) for key in self.allowedFileTypes.keys()}.items(), key=lambda t: t[0]))
        svbox = QtWidgets.QVBoxLayout()
        saveOptions = QtGui.QWidgetAction(self.savebutton)
        for filetype, widget in self.fCheckWidgets.items():
            if filetype in self.settings.fileTypes:
                widget.setChecked(True)
            svbox.addWidget(widget)

        flbl = QtWidgets.QLabel('File name:', self)
        fhbox = QtWidgets.QHBoxLayout()
        flabelWidget = QtWidgets.QLineEdit(self.filenamePattern)
        flabelWidget.textEdited.connect(self.onChangeFileName)
        storeDefaults = QtWidgets.QPushButton("Make current settings default")
        storeDefaults.clicked.connect(self.saveSettings)
        fhbox.addWidget(flbl)
        fhbox.addWidget(flabelWidget)
        svbox.addLayout(fhbox)
        svbox.addWidget(storeDefaults)
        swidgetContainer = QtWidgets.QWidget()
        swidgetContainer.setLayout(svbox)
        saveOptions.setDefaultWidget(swidgetContainer)
        self.savebutton.addAction(saveOptions)

        vsplitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        vsplitter.addWidget(self.canvas)
        vsplitter.addWidget(self.textEdit)
        layout.addWidget(vsplitter)
        layout2 = QtGui.QHBoxLayout()
        layout2.addWidget(self.plotbutton)
        layout2.addWidget(self.savebutton)
        layout.addLayout(layout2)
        self.setLayout(layout)

        self.styleNames = {k:v for k,v in enumerate(['lines', 'points', 'linespoints', 'lines_with_errorbars', 'points_with_errorbars', 'linepoints_with_errorbars'])}
        self.styleDict = {'lines': lambda trc: {'ls': '-' if trc.penList[trc.curvePen][0].style() == QtCore.Qt.SolidLine else '--'},
                          'points': lambda trc: {'marker': trc.penList[trc.curvePen][1] if trc.penList[trc.curvePen][1] != 't' else 'v', 'fillstyle': 'none' if trc.penList[trc.curvePen][3] is None else 'full'},
                          'linespoints': lambda trc: {**self.styleDict['lines'](trc),**self.styleDict['points'](trc)},
                          'lines_with_errorbars': lambda trc: self.styleDict['lines'](trc),
                          'points_with_errorbars': lambda trc: self.styleDict['points'](trc),
                          'linepoints_with_errorbars': lambda trc: self.styleDict['linespoints'](trc)}

    def onChangeFileName(self, name):
        self.filenamePattern = name

    def styleLookup(self, plottedtrace, style=None):
        return self.styleDict[self.styleNames.get(style if style is not None else plottedtrace.style, 'lines')](plottedtrace)

    def translateColor(self, plottedtrace):
        return (i/255 for i in plottedtrace.penList[plottedtrace.curvePen][4])

    def plot(self, plottedtrace):
        self.plottedTraces.append(plottedtrace)
        if self.traceind == 0:
            xlab = "{0}".format(plottedtrace.xAxisLabel) if plottedtrace.xAxisLabel else ""
            xunit = " ({0})".format(plottedtrace.xAxisUnit) if plottedtrace.xAxisUnit else ""
            ylab = "{0}".format(plottedtrace.yAxisLabel) if hasattr(plottedtrace, 'yAxisLabel') and plottedtrace.yAxisLabel else ""
            yunit = " ({0})".format(plottedtrace.yAxisUnit) if hasattr(plottedtrace, 'yAxisUnit') and plottedtrace.yAxisUnit else ""
            plt.xlabel(xlab+xunit)
            plt.ylabel(ylab+yunit)
            self.code += "plt.xlabel('{0}')\nplt.ylabel('{1}')\n".format(xlab+xunit,ylab+yunit)
        if plottedtrace.fitFunction:
            style = {'ls': 'None', 'color': tuple(self.translateColor(plottedtrace))}
            style.update(self.styleLookup(plottedtrace, 'lines'))
            ax = self.fig.add_subplot(111)
            ax.plot(plottedtrace.fitx, plottedtrace.fity, **style)
            plt.tight_layout()
            self.canvas.draw()
            styleStr = ', '.join([k+'='+str(v if not isinstance(v,str) else "'{}'".format(v)) for k,v in style.items()])
            self.code += """ax.plot(plottedTraces[{0}].fitx, plottedTraces[{0}].fity, {1})\n""".format(self.traceind, styleStr)
        style = {'ls': 'None', 'color': tuple(self.translateColor(plottedtrace))}
        style.update(self.styleLookup(plottedtrace))
        ax = self.fig.add_subplot(111)
        styleStr = ', '.join([k+'='+str(v if not isinstance(v,str) else "'{}'".format(v)) for k,v in style.items()])
        if 'errorbar' in self.styleNames.get(plottedtrace.style,'lines') and plottedtrace.hasHeightColumn:
            self.code += """ax.errorbar(plottedTraces[{0}].x, plottedTraces[{0}].y, plottedTraces[{0}].height, {1})\n""".format(self.traceind, styleStr)
            ax.errorbar(plottedtrace.x, plottedtrace.y, plottedtrace.height, **style)
            plt.tight_layout()
            self.canvas.draw()
        else:
            self.code += """ax.plot(plottedTraces[{0}].x, plottedTraces[{0}].y, {1})\n""".format(self.traceind, styleStr)
            ax.plot(plottedtrace.x, plottedtrace.y, **style)
            plt.tight_layout()
            self.canvas.draw()
        self.textEdit.setPlainText(self.header+self.code+self.footer)
        self.traceind += 1

    def replot(self):
        plottedTraces = self.plottedTraces
        canvas = self.canvas
        fig = self.fig
        d = dict(locals(), **globals()) # allow definitions in scope to be accessed by console
        self.code = self.textEdit.textEdit.text()
        exec(self.code, d, d)

    def savePlot(self):
        filenames = [str(Path(pt.trace.filename)) for pt in self.plottedTraces]
        header = '"""\n'+'\n'.join(filenames)+'\n"""\n'
        savedCode = header+self.textEdit.textEdit.text()
        self.filename, (self.filepath, name, ext) = DataDirectory().sequencefile(self.filenamePattern)
        file = Path(self.filepath+'/'+name).with_suffix('.py')
        if self.saveCode.isChecked():
            file.write_text(savedCode)
        for filetype, cwidget in self.fCheckWidgets.items():
            if cwidget.isChecked():
                self.fig.savefig(str(file.with_suffix('.'+filetype)))

    def saveSettings(self):
        """set current saving options as default, ie plot formats and file name"""
        self.settings.plotName = self.filenamePattern
        ftlist = []
        for filetype, cwidget in self.fCheckWidgets.items():
            if cwidget.isChecked():
                ftlist.append(filetype)
        self.settings.fileTypes = ftlist
        self.settings.saveCode = self.saveCode.isChecked()
        self.config[self.configname+".settings"] = self.settings

