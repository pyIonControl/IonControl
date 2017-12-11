# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtWidgets, QtGui
import numpy
from uiModules.RotatedHeaderView import RotatedHeaderView
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from uiModules.KeyboardFilter import KeyListFilter
from modules.Utility import unique
import copy
from functools import partial
from collections import deque

strmap = lambda x: list(map(str, x))

class RotatedHeaderShrink(RotatedHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        super().setSectionResizeMode(3)

class NamedTraceTableModel(QtCore.QAbstractTableModel):
    updateUndo = QtCore.pyqtSignal()
    def __init__(self, uniqueSelectedNodes, model, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = []
        self.nodelookup = dict()
        self.undoStack = deque()
        self.redoStack = deque()
        self.arraylen = 0
        self.model = model
        self.dataLookup = {
            (QtCore.Qt.DisplayRole): self.customDisplay,
            (QtCore.Qt.EditRole): lambda index: self.nodelookup[index.column()]['data'][index.row()],
            (QtCore.Qt.BackgroundRole): self.bgLookup
            }
        for node in uniqueSelectedNodes:
            dataNodes = model.getDataNodes(node)
            for dataNode in dataNodes:
                self.dataChanged.connect(dataNode.content.replot, QtCore.Qt.UniqueConnection)
                self.constructArray(dataNode.content)
        self.filterUnnecessaryNaNs()
        self.updateUndo.connect(self.pushToUndoStack)
        maxlen = max([len(self.nodelookup[i]['data']) for i in range(len(self.nodelookup))])
        self.padwithNaN(maxlen)
        self.initialData = self.getRelevantNodeLookupData()

    def overwriteNodeLookupData(self, newLU, oldLU=None):
        if oldLU is None:
            oldLU = self.nodelookup
        for k,v in newLU.items():
            oldLU[k]['parent'].traceCollection[oldLU[k]['column']] = v
            oldLU[k]['data'] = oldLU[k]['parent'].traceCollection[oldLU[k]['column']]

    def getRelevantNodeLookupData(self):
        return {k:copy.copy(v['data']) for k,v in self.nodelookup.items()}

    def pushToUndoStack(self):
        self.undoStack.append(self.getRelevantNodeLookupData())
        self.redoStack.clear()

    def popFromUndoStack(self):
        if self.undoStack:
            self.redoStack.append(self.undoStack.pop())
            if self.undoStack:
                self.overwriteNodeLookupData(self.undoStack[-1])
            else:
                self.overwriteNodeLookupData(self.initialData)
        else:
            self.overwriteNodeLookupData(self.initialData)

    def undo(self):
        self.popFromUndoStack()
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()

    def redo(self):
        if self.redoStack:
            self.overwriteNodeLookupData(self.redoStack.pop())
            self.undoStack.append(self.getRelevantNodeLookupData())
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            self.layoutChanged.emit()

    def padwithNaN(self, maxlen):
        for k, v in self.nodelookup[0]['parent'].traceCollection.items():
            if type(v) is numpy.ndarray and len(v) > 0:
                self.nodelookup[0]['parent'].traceCollection[k] = numpy.append(v, [numpy.nan]*(maxlen-len(v)))
        for k, v in self.nodelookup.items():
            self.nodelookup[k]['data'] = self.nodelookup[k]['parent'].traceCollection[self.nodelookup[k]['column']]

    def bgLookup(self, index):
        if index.isValid() and len(self.nodelookup[index.column()]['data']) > index.row() and \
                str(self.nodelookup[index.column()]['data'][index.row()]) != 'nan' and \
                isinstance(self.nodelookup[index.column()]['data'][index.row()], float):
            return QtGui.QColor(255, 255, 255, 255)
        else:
            return QtGui.QColor(215, 215, 215, 255)

    def customDisplay(self, index):
        if index.isValid() and len(self.nodelookup[index.column()]['data']) > index.row():
            retstr = str(self.nodelookup[index.column()]['data'][index.row()])
            return retstr if retstr != 'nan' else ''
        return ''

    def rowCount(self, parent):
        return max([len(self.nodelookup[i]['data']) for i in range(len(self.nodelookup))])

    def columnCount(self, parent):
        return len(self.nodelookup)

    def data(self, index, role):
        if index.isValid() and len(self.nodelookup[index.column()]['data']) >= index.row():
            return self.dataLookup.get(role, lambda index: None)(index)

    def setData(self, index, value, role):
        origData = self.nodelookup[index.column()]['data'][index.row()]
        if role == QtCore.Qt.EditRole:
            self.nodelookup[index.column()]['data'][index.row()] = float(value)
            if self.nodelookup[index.column()]['xy'] == 'x':
                parentx = self.nodelookup[index.column()]['xparent']
                for i in range(len(self.nodelookup)):
                    if self.nodelookup[i]['xparent'] == parentx:
                        self.nodelookup[i]['parent'].traceCollection[self.nodelookup[i]['parent']._xColumn][index.row()] = float(value)
            self.dataChanged.emit(index, index)
            if float(value) != origData:
                self.updateUndo.emit()
            return True
        return False

    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)

    def flags(self, index):
        if index.isValid() and len(self.nodelookup[index.column()]['data']) > index.row() and \
                not str(self.nodelookup[index.column()]['data'][index.row()]) == 'nan' and \
                not str(self.nodelookup[index.column()]['data'][index.row()]) == '':
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled #| QtCore.Qt.ItemIsEditable

    def constructArray(self, datain):
        if self.arraylen == 0 or not numpy.array_equal(self.nodelookup[self.arraylen-1]['parent'].traceCollection[self.nodelookup[self.arraylen-1]['parent']._xColumn], datain.traceCollection[datain._xColumn]):#datain.trace.x):
            self.currx = self.arraylen
            self.nodelookup[self.arraylen] = {'name': datain.name, 'xy': 'x', 'data': datain.traceCollection[datain._xColumn], 'column': datain._xColumn, 'parent': datain, 'xparent': self.currx}
            self.arraylen += 1
        self.nodelookup[self.arraylen] = {'name': datain.name, 'xy': 'y', 'data': datain.traceCollection[datain._yColumn], 'column': datain._yColumn, 'parent': datain, 'xparent': self.currx}
        self.arraylen += 1

    def numTrailingNaNs(self, arr):
        """find the number of trailing NaNs for filtering unnecessary NaNs"""
        return len(numpy.trim_zeros(numpy.isnan(arr)*1,'f'))

    def filterUnnecessaryNaNs(self):
        """NaNs show up when editing two traces with different lengths. if editing a single shorter subtrace 
           or multiple shorter subtraces, trailing NaNs are stripped"""
        nanlist = [self.numTrailingNaNs(self.nodelookup[k]['data']) for k in self.nodelookup.keys()]
        minNaNs = min(nanlist)
        if minNaNs > 0:
            for k in self.nodelookup.keys():
                self.nodelookup[k]['parent'].traceCollection[self.nodelookup[k]['column']] = self.nodelookup[k]['parent'].traceCollection[self.nodelookup[k]['column']][:-minNaNs]
                self.nodelookup[k]['data'] = self.nodelookup[k]['parent'].traceCollection[self.nodelookup[k]['column']]

    def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QAbstractTableModel.headerData(self, column, orientation, role)
        if orientation == QtCore.Qt.Horizontal:
            return self.nodelookup[column]['name']+'.'+self.nodelookup[column]['xy']
        return QtCore.QAbstractTableModel.headerData(self, column, orientation, role)

    def insertRow(self, position, index=QtCore.QModelIndex()):
        numRows = len(self.nodelookup[0]['data'])
        insertableKeys = self.acceptableKeys()
        allColsZero = True
        for k in insertableKeys:
            if len(self.nodelookup[0]['parent'].traceCollection[k]) != 0:
                allColsZero = False
                break
        for k in insertableKeys:
            v = self.nodelookup[0]['parent'].traceCollection[k]
            if len(v) == 0 and allColsZero:
                self.nodelookup[0]['parent'].traceCollection[k] = numpy.append(v, 0.0)
                retval = range(0,1)
            else:
                setval = 0.0
                if all(map(lambda x: x == 'nan',v)):
                    setval = 'nan'
                elif '_filt' in k:
                    setval = 1.0
                self.nodelookup[0]['parent'].traceCollection[k] = numpy.insert(v, position[0].row()+1, setval)
                #self.nodelookup[0]['parent'].traceCollection[k] = numpy.insert(v, position[0].row()+1, 0.0 if not all(map(lambda x: x == 'nan',v)) else 'nan')
                retval = range(position[0].row(), numRows)
        for i in self.nodelookup.keys():
            self.nodelookup[i]['data'] = self.nodelookup[i]['parent'].traceCollection[self.nodelookup[i]['column']]
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.updateUndo.emit()
        self.layoutChanged.emit()
        return retval

    def acceptableKeys(self):
        allKeys = set(self.nodelookup[0]['parent'].traceCollection.keys())
        displayedColumns = set()
        for k in self.nodelookup.keys():
            for key in allKeys:
                if self.nodelookup[k]['column'] in key or key is 'x' or key is 'y':
                    displayedColumns.add(key)
        return displayedColumns

    def copy_rowsorig(self, rows, position):
        for k, v in self.nodelookup[0]['parent'].traceCollection.items():
            if type(v) is numpy.ndarray and len(v) > 0:
                self.nodelookup[0]['parent'].traceCollection[k] = numpy.insert(v, position+1, v[rows])
        for k, v in self.nodelookup.items():
            self.nodelookup[k]['data'] = self.nodelookup[k]['parent'].traceCollection[self.nodelookup[k]['column']]
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        return True

    def copy_rows(self, rows, position):
        for k, v in self.nodelookup[0]['parent'].traceCollection.items():
            if type(v) is numpy.ndarray and len(v) > 0:
                self.nodelookup[0]['parent'].traceCollection[k] = numpy.insert(v, position+1, v[rows])
        for k, v in self.nodelookup.items():
            self.nodelookup[k]['data'] = self.nodelookup[k]['parent'].traceCollection[self.nodelookup[k]['column']]
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        return True

    def set_rows(self, data, position):
        initrow = position[0].row()
        initcol = position[0].column()
        for ci, cv in enumerate(range(initcol, initcol+len(data[0]))):
            if cv in self.nodelookup.keys():#< len(self.nodelookup):
                tracedata = self.nodelookup[cv]['parent'].traceCollection[self.nodelookup[cv]['column']]
                for ri, rv in enumerate(range(initrow, initrow+len(data))):
                    if rv < len(tracedata):
                        tracedata[rv] = data[ri][ci]
                self.nodelookup[cv]['data'] = copy.copy(tracedata)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.layoutChanged.emit()
        return True

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        for key in self.acceptableKeys():
            if len(self.nodelookup[0]['parent'].traceCollection[key]) > position:
                self.nodelookup[0]['parent'].traceCollection[key] = numpy.delete(self.nodelookup[0]['parent'].traceCollection[key], range(position, position+rows))
        for i in self.nodelookup.keys():
            self.nodelookup[i]['data'] = self.nodelookup[i]['parent'].traceCollection[self.nodelookup[i]['column']]
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.updateUndo.emit()
        self.layoutChanged.emit()
        return range(position, rows)

    def clearContents(self, indices):
        for i in indices:
            self.nodelookup[i.column()]['data'][i.row()] = float(0.0)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.updateUndo.emit()
        return True

    def disableCells(self, indices):
        for i in indices:
            self.nodelookup[i.column()]['data'][i.row()] = numpy.nan
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        self.updateUndo.emit()
        return True

    def moveRow(self, rows, delta):
        if len(rows)>0 and (rows[0]>0 or delta>0) and (len(self.nodelookup[0]['data']) > max(rows)+1 or delta < 0):
            for k, v in self.nodelookup[0]['parent'].traceCollection.items():
                if type(v) is numpy.ndarray and len(v) > 0:
                    for row in rows:
                        self.nodelookup[0]['parent'].traceCollection[k][row], self.nodelookup[0]['parent'].traceCollection[k][row+delta] = self.nodelookup[0]['parent'].traceCollection[k][row+delta], self.nodelookup[0]['parent'].traceCollection[k][row]
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            self.updateUndo.emit()
            return True
        return False

class TraceTableEditor(QtWidgets.QWidget):
    finishedEditing = QtCore.pyqtSignal()
    def __init__(self, *args):
        super().__init__(*args)

    def setupUi(self, plottedTrace, model):
        self.tablemodel = NamedTraceTableModel(plottedTrace, model, self)
        self.tableview = QtWidgets.QTableView()
        self.tableview.setModel(self.tablemodel)
        self.delegate = MagnitudeSpinBoxDelegate()
        self.tableview.setItemDelegate(self.delegate)
        self.tableview.setHorizontalHeader(RotatedHeaderShrink(QtCore.Qt.Horizontal, self.tableview))
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tableview)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.addRow = QtWidgets.QAction("Add Row", self)
        self.addRow.triggered.connect(self.onAddRow)
        self.addAction(self.addRow)

        self.removeRow = QtWidgets.QAction("Remove Rows", self)
        self.removeRow.triggered.connect(self.onRemoveRow)
        self.addAction(self.removeRow)

        self.clearContents = QtWidgets.QAction("Clear Contents", self)
        self.clearContents.triggered.connect(self.onClearContents)
        self.addAction(self.clearContents)

        self.disableCells = QtWidgets.QAction("Disable Cells (set to NaN)", self)
        self.disableCells.triggered.connect(self.onDisableCells)
        self.addAction(self.disableCells)

        self.filter = KeyListFilter( [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown] )
        self.filter.keyPressed.connect( self.onReorder )
        self.tableview.installEventFilter(self.filter)

        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self, self.copy_to_clipboard)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Paste), self, self.paste_from_clipboard)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Undo), self, self.tablemodel.undo)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Redo), self, self.tablemodel.redo)

        self.resize(950, 650)
        self.move(300, 300)
        self.setWindowTitle('Trace Table Editor')
        self.show()

    def closeEvent(self, a):
        self.finishedEditing.emit()

    def onAddRow(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.insertRow(zeroColSelInd)

    def onRemoveRow(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        initRow = zeroColSelInd[0].row()
        finRow = zeroColSelInd[-1].row()-initRow+1
        self.tablemodel.removeRows(initRow, finRow)

    def onClearContents(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.clearContents(zeroColSelInd)

    def onDisableCells(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.disableCells(zeroColSelInd)

    def onReorder(self, key):
        if key in [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown]:
            indexes = self.tableview.selectedIndexes()
            up = key == QtCore.Qt.Key_PageUp
            delta = -1 if up else 1
            rows = sorted(unique([i.row() for i in indexes]), reverse=not up)
            if self.tablemodel.moveRow( rows, delta):
                selectionModel = self.tableview.selectionModel()
                selectionModel.clearSelection()
                for index in indexes:
                    selectionModel.select(self.tablemodel.createIndex(index.row()+delta, index.column()), QtCore.QItemSelectionModel.Select)

    def copy_to_clipboard_orig(self):
        """ Copy the list of selected rows to the clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        rows = sorted(unique([ i.row() for i in self.tableview.selectedIndexes()]))
        clip.setText(str(rows))

    def copy_to_clipboard(self):
        """ Copy the list of selected rows to the clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        data = []
        dataline = []
        oldrow = None
        for ind in sorted(self.tableview.selectedIndexes(), key=lambda x: x.row()*1000+x.column()):
            if oldrow is None:
                oldrow = ind.row()
            if oldrow != ind.row():
                oldrow = ind.row()
                data.append('\t'.join(dataline))
                dataline = []
            dataline += [str(self.tablemodel.nodelookup[ind.column()]['data'][ind.row()])]
        data.append('\t'.join(dataline))
        clip.setText('\n'.join(data))
        return True

    def paste_from_clipboard_orig(self):
        """ Append the string of rows from the clipboard to the end of the TODO list. """
        clip = QtWidgets.QApplication.clipboard()
        row_string = str(clip.text())
        try:
            row_list = list(map(int, row_string.strip('[]').split(',')))
        except ValueError:
            raise ValueError("Invalid data on clipboard. Cannot paste into TODO list")
        zeroColSelInd = self.tableview.selectedIndexes()
        initRow = zeroColSelInd[-1].row()
        self.tablemodel.copy_rows(row_list, initRow)


    def paste_from_clipboard(self):
        """ Append the string of rows from the clipboard to the end of the TODO list. """
        clip = QtWidgets.QApplication.clipboard()
        row_string = str(clip.text())
        row_list = row_string.splitlines()
        raw_data = []
        for row in row_list:
            try:
                raw_data.append(list(map(float, row.split('\t'))))
            except ValueError:
                raise ValueError("Invalid data on clipboard. Cannot paste into editor.")
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.set_rows(raw_data, zeroColSelInd)

