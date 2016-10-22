# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import os.path

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from trace.BlockAutoRange import BlockAutoRangeList
from trace.TraceCollection import TraceCollection
from trace import pens

from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic

from ProjectConfig.Project import getProject
from .TraceModel import TraceComboDelegate
from .TraceModel import TraceModel
from uiModules.CategoryTree import nodeTypes
from trace.PlottedTrace import PlottedTrace
from .TraceDescriptionTableModel import TraceDescriptionTableModel
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from uiModules.KeyboardFilter import KeyListFilter
from functools import partial
from dateutil.tz import tzlocal
from modules.doProfile import doprofile
import subprocess
from pathlib import Path
import ctypes
from modules.InkscapeConversion import getPdfMetaData, getSvgMetaData
from functools import reduce

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/Traceui.ui')
TraceuiForm, TraceuiBase = PyQt5.uic.loadUiType(uipath)

traceFocus = None

class Settings(AttributeComparisonEquality):
    """
    Class to hold Traceui settings

    Attributes:
        lastDir (str): last directory from which traces were opened
        plotStyle (int): style to use for plotting new traces (i.e. lines, points, etc.)
        unplotLastTrace (bool): whether last trace should be unplotted when new trace is created
        collapseLastTrace (bool): whether last set of traces should be collapsed in tree when new trace set is created
        expandNew (bool): whether new trace sets should be expanded when they are created
    """
    def __init__(self, lastDir=None, plotstyle=0):
        if lastDir is None:
            self.lastDir = getProject().projectDir
        else:
            self.lastDir = lastDir
        self.plotstyle = plotstyle
        self.unplotLastTrace = True
        self.collapseLastTrace = False
        self.expandNew = True
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('unplotLastTrace', True)
        self.__dict__.setdefault('collapseLastTrace', False)
        self.__dict__.setdefault('expandNew', True)

class TraceuiMixin:
    """
    Class for the trace interface.
    Attributes:
        penicons (list[QtGui.QIcon]): icons to display available trace pens
        config (configshelve): configuration dictionary
        experimentName (str): name of experiment with which this Traceui is associated
        graphicsViewDict (dict): dict of available plot windows
    """
    openMeasurementLog = QtCore.pyqtSignal(list) #list of strings with trace creation dates
    def __init__(self, penicons, config, experimentName, graphicsViewDict, parent=None, lastDir=None, hasMeasurementLog=False, highlightUnsaved=False, preferences=None):
        self.penicons = penicons
        self.config = config
        self.configname = "Traceui."+experimentName
        self.settings = self.config.get(self.configname+".settings", Settings(lastDir=lastDir, plotstyle=0))
        self.graphicsViewDict = graphicsViewDict
        self.hasMeasurementLog = hasMeasurementLog
        self.highlightUnsaved = highlightUnsaved
        self.preferences = preferences #these are really print preferences used to find gnuplot path
        self.classIndicator = 'trace'

    def setupUi(self, MainWindow):
        """Setup the UI. Create the model and the view. Connect all the buttons."""
        self.model = TraceModel([], self.penicons, self.graphicsViewDict, highlightUnsaved=self.highlightUnsaved)
        self.traceView.setModel(self.model)
        self.delegate = TraceComboDelegate(self.penicons)
        self.graphicsViewDelegate = ComboBoxDelegate()
        self.traceView.setItemDelegateForColumn(self.model.column.pen, self.delegate) #This is for selecting which pen to use in the plot
        self.traceView.setItemDelegateForColumn(self.model.column.window, self.graphicsViewDelegate) #This is for selecting which plot to use
        self.traceView.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection) #allows selecting more than one element in the view

        self.clearButton.clicked.connect(partial(self.onClearOrPlot, 'clear'))
        self.plotButton.clicked.connect(partial(self.onClearOrPlot, 'plot'))
        self.pushButtonApplyStyle.clicked.connect(self.onApplyStyle)
        self.saveButton.clicked.connect(self.onSave)
        self.removeButton.clicked.connect(self.onDelete) #  (self.traceView.onDelete)
        self.openFileButton.clicked.connect(self.onOpenFile)
        self.comboBoxStyle.currentIndexChanged[int].connect(self.setPlotStyle)
        self.traceView.clicked.connect(self.onViewClicked)
        self.comboBoxStyle.setCurrentIndex(self.settings.plotstyle)

        self.saveButtonMenu = QtWidgets.QMenu(self.saveButton)
        self.saveButton.setMenu(self.saveButtonMenu)
        saveAsTextAction = QtWidgets.QAction("save as text", self.saveButtonMenu)
        saveAsTextAction.triggered.connect(partial(self.onSave, 'text'))
        saveAsHdf5Action = QtWidgets.QAction("save as hdf5", self.saveButtonMenu)
        saveAsHdf5Action.triggered.connect(partial(self.onSave, 'hdf5'))
        self.saveButtonMenu.addAction(saveAsTextAction)
        self.saveButtonMenu.addAction(saveAsHdf5Action)

        self.selectAllButton.clicked.connect(self.traceView.selectAll)
        self.collapseAllButton.clicked.connect(self.traceView.collapseAll)
        self.expandAllButton.clicked.connect(self.traceView.expandAll)
        self.traceView.selectionModel().selectionChanged.connect(self.onActiveTraceChanged)
        self.measurementLogButton.clicked.connect(self.onMeasurementLog)

        self.traceView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )

        self.measurementLogButton.setVisible(self.hasMeasurementLog)

        self.plotWithMatplotlib = QtWidgets.QAction("Plot with matplotlib", self)
        self.plotWithMatplotlib.triggered.connect(self.onPlotWithMatplotlib)

        self.plotWithGnuplot = QtWidgets.QAction("Plot with gnuplot", self)
        self.plotWithGnuplot.triggered.connect(self.onPlotWithGnuplot)
        self.openDirectory = QtWidgets.QAction("Open containing directory", self)
        self.openDirectory.triggered.connect(self.openContainingDirectory)

    @doprofile
    def onDelete(self, _):
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            self.traceView.onDelete()

    def onMeasurementLog(self):
        """Execute when open measurement log is clicked. Emit signal containing list of trace creation keys selected."""
        selectedTopNodes = self.traceView.selectedTopNodes()
        traceCreationList = []
        for topNode in selectedTopNodes:
            dataNode = self.model.getFirstDataNode(topNode)
            if dataNode:
                traceCreation = str(dataNode.content.traceCollection.traceCreation)
                traceCreationList.append(traceCreation)
        self.openMeasurementLog.emit(traceCreationList)

    def onClearOrPlot(self, changeType):
        """Execute when clear or plot action buttons are clicked."""
        leftCol=self.model.column.name
        rightCol=self.model.column.pen
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            for node in uniqueSelectedNodes:
                dataNodes = self.model.getDataNodes(node)
                for dataNode in dataNodes:
                    plottedTrace = dataNode.content
                    changed=False
                    if changeType=='clear' and plottedTrace.curvePen!=0:
                        plottedTrace.plot(0)
                        changed=True
                    elif changeType=='plot' and plottedTrace.curvePen==0:
                        plottedTrace.plot(-1, self.settings.plotstyle)
                        changed=True
                    if changed:
                        self.model.traceModelDataChanged.emit(str(plottedTrace.traceCollection.traceCreation), 'isPlotted', '')
                        leftInd = self.model.indexFromNode(dataNode, col=leftCol)
                        rightInd = self.model.indexFromNode(dataNode, col=rightCol)
                        self.model.dataChanged.emit(leftInd, rightInd)
                        self.model.emitParentDataChanged(dataNode, leftCol, rightCol)

    def onPlotWithGnuplot(self):
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        plotCommands = ""
        lc = 0  # custom cycle counter for plot color
        lt = 11  # custom cycle counter for line style
        colorList = ['#0072bd', '#e2141f', '#77ac30', '#d95319', '#4dbeee', '#7e2f8e', '#000000', '#edb120']
        clLen = len(colorList)
        linesonly = True
        for node in uniqueSelectedNodes:
            dataNodes = self.model.getDataNodes(node)
            for dataNode in dataNodes:
                plottedTrace = dataNode.content
                path = plottedTrace.traceCollection.filename.replace('\\', '/')
                xind = list(plottedTrace.traceCollection.keys()).index(plottedTrace._xColumn)
                yind = list(plottedTrace.traceCollection.keys()).index(plottedTrace._yColumn)
                plotstyle = plottedTrace.Styles.reverse_mapping[plottedTrace.style].split(' ')[0]
                if plotstyle != 'lines':
                    linesonly = False
                xAxisLabel = plottedTrace.xAxisLabel
                xAxisUnit = plottedTrace.xAxisUnit
                yAxisLabel = plottedTrace.yAxisLabel
                yAxisUnit = plottedTrace.yAxisUnit
                if plotCommands != "":
                    lt += 1
                    lc += 1
                    if not lt % 19:
                        lt = 11
                    plotCommands += ', '
                plotCommands += "'{0}' using {1}:{2} ls {3} lc rgb '{4}' w {5}".format(path, xind + 1, yind + 1, lt,
                                                                                       colorList[lc % clLen], plotstyle)
        gnupath = self.preferences.gnuplotExecutable
        if not os.path.exists(gnupath):
            raise Exception("Path to gnuplot executable {0} doesn't exist!".format(gnupath))
        else:
            with subprocess.Popen([gnupath, '-persist'],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE
                                  ) as proc:
                if xAxisLabel is not None:
                    xlabel = xAxisLabel
                    if xAxisUnit is not None and len(xAxisUnit):
                        xlabel += ' (' + xAxisUnit + ')'
                else:
                    xlabel = ''
                if yAxisLabel is not None:
                    ylabel = yAxisLabel
                    if yAxisUnit is not None and len(xAxisUnit):
                        ylabel += ' (' + yAxisUnit + ')'
                else:
                    ylabel = ''

                # some custom line types started at a higher index so
                # as not to conflict with lower index line styles if people prefer them
                # line styles exceed color list by 1 so point types and colors will go through every combination
                proc.stdin.write(b" set style line 11 lt 1 pt 5 lw 2 ps 1.25\n")  # blue
                proc.stdin.write(b" set style line 12 lt 1 pt 7 lw 2 ps 1.25\n")  # red
                proc.stdin.write(b" set style line 13 lt 1 pt 13 lw 2 ps 1.25\n")  # green
                proc.stdin.write(b" set style line 14 lt 1 pt 9 lw 2 ps 1.25\n")  # orange
                proc.stdin.write(b" set style line 15 lt 1 pt 11 lw 2 ps 1.25\n")  # light blue
                proc.stdin.write(b" set style line 16 lt 1 pt 4 lw 2 ps 1.25\n")  # purple
                proc.stdin.write(b" set style line 17 lt 1 pt 6 lw 2 ps 1.25\n")  # black
                proc.stdin.write(b" set style line 18 lt 1 pt 12 lw 2 ps 1.25\n")  # yellow
                proc.stdin.write(b" set style line 19 lt 1 pt 8 lw 2 ps 1.25\n")  # yellow

                # autoscale fix prevents gnuplot from autoscaling up to next tick, offset command gives a 2% offset
                # from edge of data along x axis, and a 4% offset along y axis
                if linesonly:
                    proc.stdin.write(
                        b"unset key; set autoscale fix; set offset graph 0.0, graph 0.0, graph 0.04, graph 0.04\n")
                else:
                    proc.stdin.write(
                        b"unset key; set autoscale fix; set offset graph 0.02, graph 0.02, graph 0.04, graph 0.04\n")
                proc.stdin.write(bytes("set xlabel '{0}'\nset ylabel '{1}'\n".format(xlabel, ylabel), 'ASCII'))
                proc.stdin.write(bytes("plot " + plotCommands + "\n", 'ASCII'))
                proc.stdin.flush()

    def onPlotWithMatplotlib(self):
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        for node in uniqueSelectedNodes:
            dataNodes = self.model.getDataNodes(node)
            for dataNode in dataNodes:
                plottedTrace = dataNode.content
 
    def onApplyStyle(self):
        """Execute when apply style button is clicked. Changed style of selected traces."""
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        for node in uniqueSelectedNodes:
            dataNodes = self.model.getDataNodes(node)
            for dataNode in dataNodes:
                trace = dataNode.content
                trace.plot(-2, self.settings.plotstyle)

    def onSave(self, fileType=None, saveCopy=False, returnTraceNodeNames=False):
        """Save button is clicked. Save selected traces. If a trace has never been saved before, update model."""
        leftCol = 0
        rightCol = self.model.numColumns-1
        selectedTopNodes = self.traceView.selectedTopNodes()
        filename = ''
        parentids = []
        for node in selectedTopNodes:
            dataNode=self.model.getFirstDataNode(node)
            if dataNode:
                traceCollection = dataNode.content.traceCollection
                alreadySaved = traceCollection.saved
                filename = traceCollection.save(fileType, saveCopy)
                parentids.append(dataNode.parent.id)
                if not alreadySaved:
                    self.model.onSaveUnsavedTrace(dataNode)
                    self.model.traceModelDataChanged.emit(str(traceCollection.traceCreation), 'filename', traceCollection.filename)
                    if dataNode is node:
                        topLeftInd = self.model.indexFromNode(dataNode, leftCol)
                        bottomRightInd = self.model.indexFromNode(dataNode, rightCol)
                    else:
                        topLeftInd = self.model.indexFromNode(dataNode.parent.children[0], leftCol)
                        bottomRightInd = self.model.indexFromNode(dataNode.parent.children[-1], rightCol)
                    self.model.dataChanged.emit(topLeftInd, bottomRightInd)
                    self.model.emitParentDataChanged(dataNode, leftCol, rightCol)
        if returnTraceNodeNames:
            return filename, parentids
        return filename

    def updateFocus(self):
        global traceFocus
        traceFocus = self.classIndicator

    def onActiveTraceChanged(self):
        """Display trace creation/finalized date/time when a trace is selected"""
        nodes=self.traceView.selectedNodes()
        dataNode=self.model.getFirstDataNode(nodes[0]) if nodes else None
        if dataNode:
            description = dataNode.content.traceCollection.description
            traceCreation = description.get("traceCreation")
            traceFinalized = description.get("traceFinalized")
            if traceCreation:
                traceCreationLocal = traceCreation.astimezone(tzlocal()) #use local time
                self.createdDateLabel.setText(traceCreationLocal.strftime('%Y-%m-%d'))
                self.createdTimeLabel.setText(traceCreationLocal.strftime('%H:%M:%S'))
            else:
                self.createdDateLabel.setText('')
                self.createdTimeLabel.setText('')
            if traceFinalized:
                traceFinalizedLocal = traceFinalized.astimezone(tzlocal()) #use local time
                self.finalizedDateLabel.setText(traceFinalizedLocal.strftime('%Y-%m-%d'))
                self.finalizedTimeLabel.setText(traceFinalizedLocal.strftime('%H:%M:%S'))
            else:
                self.finalizedDateLabel.setText('')
                self.finalizedTimeLabel.setText('')
        else:
                self.createdDateLabel.setText('')
                self.createdTimeLabel.setText('')
                self.finalizedDateLabel.setText('')
                self.finalizedTimeLabel.setText('')

    def onUnplotSetting(self, checked):
        self.settings.unplotLastTrace = checked

    def onCollapseLastTrace(self, checked):
        self.settings.collapseLastTrace = checked

    def onExpandNew(self, checked):
        self.settings.expandNew = checked

    @QtCore.pyqtProperty(bool)
    def unplotLastTrace(self):
        return self.settings.unplotLastTrace

    @QtCore.pyqtProperty(bool)
    def collapseLastTrace(self):
        return self.settings.collapseLastTrace

    @QtCore.pyqtProperty(bool)
    def expandNew(self):
        return self.settings.expandNew

    def collapse(self, trace):
        """collapse node associated with trace"""
        node = self.model.nodeFromContent(trace)
        if node:
            index = self.model.indexFromNode(node.parent)
            self.traceView.collapse(index)

    def expand(self, trace):
        """expand node associated with trace"""
        node = self.model.nodeFromContent(trace)
        if node:
            index = self.model.indexFromNode(node.parent)
            self.traceView.expand(index)

    def selectedRowIndexes(self, useLastIfNoSelection=True, allowUnplotted=True):
        """Return selected row indexes, modified according to the boolean controls"""
        inputIndexes = self.traceView.selectedRowIndexes()
        outputIndexes = []
        for index in inputIndexes:
            trace = self.model.contentFromIndex(index)
            if allowUnplotted or trace.isPlotted:
                outputIndexes.append(index)
        if not outputIndexes and useLastIfNoSelection:
            node = self.model.getLastDataNode(self.model.root)
            if node:
                index = self.model.indexFromNode(node)
                outputIndexes.append(index)
        return outputIndexes

    def selectedTraces(self, useLastIfNoSelection=False, allowUnplotted=True):
        """Return a list of the selected traces."""
        selectedIndexes = self.selectedRowIndexes(useLastIfNoSelection, allowUnplotted)
        return [self.model.contentFromIndex(index) for index in selectedIndexes]

    def addTrace(self, trace, pen, style=-1):
        """Add a trace to the model and plot it."""
        self.model.addTrace(trace)
        if style not in range(6):
            style = self.settings.plotstyle
        trace.plot(pen, style)
                
    def resizeColumnsToContents(self):
        for column in range(self.model.numColumns):
            self.traceView.resizeColumnToContents(column)

    def setPlotStyle(self, value):
        """Set the plot style to 'value'."""
        self.settings.plotstyle = value
        self.onApplyStyle()
        
    def onViewClicked(self, index):
        """If one of the editable columns is clicked, begin to edit it."""
        self.updateFocus()
        if self.model.isDataNode(index):
            if index.column() in [self.model.column.pen, self.model.column.window, self.model.column.comment]:
                self.traceView.edit(index)
        elif index.column()==self.model.column.comment:
            self.traceView.edit(index)

    def onOpenFile(self):
        """Execute when the open button is clicked. Open an existing trace file from disk."""
        fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open files', self.settings.lastDir)
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            for fname in fnames:
                if Path(fname).suffix == '.pdf':
                    pdfnames = getPdfMetaData(fname)
                    if pdfnames:
                        for pdfname in pdfnames:
                            self.openFile(pdfname)
                elif Path(fname).suffix == '.svg':
                    svgnames = getSvgMetaData(fname)
                    if svgnames:
                        for svgname in svgnames:
                            self.openFile(svgname)
                else:
                    self.openFile(fname)

    def openFile(self, filename, defaultpen=-1):
        filename = str(filename)
        traceCollection = TraceCollection()
        traceCollection.filename = filename
        traceCollection.filepath, traceCollection.fileleaf = os.path.split(filename)
        self.settings.lastDir = traceCollection.filepath
        traceCollection.name = traceCollection.fileleaf
        traceCollection.saved = True
        traceCollection.loadTrace(filename)
        if traceCollection.description["name"] != "":
            traceCollection.name = traceCollection.description["name"]
        for node in list(self.model.traceDict.values()):
            dataNode=self.model.getFirstDataNode(node)
            existingTraceCollection=dataNode.content.traceCollection
            if existingTraceCollection.fileleaf==traceCollection.fileleaf and str(existingTraceCollection.traceCreation)==str(traceCollection.traceCreation):
                return #If the filename and creation dates are the same, you're trying to open an existing trace.
        plottedTraceList = list()
        category = None if len(traceCollection.tracePlottingList)==1 else self.getUniqueCategory(filename)
        for plotting in traceCollection.tracePlottingList:
            windowName = plotting.windowName if plotting.windowName in self.graphicsViewDict else list(self.graphicsViewDict.keys())[0]
            name = plotting.name
            plottedTrace = PlottedTrace(traceCollection, self.graphicsViewDict[windowName]['view'], pens.penList, -1, tracePlotting=plotting, windowName=windowName, name=name)
            plottedTrace.category = category
            plottedTraceList.append(plottedTrace)
            self.addTrace(plottedTrace, defaultpen)
        if self.expandNew:
            self.expand(plottedTraceList[0])
        self.resizeColumnsToContents()
        return plottedTraceList

    def openContainingDirectory(self):
        """Opens the parent directory of a file, selecting the file if possible."""
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        dataNodes = self.model.getDataNodes(uniqueSelectedNodes[0])
        path = dataNodes[0].content.traceCollection.filename.replace('\\', '/')
        ctypes.windll.ole32.CoInitialize(None)
        upath = str(Path(path))
        pidl = ctypes.windll.shell32.ILCreateFromPathW(upath)
        ctypes.windll.shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
        ctypes.windll.shell32.ILFree(pidl)
        ctypes.windll.ole32.CoUninitialize()

    def saveConfig(self):
        """Execute when the UI is closed. Save the settings to the config file."""
        self.config[self.configname+".settings"] = self.settings
        
    def onShowOnlyLast(self):
        for node in self.model.root.children:
            index = self.model.indexFromNode(node)
            functionCall = self.model.categoryCheckboxChange if node.nodeType==nodeTypes.category else self.model.checkboxChange
            value=QtCore.Qt.Checked if node is self.model.root.children[-1] else QtCore.Qt.Unchecked
            if index.data(QtCore.Qt.CheckStateRole) != value:
                functionCall(index, value)

    def getUniqueCategory(self, filename):
        return self.model.getUniqueCategory(filename)

class Traceui(TraceuiMixin, TraceuiForm, TraceuiBase):
    def __init__(self, penicons, config, experimentName, graphicsViewDict, parent=None, lastDir=None, hasMeasurementLog=False, highlightUnsaved=False, preferences=None):
        TraceuiBase.__init__(self, parent)
        TraceuiForm.__init__(self)
        super().__init__(penicons, config, experimentName, graphicsViewDict, parent, lastDir, hasMeasurementLog, highlightUnsaved, preferences)

    def setupUi(self, MainWindow):
        TraceuiForm.setupUi(self, MainWindow)
        super().setupUi(MainWindow)
        self.showOnlyLastButton.clicked.connect(self.onShowOnlyLast)
        self.unplotSettingsAction = QtWidgets.QAction( "Unplot last trace set", self )
        self.unplotSettingsAction.setCheckable(True)
        self.unplotSettingsAction.setChecked( self.settings.unplotLastTrace)
        self.unplotSettingsAction.triggered.connect( self.onUnplotSetting )
        self.traceView.addAction( self.unplotSettingsAction )

        self.collapseLastTraceAction = QtWidgets.QAction( "Collapse last trace set", self )
        self.collapseLastTraceAction.setCheckable(True)
        self.collapseLastTraceAction.setChecked( self.settings.collapseLastTrace)
        self.collapseLastTraceAction.triggered.connect(self.onCollapseLastTrace)
        self.traceView.addAction( self.collapseLastTraceAction )

        self.expandNewAction = QtWidgets.QAction( "Expand new traces", self )
        self.expandNewAction.setCheckable(True)
        self.expandNewAction.setChecked( self.settings.expandNew)
        self.expandNewAction.triggered.connect(self.onExpandNew)
        self.traceView.addAction( self.expandNewAction )
        self.traceView.addAction(self.plotWithMatplotlib)
        self.traceView.addAction(self.plotWithGnuplot)
        self.traceView.addAction(self.openDirectory)
# if __name__ == '__main__':
#     import sys
#     import pyqtgraph as pg
#     from uiModules.CoordinatePlotWidget import CoordinatePlotWidget
#     import pens
#     pg.setConfigOption('background', 'w') #set background to white
#     pg.setConfigOption('foreground', 'k') #set foreground to black
#     app = QtWidgets.QApplication(sys.argv)
#     penicons = pens.penicons().penicons()
#     window = QtWidgets.QWidget()
#     layout = QtWidgets.QVBoxLayout()
#     window.setLayout(layout)
#     addPlotButton = QtWidgets.QPushButton()
#     layout.addWidget(addPlotButton)
#     ui = Traceui(penicons, {}, '', {}, lastDir = ' ')
#     ui.setupUi(ui)
#     layout.addWidget(ui)
#     plot = CoordinatePlotWidget(ui)
#     layout.addWidget(plot)
#     traceCollection = TraceCollection.TraceCollection()
#     plottedTrace = PlottedTrace(traceCollection, plot, pens.penList)
#     addPlotButton.clicked.connect(ui.addTrace(plottedTrace, pens.penList[0]))
#     window.show()
#     sys.exit(app.exec_())