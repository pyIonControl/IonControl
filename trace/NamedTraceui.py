# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os.path
import PyQt5.uic
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

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/NamedTraceui.ui')
TraceuiForm, TraceuiBase = PyQt5.uic.loadUiType(uipath)

class NewTraceTableModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.childList = [["",0.0]]
        self.dataLookup = {(QtCore.Qt.DisplayRole): lambda index: self.childList[index.row()][index.column()] if index.column() == 0 else int(self.childList[index.row()][index.column()]),#self.displayGain(index.row()),#(self.childList[index.row()].value),
                           (QtCore.Qt.EditRole): lambda index: self.childList[index.row()][index.column()] if index.column() == 0 else int(self.childList[index.row()][index.column()]) } #self.displayGain(self.childList[index.row()].value)}
        self.headerDataLookup = ['Child Name', 'Length']

    def init(self):
        self.childList = [["",0.0]]
        self.layoutChanged.emit()

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

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('unplotLastTrace', True)
        self.__dict__.setdefault('collapseLastTrace', False)
        self.__dict__.setdefault('expandNew', True)
        self.__dict__.setdefault('filelist', [])

class NamedTraceui(Traceui.TraceuiMixin, TraceuiForm, TraceuiBase):
    externalUpdate = QtCore.pyqtSignal()
    def __init__(self, penicons, config, experimentName, graphicsViewDict, parent=None, lastDir=None, hasMeasurementLog=False, highlightUnsaved=False, preferences=None):
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

        self.createTraceOptions.setVisible(False)
        self.childTableModel = NewTraceTableModel()
        self.childTableView.setModel(self.childTableModel)
        self.addChild.clicked.connect(self.onAddRow)
        self.removeChild.clicked.connect(self.onRemoveRow)

        self.editData = QtWidgets.QAction("Edit Data", self)
        self.editData.triggered.connect(self.onEditData)
        self.addAction(self.editData)
        #self.removeData.triggered.connect(self.onNamedDelete)
        self.removeButton.clicked.disconnect()
        self.removeButton.clicked.connect(self.onNamedDelete)
        self.confirmCreateTrace.clicked.connect(self.createRawData)
        self.cancelCreateTrace.clicked.connect(self.resetTraceOptions)
        self.comboBox.currentIndexChanged[int].connect(self.setDefaultPlot)
        #self.traceView.clicked.connect(self.onViewClicked)
        self.comboBox.setCurrentIndex(0)
        self.comboBox.setInsertPolicy(1)
        for plotname in self.graphicsViewDict:
            self.comboBox.insertItem(0, plotname)

        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self, self.copy_to_clipboard)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Paste), self, self.paste_from_clipboard)

        self.saveTrace =  QtWidgets.QAction("Save New Copy", self)
        self.saveTrace.triggered.connect(self.forceSave)
        self.addAction(self.saveTrace)
        try:
            for filename in self.settings.filelist:
                self.openFile(filename)
            self.updateNames()
        except NameError:
            self.settings.filelist = []

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
                self.openFile(fname)
                self.settings.filelist += [fname]
                self.settings.filelist = list(set(self.settings.filelist))
        self.updateNames()

    def setDefaultPlot(self, val):
        self.defaultTracePlot = val

    def updateNames(self):
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
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        self.tableEditor = TraceTableEditor.TraceTableEditor()
        self.tableEditor.setupUi(uniqueSelectedNodes, self.model)
        self.tableEditor.finishedEditing.connect(self.saveAndUpdateFileList)
        self.tableEditor.tablemodel.dataChanged.connect(self.newData)
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def renameTraceField(self, index, newname):
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
        self.newData()
        self.saveAndUpdateFileList()

    def saveAndUpdateFileList(self, keys=set()):
        if self.newDataAvailable:
            if keys == set():
                self.onSave(saveCopy=True)
            else:
                for k in keys:
                    tc = self.model.nodeDict[k].children[0].content.traceCollection
                    tc.save(tc._fileType, saveCopy=True)
            self.settings.filelist = []
            for k,v in self.model.nodeDict.items():
                if v.parent is not None and v.nodeType == 0:
                    self.settings.filelist.append(self.model.nodeDict[k].children[0].content.traceCollection.filename)
        self.newDataAvailable = False

    def updateExternally(self, topNode, child, row, data, col, saveEvery=False):
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
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            for node in uniqueSelectedNodes:
                if node.nodeType == 0:
                    filename = node.children[0].content.traceCollection.filename
                    if filename in self.settings.filelist:
                        self.settings.filelist.remove(filename)
                    #self.onDelete(a)
            self.traceView.onDelete()
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def resetTraceOptions(self):
        self.createNamedTrace.setChecked(False)
        self.createTraceOptions.setVisible(False)
        self.parentNameField.setText("")
        self.childTableModel.init()

    def createRawData(self):
        traceCollection = TraceCollection(record_timestamps=False)
        self.plottedTraceList = list()
        for index in reversed(range(len(self.childTableModel.childList))):
            yColumnName = self.childTableModel.childList[index][0]
            rawColumnName = '{0}_raw'.format(yColumnName)
            plottedTrace = PlottedTrace(traceCollection, self.graphicsViewDict[self.comboBox.currentText()]["view"], #self.plotDict[self.context.evaluation.evalList[index].plotname]["view"] if self.context.evaluation.evalList[index].plotname != 'None' else None,
                                        pens.penList, xColumn=yColumnName+"_x", yColumn=yColumnName, rawColumn=rawColumnName, name=yColumnName,#.context.evaluation.evalList[index].name,
                                        xAxisUnit='', xAxisLabel=yColumnName, windowName=self.comboBox.currentText())#"Scripting")
            plottedTrace.x = numpy.append(plottedTrace.x, range(self.childTableModel.childList[index][1]))
            plottedTrace.y = numpy.append(plottedTrace.y, self.childTableModel.childList[index][1]*[0.0])
            plottedTrace.raw = numpy.append(plottedTrace.raw, self.childTableModel.childList[index][1]*[0.0])
            self.plottedTraceList.append(plottedTrace)
        self.plottedTraceList[0].traceCollection.name = self.parentNameField.text()
        self.plottedTraceList[0].traceCollection.description["name"] = self.parentNameField.text()
        self.plottedTraceList[0].traceCollection.description["comment"] = ""
        self.plottedTraceList[0].traceCollection.description["PulseProgram"] = None
        self.plottedTraceList[0].traceCollection.description["Scan"] = None
        self.plottedTraceList[0].traceCollection.description["traceFinalized"] = datetime.now(pytz.utc)
        self.plottedTraceList[0].traceCollection.autoSave = True
        #self.plottedTraceList[0].traceCollection.traceCreation = self.plottedTraceList[0].traceCollection.description["traceFinalized"]
        self.plottedTraceList[0].traceCollection.filenamePattern = self.parentNameField.text()
        if len(self.plottedTraceList)==1:
            category = None
        else:
            category = self.plottedTraceList[0].traceCollection.name
        for plottedTrace in self.plottedTraceList:
            plottedTrace.category = category
        for index, plottedTrace in reversed(list(enumerate(self.plottedTraceList))):
            self.addTrace(plottedTrace, pen=-1)
        if self.expandNew:
            self.expand(self.plottedTraceList[0])
        self.resizeColumnsToContents()
        #self.plottedTraceList[0].traceCollection.save()
        #self.finalizeData()
        #self.openFile(self.plottedTraceList[0].traceCollection.filename)
        self.resetTraceOptions()
        self.settings.filelist += [self.plottedTraceList[0].traceCollection.filename]
        self.settings.filelist = list(set(self.settings.filelist))
        self.updateNames()
        self.onSave("text")

