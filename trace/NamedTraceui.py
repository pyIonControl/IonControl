# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os.path
import PyQt5.uic

from modules.InkscapeConversion import getSvgMetaData, getPdfMetaData
from trace import Traceui
from trace import pens
from gui import TraceTableEditor
from PyQt5 import QtGui, QtCore, QtWidgets
from trace.BlockAutoRange import BlockAutoRangeList
import expressionFunctions.ExprFuncDecorator as trc
from trace.PlottedTrace import PlottedTrace
from trace.TraceCollection import TraceCollection
import numpy
import copy
from modules.Utility import unique
from datetime import datetime
import pytz
from pathlib import Path

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/NamedTraceui.ui')
TraceuiForm, TraceuiBase = PyQt5.uic.loadUiType(uipath)

class NewTraceTableModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.childList = [['', 0]]
        self.dataLookup = {(QtCore.Qt.DisplayRole): lambda index: self.childList[index.row()][index.column()] if index.column() == 0 else int(self.childList[index.row()][index.column()]),
                           (QtCore.Qt.EditRole): lambda index: self.childList[index.row()][index.column()] if index.column() == 0 else int(self.childList[index.row()][index.column()]) }
        self.headerDataLookup = ['Child Name', 'Length']

    def init(self):
        self.layoutChanged.emit()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def rowCount(self, *args):
        return len(self.childList)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def insertRow(self, position=0, index=QtCore.QModelIndex()):
        self.childList.append(["",0])
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        exprlen = len(self.childList)
        return range(exprlen-1, exprlen)

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        if len(self.childList):
            del(self.childList[position:(position + rows)])
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        return range(position, position+rows)

    def data(self, index, role):
        if index.isValid():
            return self.dataLookup.get(role, lambda index: None)(index)

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            self.childList[index.row()][index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)

    def updateData(self, index=QtCore.QModelIndex):
        index = self.createIndex(0, 1)
        self.dataChanged.emit(index, index)

    def valueChanged(self, ind):
        index = self.createIndex(ind, 1)
        self.dataChanged.emit(index, index)

    def flags(self, index):
        if index.column() == 0:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        if index.column() == 1:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal):
                return self.headerDataLookup[section]
        return None

    def copy_rows(self, rows, position):
        """creates a copy of elements in table specified by indices in the rows variable and inserts at position+1"""
        for i in reversed(rows):
            self.childList.insert(position + 1, copy.deepcopy(self.childList[i]))
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        return True

    def moveRow(self, rows, delta):
        """manually resort rows (for use with pgup/pgdn). rows specifies selected rows, delta specifies up/down movement"""
        if len(rows)>0 and (rows[0]>0 or delta>0) and (len(self.childList) > max(rows)+1 or delta < 0):
            for row in rows:
                self.childList[row], self.childList[row + delta] = self.childList[row + delta], self.childList[row]
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            return True
        return False

class Settings(Traceui.Settings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.filelist = []
        self.createTraceParentName = ''
        self.createTraceChildList = [['', 0]]
        self.defaultPlotIndex = 0
        self.defaultPlotName = ""
        self.splitterVerticalState = None

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('unplotLastTrace', True)
        self.__dict__.setdefault('collapseLastTrace', False)
        self.__dict__.setdefault('expandNew', True)
        self.__dict__.setdefault('filelist', [])
        self.__dict__.setdefault('createTraceParentName', '')
        self.__dict__.setdefault('createTraceChildList', [['', 0]])
        self.__dict__.setdefault('defaultPlotIndex', 0)
        self.__dict__.setdefault('defaultPlotName', '')
        self.__dict__.setdefault('splitterVerticalState', 0)

class NamedTraceui(Traceui.TraceuiMixin, TraceuiForm, TraceuiBase):
    externalUpdate = QtCore.pyqtSignal()
    def __init__(self, penicons, config, experimentName, graphicsViewDict, parent=None, lastDir=None, hasMeasurementLog=False, highlightUnsaved=False, preferences=None, plotsChangedSignal=None):
        TraceuiBase.__init__(self, parent)
        TraceuiForm.__init__(self)
        super().__init__(penicons, config, experimentName, graphicsViewDict, parent, lastDir, hasMeasurementLog, highlightUnsaved, preferences=preferences)
        self.penicons = penicons
        self.config = config
        self.configname = "NamedTraceui."+experimentName
        self.settings = self.config.get(self.configname+".settings", Settings(lastDir=lastDir, plotstyle=0))
        self.graphicsViewDict = graphicsViewDict
        self.hasMeasurementLog = hasMeasurementLog
        self.highlightUnsaved = highlightUnsaved
        self.newDataAvailable = False
        self.plotsChangedSignal = plotsChangedSignal
        self.classIndicator = 'namedtrace'
        self.tableEditor = None

    def setupUi(self, *args):
        TraceuiForm.setupUi(self, *args)
        super().setupUi(*args)
        self.model.flagsLookup[self.model.column.name] = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
        self.model.categoryFlagsLookup[self.model.column.name] = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
        self.model.dataLookup.update({
            (QtCore.Qt.DisplayRole, self.model.column.name): lambda node: node.content.name,
            (QtCore.Qt.EditRole, self.model.column.name): lambda node: node.content.name
            })
        self.model.setDataLookup.update({(QtCore.Qt.EditRole, self.model.column.name): self.renameTraceField})
        self.model.categoryDataLookup.update({
            (QtCore.Qt.DisplayRole, self.model.column.name): lambda node: node.id,
            (QtCore.Qt.EditRole, self.model.column.name): lambda node: node.id
        })
        self.model.categorySetDataLookup.update({(QtCore.Qt.EditRole, self.model.column.name): self.renameTraceField})

        self.createTraceOptions.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )

        self.setDefaultTraceOptionsAction = QtWidgets.QAction("Make current settings default", self)
        self.setDefaultTraceOptionsAction.triggered.connect(self.updateTraceCreationDefaults)
        self.createTraceOptions.addAction(self.setDefaultTraceOptionsAction)

        self.childTableModel = NewTraceTableModel()
        self.childTableView.setModel(self.childTableModel)
        self.addChild.clicked.connect(self.onAddRow)
        self.removeChild.clicked.connect(self.onRemoveRow)

        self.editData = QtWidgets.QAction("Edit Data", self)
        self.editData.triggered.connect(self.onEditData)
        self.traceView.addAction(self.editData)

        self.removeButton.clicked.disconnect()
        self.removeButton.clicked.connect(self.onNamedDelete)
        self.confirmCreateTrace.clicked.connect(self.createRawData)
        self.cancelCreateTrace.clicked.connect(self.resetTraceOptions)

        self.plotsChangedSignal.connect(self.initComboBox)
        self.comboBox.setInsertPolicy(3)
        self.initComboBox()

        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self, self.copy_to_clipboard, context=QtCore.Qt.WidgetWithChildrenShortcut)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Paste), self, self.paste_from_clipboard, context=QtCore.Qt.WidgetWithChildrenShortcut)

        self.saveTrace = QtWidgets.QAction("Save New Copy", self)
        self.saveTrace.triggered.connect(self.forceSave)
        self.traceView.addAction(self.saveTrace)
        self.traceView.addAction(self.plotWithMatplotlib)
        self.traceView.addAction(self.plotWithGnuplot)
        self.traceView.addAction(self.openDirectory)

        self.resetTraceOptions()
        try:
            for filename in sorted(self.settings.filelist, key=lambda x: Path(x).stem):
                self.openFile(filename, defaultpen=0)
            self.updateNames()
        except NameError:
            self.settings.filelist = []
        self.traceView.collapseAll()

    def initComboBox(self):
        """Clear and repopulate comboBox for default plots. Necessary when plot names are updated"""
        for i in reversed(range(self.comboBox.count())):
            self.comboBox.removeItem(i)
        for plotname in sorted(self.graphicsViewDict):
            self.comboBox.addItem(plotname)
        self.resetTraceOptions()

    def updateTraceCreationDefaults(self):
        """Save current settings in named trace generator as default"""
        self.settings.createTraceParentName = self.parentNameField.text()
        self.settings.createTraceChildList = copy.deepcopy(self.childTableModel.childList)
        self.settings.defaultPlotIndex = self.comboBox.currentIndex()
        self.settings.defaultPlotName = self.comboBox.currentText()
        self.settings.splitterVerticalState = self.splitter.saveState()

    def copy_to_clipboard(self):
        """ Copy the list of selected rows to the clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        rows = sorted(unique([i.row() for i in self.childTableView.selectedIndexes()]))
        clip.setText(str(rows))

    def paste_from_clipboard(self):
        """ Append the string of rows from the clipboard to the end of the TODO list. """
        clip = QtWidgets.QApplication.clipboard()
        row_string = str(clip.text())
        try:
            row_list = list(map(int, row_string.strip('[]').split(',')))
        except ValueError:
            raise ValueError("Invalid data on clipboard. Cannot paste into eval list")
        zeroColSelInd = self.childTableView.selectedIndexes()
        initRow = zeroColSelInd[-1].row()
        self.childTableModel.copy_rows(row_list, initRow)

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
                            self.settings.filelist += [pdfname]
                elif Path(fname).suffix == '.svg':
                    svgnames = getSvgMetaData(fname)
                    if svgnames:
                        for svgname in svgnames:
                            self.openFile(svgname)
                            self.settings.filelist += [svgname]
                else:
                    self.openFile(fname)
                    self.settings.filelist += [fname]
        self.settings.filelist = list(set(self.settings.filelist))
        self.updateNames()

    def updateNames(self):
        """updates names of loaded named traces in nodeDict and NamedTraceDict"""
        for node in self.model.root.children:
            if node.parent is not None and node.nodeType == 0:
                nodename = node.children[0].content.traceCollection.description['name']
                if nodename != '':
                    node.content = nodename
                    node.id = nodename
                    for child in node.children:
                        child.content.traceCollection.description['name'] = nodename
                        child.content.traceCollection._filenamePattern = nodename
                        child.id = nodename + '_' + child.content.name
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}
        self.model.nodeDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def onEditData(self):
        """open up the trace table editor"""
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        self.tableEditor = TraceTableEditor.TraceTableEditor()
        self.tableEditor.setupUi(uniqueSelectedNodes, self.model)
        self.tableEditor.finishedEditing.connect(self.saveAndUpdateFileList)
        self.tableEditor.tablemodel.dataChanged.connect(self.newData)
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def renameTraceField(self, index, newname):
        """updates trace information when a named trace field is renamed"""
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        for node in uniqueSelectedNodes:
            if node.nodeType == 0:
                if newname != node.content:
                    self.newDataAvailable = True
                node.content = newname
                node.id = newname
                for child in node.children:
                    child.content.traceCollection.description['name'] = newname
                    child.content.traceCollection._filenamePattern = newname
                    child.id = newname + '_' + child.content.name
            elif node.nodeType == 1:
                if newname != node.content.name:
                    self.newDataAvailable = True
                node.content.name = newname
                node.content.tracePlotting.name = newname
                node.id = node.parent.id + '_' + newname
            break
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}
        self.model.nodeDict = {v.id: v for k,v in self.model.nodeDict.items()}
        self.saveAndUpdateFileList()
        return True

    def forceSave(self):
        """saves a new copy of a named trace, even when the named trace hasn't changed"""
        self.newData()
        self.saveAndUpdateFileList()

    def saveAndUpdateFileList(self, keys=set()):
        """when data in a named trace is changed, save a new copy of the trace and
           change the default file list to maintain settings after software is reloaded"""
        if self.newDataAvailable:
            if keys == set():
                _, updatedNodes = self.onSave(saveCopy=True, returnTraceNodeNames=True)
                for node in updatedNodes:
                    trc.NamedTraceUpdate.dataChanged.emit('_NT_'+node)
            else:
                for k in keys:
                    tc = self.model.nodeDict[k].children[0].content.traceCollection
                    tc.save(tc._fileType, saveCopy=True)
                    trc.NamedTraceUpdate.dataChanged.emit('_NT_'+k.split('_'))
            self.settings.filelist = []
            for k,v in self.model.nodeDict.items():
                if v.parent is not None and v.nodeType == 0:
                    self.settings.filelist.append(self.model.nodeDict[k].children[0].content.traceCollection.filename)
        self.newDataAvailable = False

    def updateExternally(self, topNode, child, row, data, col, saveEvery=False):
        """overwrites specific elements of a preexisting named trace.
           Used in scripting when pushing results to a named trace"""
        self.newDataAvailable = True
        if col == 'x':
            self.model.nodeDict[topNode+'_'+child].content.trace[self.model.nodeDict[topNode+'_'+child].content._xColumn][row] = data
            self.model.nodeDict[topNode+'_'+child].content.replot()
        elif col == 'y':
            self.model.nodeDict[topNode+'_'+child].content.trace[self.model.nodeDict[topNode+'_'+child].content._yColumn][row] = data
            self.model.nodeDict[topNode+'_'+child].content.replot()
        else:
            if col in self.model.nodeDict[topNode+'_'+child].content.trace:
                self.model.nodeDict[topNode+'_'+child].content.trace[col][row] = data
        if saveEvery:
            self.saveAndUpdateFileList()

    def onAddRow(self):
        """add a row in expression tests"""
        self.childTableModel.insertRow()

    def onRemoveRow(self):
        """remove row(s) in expression tests"""
        zeroColSelInd = self.childTableView.selectedIndexes()
        if len(zeroColSelInd):
            initRow = zeroColSelInd[0].row()
            finRow = zeroColSelInd[-1].row()-initRow+1
            self.childTableModel.removeRows(initRow, finRow)
        else:
            self.childTableModel.removeRows(len(self.childTableModel.childList) - 1)

    def newData(self):
        self.newDataAvailable = True

    def onNamedDelete(self, a):
        """Same as removing trace from the traceView, but also updates the NamedTraceDict
           and default file list used for reloading named traces"""
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            for node in uniqueSelectedNodes:
                if node.nodeType == 0:
                    filename = node.children[0].content.traceCollection.filename
                    if filename in self.settings.filelist:
                        self.settings.filelist.remove(filename)
            self.traceView.onDelete()
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def resetTraceOptions(self):
        """When an empty named trace is generated, hide the generator gui and reinitialize
           to to the default parameters"""
        if self.settings.splitterVerticalState:
            self.splitter.restoreState(self.settings.splitterVerticalState)
        comboIndex = 0
        if self.settings.defaultPlotName in self.graphicsViewDict:
            comboIndex = self.comboBox.findText(self.settings.defaultPlotName)
        elif self.settings.defaultPlotIndex < len(self.graphicsViewDict):
            comboIndex = self.settings.defaultPlotIndex
        self.comboBox.setCurrentIndex(comboIndex)
        self.createNamedTrace.setChecked(False)
        self.createTraceOptions.setVisible(False)
        self.parentNameField.setText(self.settings.createTraceParentName)
        self.childTableModel.childList = copy.deepcopy(self.settings.createTraceChildList)
        self.childTableModel.init()

    def getUniqueName(self, name):
        """Gets a unique name for named traces. This was added to avoid name conflicts when
           multiple empty named traces are generated from a set of user-defined defaults"""
        basenewname = name
        newname = copy.copy(name)
        cati = 2
        while newname in trc.NamedTraceDict.keys():
            newname = basenewname+str(cati)
            cati +=1
        return newname

    def getUniqueChildName(self, index):
        """Gets a unique name for child traces."""
        basenewname = self.childTableModel.childList[index][0]
        newname = copy.copy(basenewname)
        cati = 2
        if index == 0:
            return newname
        partialChildList = [self.childTableModel.childList[cii][0] for cii in range(index)]
        while newname in partialChildList:
            newname = basenewname+str(cati)
            cati +=1
        return newname

    def createRawData(self):
        """Creates an empty named trace based on parameters in the NamedTrace generator GUI"""
        traceCollection = TraceCollection(record_timestamps=False)
        self.plottedTraceList = list()
        for index in range(len(self.childTableModel.childList)):
            yColumnName = self.getUniqueChildName(index)
            rawColumnName = '{0}_raw'.format(yColumnName)
            plottedTrace = PlottedTrace(traceCollection, self.graphicsViewDict[self.comboBox.currentText()]["view"],
                                        pens.penList, xColumn=yColumnName+"_x", yColumn=yColumnName, rawColumn=rawColumnName, name=yColumnName,
                                        xAxisUnit='', xAxisLabel=yColumnName, windowName=self.comboBox.currentText())
            plottedTrace.x = numpy.append(plottedTrace.x, range(self.childTableModel.childList[index][1]))
            plottedTrace.y = numpy.append(plottedTrace.y, self.childTableModel.childList[index][1]*[0.0])
            plottedTrace.traceCollection.x = plottedTrace.x
            plottedTrace.traceCollection.y = plottedTrace.y
            self.plottedTraceList.append(plottedTrace)
        parentName = self.getUniqueName(self.parentNameField.text())
        self.plottedTraceList[0].traceCollection.name = parentName
        self.plottedTraceList[0].traceCollection.description["name"] = parentName
        self.plottedTraceList[0].traceCollection.description["comment"] = ""
        self.plottedTraceList[0].traceCollection.description["PulseProgram"] = None
        self.plottedTraceList[0].traceCollection.description["Scan"] = None
        self.plottedTraceList[0].traceCollection.description["traceFinalized"] = datetime.now(pytz.utc)
        self.plottedTraceList[0].traceCollection.autoSave = True
        self.plottedTraceList[0].traceCollection.filenamePattern = parentName
        if len(self.plottedTraceList)==1:
            category = None
        else:
            category = parentName
        for plottedTrace in self.plottedTraceList:
            plottedTrace.category = category
        for index, plottedTrace in reversed(list(enumerate(self.plottedTraceList))):
            self.addTrace(plottedTrace, pen=-1)
        if self.expandNew:
            self.expand(self.plottedTraceList[0])
        self.resizeColumnsToContents()
        self.resetTraceOptions()
        self.settings.filelist += [self.plottedTraceList[0].traceCollection.filename]
        self.settings.filelist = list(set(self.settings.filelist))
        self.updateNames()

    def onClose(self):
        if self.tableEditor is not None:
            self.tableEditor.close()

