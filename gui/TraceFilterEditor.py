# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtWidgets, QtGui
import numpy
from uiModules.RotatedHeaderView import RotatedHeaderView
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.Utility import unique
from uiModules.KeyboardFilter import KeyListFilter
strmap = lambda x: list(map(str, x))

class RotatedHeaderShrink(RotatedHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        super().setSectionResizeMode(3)

class TraceFilterTableModel(QtCore.QAbstractTableModel):
    def __init__(self, uniqueSelectedNodes, model, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = []
        self.nodelookup = dict()
        self.arraylen = 0
        self.model = model
        self.dataLookup = {
            (QtCore.Qt.DisplayRole): self.customDisplay,
            (QtCore.Qt.BackgroundRole): self.bgLookup
        }
        self.filterDataLookup = {
            (QtCore.Qt.DisplayRole): lambda index: '',
            (QtCore.Qt.BackgroundRole): self.bgFilterLookup
        }
        for node in uniqueSelectedNodes:
            dataNodes = model.getDataNodes(node)
            for dataNode in dataNodes:
                self.dataChanged.connect(lambda *x: dataNode.content.plot(dataNode.content.curvePen), QtCore.Qt.UniqueConnection)
                self.constructArray(dataNode.content)
        self.numcols = len(self.nodelookup)

    def bgLookup(self, index):
        if index.isValid() and len(self.nodelookup[index.column()]['data']) > index.row() and \
                        str(self.nodelookup[index.column()]['data'][index.row()]) != 'nan' and \
                isinstance(self.nodelookup[index.column()]['data'][index.row()], float):
            return QtGui.QColor(255, 255, 255, 255)
        else:
            return QtGui.QColor(215, 215, 215, 255)

    def bgFilterLookup(self, index):
        if index.column() == self.numcols:
            if index.row() >= len(self.nodelookup[0]['filter']) or self.nodelookup[0]['filter'][index.row()]:
                return QtGui.QColor(0, 205, 0, 255)
            else:
                return QtGui.QColor(205, 0, 0, 255)

    def customDisplay(self, index):
        if index.isValid() and len(self.nodelookup[index.column()]['data']) > index.row():
            retstr = str(self.nodelookup[index.column()]['data'][index.row()])
            return retstr if retstr != 'nan' else ''
        return ''

    def rowCount(self, parent):
        return max([len(self.nodelookup[i]['data']) for i in range(len(self.nodelookup))])

    def columnCount(self, parent):
        return len(self.nodelookup)+1

    def data(self, index, role):
        if index.column() == self.numcols:
            return self.filterDataLookup.get(role, lambda index: None)(index)
        if index.isValid() and len(self.nodelookup[index.column()]['data']) >= index.row():
            return self.dataLookup.get(role, lambda index: None)(index)

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            for i in range(len(self.nodelookup)):
                self.nodelookup[i]['filter'][index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def setValue(self, index, value):
        self.setData(index, value, QtCore.Qt.EditRole)

    def flags(self, index):
        if index.column() == self.numcols:
            return QtCore.Qt.ItemIsEnabled #| QtCore.Qt.ItemIsEditable
        else:
            return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def constructArray(self, datain):
        if self.arraylen == 0 or not numpy.array_equal(self.nodelookup[self.arraylen-1]['parent'].traceCollection[self.nodelookup[self.arraylen-1]['parent']._xColumn], datain.traceCollection[datain._xColumn]):#datain.trace.x):
            self.currx = self.arraylen
            if datain.filt is None:
                datain.filt = numpy.array([1]*len(datain.traceCollection[datain._xColumn]))
            elif not isinstance(datain.filt, numpy.ndarray):
                datain.filt = numpy.array(datain.filt)
            self.nodelookup[self.arraylen] = {'name': datain.name, 'xy': 'x', 'data': datain.traceCollection[datain._xColumn], 'column': datain._xColumn, 'parent': datain, 'xparent': self.currx, 'filter': datain.filt}
            self.arraylen += 1
        if datain.filt is None:
            datain.filt = numpy.array([1]*len(datain.traceCollection[datain._xColumn]))
        elif not isinstance(datain.filt, numpy.ndarray):
            datain.filt = numpy.array(datain.filt)
        self.nodelookup[self.arraylen] = {'name': datain.name, 'xy': 'x', 'data': datain.traceCollection[datain._xColumn], 'column': datain._xColumn, 'parent': datain, 'xparent': self.currx, 'filter': datain.filt}
        self.nodelookup[self.arraylen] = {'name': datain.name, 'xy': 'y', 'data': datain.traceCollection[datain._yColumn], 'column': datain._yColumn, 'parent': datain, 'xparent': self.currx, 'filter': datain.filt}
        self.arraylen += 1

    def headerData(self, column, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QAbstractTableModel.headerData(self, column, orientation, role)
        if orientation == QtCore.Qt.Horizontal:
            if column == self.numcols:
                return 'Enabled'
            else:
                return self.nodelookup[column]['name']+'.'+self.nodelookup[column]['xy']
        return QtCore.QAbstractTableModel.headerData(self, column, orientation, role)

    def onClicked(self, index):
        if index.column() == self.numcols:
            val = 0 if self.nodelookup[0]['filter'][index.row()] else 1
            for j in range(self.numcols):
                self.nodelookup[j]['filter'][index.row()] = val
            self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            return True
        return False

    def disableContents(self, indices):
        for j in range(self.numcols):
            for i in indices:
                self.nodelookup[j]['filter'][i.row()] = 0
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        return True

    def enableContents(self, indices):
        for j in range(self.numcols):
            for i in indices:
                self.nodelookup[j]['filter'][i.row()] = 1
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        return True

    def toggleContents(self, indices):
        rows = sorted(unique([i.row() for i in indices]))
        for i in rows:
            val = 0 if self.nodelookup[0]['filter'][i] else 1
            for j in reversed(range(self.numcols)):
                self.nodelookup[j]['filter'][i] = val
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
        return True

class TraceFilterEditor(QtWidgets.QWidget):
    finishedEditing = QtCore.pyqtSignal()
    def __init__(self, *args):
        super().__init__(*args)

    def setupUi(self, plottedTrace, model):
        self.tablemodel = TraceFilterTableModel(plottedTrace, model, self)
        self.tableview = QtWidgets.QTableView()
        self.tableview.setModel(self.tablemodel)
        self.delegate = MagnitudeSpinBoxDelegate()
        self.tableview.setItemDelegate(self.delegate)
        self.tableview.setHorizontalHeader(RotatedHeaderShrink(QtCore.Qt.Horizontal, self.tableview))
        self.tableview.clicked.connect(self.tablemodel.onClicked)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tableview)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.disableContents = QtWidgets.QAction("Disable contents (d)", self)
        self.disableContents.triggered.connect(self.onDisableContents)
        self.addAction(self.disableContents)

        self.enableContents = QtWidgets.QAction("Enable contents (e)", self)
        self.enableContents.triggered.connect(self.onEnableContents)
        self.addAction(self.enableContents)

        self.toggleContents = QtWidgets.QAction("Toggle contents (space)", self)
        self.toggleContents.triggered.connect(self.onToggleContents)
        self.addAction(self.toggleContents)

        self.toggleFilterType = KeyListFilter([QtCore.Qt.Key_Space, QtCore.Qt.Key_T])
        self.toggleFilterType.keyPressed.connect(self.onToggleContents)
        self.tableview.installEventFilter(self.toggleFilterType)

        self.setDisableFilterType = KeyListFilter([QtCore.Qt.Key_D])
        self.setDisableFilterType.keyPressed.connect(self.onDisableContents)
        self.tableview.installEventFilter(self.setDisableFilterType)

        self.setEnableFilterType = KeyListFilter([QtCore.Qt.Key_E])
        self.setEnableFilterType.keyPressed.connect(self.onEnableContents)
        self.tableview.installEventFilter(self.setEnableFilterType)

        self.resize(950, 650)
        self.move(300, 300)
        self.setWindowTitle('Trace Table Editor')
        self.show()

    def onDisableContents(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.disableContents(zeroColSelInd)

    def onEnableContents(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.enableContents(zeroColSelInd)

    def onToggleContents(self):
        zeroColSelInd = self.tableview.selectedIndexes()
        self.tablemodel.toggleContents(zeroColSelInd)

    def closeEvent(self, a):
        self.finishedEditing.emit()

