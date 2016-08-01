# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from collections import ChainMap
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets

from modules.Expression import Expression
from modules.SequenceDict import SequenceDict
from modules.firstNotNone import firstNotNone


class BinaryTableModel(QtCore.QAbstractTableModel):
    """Class for tables which contain green/white/(red) boxes for settings shutters, triggers, and counters
    Args:
        dataDict (dict): The binary data. key: name, val: Variable datatype
        size (int): The number of bits in the binary data. (NOT the number of columns in the table)
        tristate (bool): True: red/green/white boxes, i.e. for shutters. False: green/white boxes.
        channelNames (list): Names to display for the channels
        channelSignal (signal): signal that indicates that a channel name header changed
        stateDict (dict): A dict of binary data values. key: name, val: list of the form [1,1,0,1,0,0,-1...]
        """
    contentsChanged = QtCore.pyqtSignal()
    colorLookup = {-1: QtGui.QColor(QtCore.Qt.red),
                    0: QtGui.QColor(QtCore.Qt.white),
                    1: QtGui.QColor(QtCore.Qt.green)}
    dependencyColorLookup = {-1: QtGui.QColor(QtCore.Qt.red).lighter(155),
                             0: QtGui.QColor(QtCore.Qt.blue).lighter(188),
                             1: QtGui.QColor(QtCore.Qt.green).lighter(155)}
    expression = Expression()
    def __init__(self, dataDict, channelNames, size, globalDict=None, channelSignal=None, tristate=False, parent=None, *args):
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.size = size
        self.tristate = tristate
        self.globalDict = globalDict
        self.channelNames = channelNames
        self.channelSignal = channelSignal
        self.columnOffset = 1 if not self.tristate else 2
        self.numericDataColumn = 0
        self.numericMaskColumn = 1 if self.tristate else None
        if self.tristate:
            maskKey = max(self.size, len(self.channelNames))
            self.channelNames[maskKey] = 'Numeric Mask'
            dataKey = maskKey + 1
        else:
            dataKey = max(self.size, len(self.channelNames))
        self.channelNames[dataKey] = 'Numeric Data'
        if self.channelSignal:
            self.channelSignal.dataChanged.connect( self.onHeaderChanged )
        self.textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
        self.disabledBG = QtGui.QColor(200, 200, 200)
        self.setDataDict(dataDict, resetModel=False)
        self.dataLookup = {
           (QtCore.Qt.DisplayRole, self.numericDataColumn): lambda row: firstNotNone(getattr(self.dataDict.at(row), 'text', None), hex(self.dataDict.at(row).data)),
            (QtCore.Qt.EditRole, self.numericDataColumn): lambda row: firstNotNone(getattr(self.dataDict.at(row), 'text', None), self.dataDict.at(row).data),
            (QtCore.Qt.DisplayRole, self.numericMaskColumn): lambda row: firstNotNone(getattr(self.maskDict.at(row), 'text', None), hex(self.maskDict.at(row).data)) if self.maskDict.at(row) else None,
            (QtCore.Qt.EditRole, self.numericMaskColumn): lambda row: firstNotNone(getattr(self.maskDict.at(row), 'text', None), self.maskDict.at(row).data) if self.maskDict.at(row) else None,
            (QtCore.Qt.ToolTipRole, self.numericDataColumn): lambda row: hex(self.dataDict.at(row).data) if getattr(self.dataDict.at(row), 'text', None) else None,
            (QtCore.Qt.ToolTipRole, self.numericMaskColumn): lambda row: (hex(self.maskDict.at(row).data) if getattr(self.maskDict.at(row), 'text', None) else None) if self.maskDict.at(row) else None,
            (QtCore.Qt.BackgroundRole, self.numericDataColumn): lambda row: self.textBG if getattr(self.dataDict.at(row), 'text', None) else None,
            (QtCore.Qt.BackgroundRole, self.numericMaskColumn): lambda row: self.disabledBG if not self.maskDict.at(row) else (self.textBG if getattr(self.maskDict.at(row), 'text', None) else None)
        }
        self.setDataLookup =  {
            (QtCore.Qt.EditRole, self.numericDataColumn): self.setValue,
            (QtCore.Qt.EditRole, self.numericMaskColumn): self.setValue,
            (QtCore.Qt.UserRole, self.numericDataColumn): self.setText,
            (QtCore.Qt.UserRole, self.numericMaskColumn): self.setText
        }

    def setStateDict(self, row):
        """set the stateDict, which is derived from the dataDict and used for more efficient display"""
        name = self.dataDict.keyAt(row)
        var = self.dataDict.at(row)
        self.stateDict[name] = []
        data = var.data
        for column in range(self.size):
            bit = 0x1<<(self.size-column-1)
            if not self.tristate:
                self.stateDict[name].append(1 if bit & data > 0 else 0)
            else:
                maskVar = self.maskDict[name]
                mask = maskVar.data if maskVar else ((1<<self.size)-1)
                self.stateDict[name].append((1 if data & bit else -1) if mask & bit else 0)

    def currentState(self, index):
        row = index.row()
        column = index.column()
        name = self.dataDict.keyAt(row)
        return self.stateDict[name][column - self.columnOffset]

    def onClicked(self, index):
        column = index.column()
        row = index.row()
        updateAll = False
        if column >= self.columnOffset:
            bit = 0x1<<(self.size-column-1+self.columnOffset)
            name = self.dataDict.keyAt(row)
            var = self.dataDict.at(row)
            if getattr(var, 'text', None):
                updateAll = True
                var.lastText = var.text
            var.text = None
            if not self.tristate:
                state = self.stateDict[name][column-self.columnOffset] = 1 - self.currentState(index)
                var.data = (var.data & ~bit) | bit if state else var.data & ~bit
            else:
                mask = self.maskDict.at(row)
                if getattr(mask, 'text', None):
                    updateAll = True
                    mask.lastText = mask.text
                state = self.stateDict[name][column-self.columnOffset] = (self.currentState(index)+2)%3 -1 if mask else -self.currentState(index)
                if mask is not None:
                    mask.text = None
                    mask.data = (mask.data & ~bit) | bit if state else mask.data & ~bit
                if state == -1:
                    var.data &= ~bit
                elif state == 1:
                    var.data = (var.data & ~bit) | bit
            if not updateAll:
                numericDataIndex = self.createIndex(row, self.numericDataColumn)
                self.dataChanged.emit(index, index)
                self.dataChanged.emit(numericDataIndex, numericDataIndex)
                if self.tristate:
                    numericMaskIndex = self.createIndex(row, self.numericMaskColumn)
                    self.dataChanged.emit(numericMaskIndex, numericMaskIndex)
            else:
                self.emitRowChanged(row)
            self.contentsChanged.emit()

    def setDataDict(self, dataDict, resetModel=True):
        if resetModel:
            self.beginResetModel()
        if not self.tristate:
            self.dataDict = dataDict
        else:
            self.dataDict = SequenceDict()
            self.maskDict = SequenceDict()
            for name, var in dataDict.items():
                self.dataDict[name] = var[0]
                self.maskDict[name] = var[1]
        self.stateDict = dict()
        for row in range(len(self.dataDict)):
            self.recalculateDependents(row)
            self.setStateDict(row)
        if resetModel:
            self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.dataDict)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return self.size + self.columnOffset

    def data(self, index, role):
        if index.isValid():
            if role==QtCore.Qt.BackgroundRole and index.column() >= self.columnOffset:
                dataText = getattr(self.dataDict.at(index.row()), 'text', None)
                maskText = getattr(self.maskDict.at(index.row()), 'text', None) if self.tristate else None
                return self.colorLookup[ self.currentState(index) ] if (not dataText and not maskText) else self.dependencyColorLookup[ self.currentState(index) ]
            else:
                return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())

    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)

    def setValue(self, index, value):
        row = index.row()
        column = index.column()
        if column==self.numericDataColumn:
            var = self.dataDict.at(row)
            var.data = int(value)
        elif self.tristate and column==self.numericMaskColumn:
            var = self.maskDict.at(row)
            var.data = int(value)
        self.setStateDict(row)
        self.emitRowChanged(row)
        return True

    def emitRowChanged(self, row):
        leftIndex = self.createIndex(row, 0)
        rightIndex = self.createIndex(row, self.columnCount()-1)
        self.dataChanged.emit(leftIndex, rightIndex)

    def setText(self, index, text):
        row = index.row()
        column = index.column()
        if column==self.numericDataColumn:
            var = self.dataDict.at(row)
            # if a text value has been entered, use that for lastText, otherwise use the old text value, otherwise leave it unchanged
            var.lastText = firstNotNone(text, getattr(var,'text',None), getattr(var,'lastText',None))
            var.text = text
        elif self.tristate and column==self.numericMaskColumn:
            mask = self.maskDict.at(row)
            mask.lastText = firstNotNone(text, getattr(mask,'text',None), getattr(mask,'lastText',None))
            mask.text = text
        return True

    def flags(self, index):
        if index.column()>=self.columnOffset:
            return QtCore.Qt.ItemIsEnabled
        elif index.column()==self.numericDataColumn:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        elif self.tristate and index.column()==self.numericMaskColumn:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable if self.maskDict.at(index.row()) else QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled

    def onHeaderChanged(self, first, last):
        self.headerDataChanged.emit(QtCore.Qt.Horizontal, first, last)

    def headerData(self, section, orientation, role):
        key = self.size - section - 1 + self.columnOffset
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.channelNames.get(key, key)
            elif orientation == QtCore.Qt.Vertical:
                return self.dataDict.at(section).name

    def getVariables(self):
        returnDict = {var.name : var.data for var in self.dataDict.values()}
        if self.tristate:
            returnDict.update( {mask.name : mask.data for mask in self.maskDict.values() if mask} )
        return returnDict

    def recalculateDependents(self, row):
        var = self.dataDict.at(row)
        varText = getattr(var, 'text', None)
        mask = self.maskDict.at(row) if self.tristate else None
        maskText = getattr(mask, 'text', None) if self.tristate else None
        changed=False
        if varText:
            data = self.expression.evaluateAsMagnitude(varText, self.globalDict)
            var.data = int(data)
            changed=True
        if self.tristate and mask and maskText:
            maskData = self.expression.evaluateAsMagnitude(maskText, self.globalDict)
            mask.data = int(maskData)
            changed=True
        return changed

    def recalculateAllDependents(self):
        for row in range(len(self.dataDict)):
            changed = self.recalculateDependents(row)
            if changed:
                self.setStateDict(row)
                self.emitRowChanged(row)


class ShutterTableModel(BinaryTableModel):
    def __init__(self, dataDict, channelNames, size, globalDict=None, channelSignal=None, parent=None, *args):
        bitsLookup = sorted(channelNames.defaultDict.keys())
        if bitsLookup:
            size = max(size, bitsLookup[-1] + 1)
        super().__init__(dataDict, channelNames, size, globalDict, channelSignal, True, parent, *args)


class TriggerTableModel(BinaryTableModel):
    def __init__(self, dataDict, channelNames, size, globalDict=None, channelSignal=None, parent=None, *args):
        super().__init__(dataDict, channelNames, size, globalDict, channelSignal, False, parent, *args)


class CounterTableModel(BinaryTableModel):
    def __init__(self, dataDict, channelNames, size=49, globalDict=None, parent=None, *args):
        defaultChannelNames = ['Count {0}'.format(i) for i in range(24)]
        defaultChannelNames.extend( ['TS {0}'.format(i) for i in range(8)] )
        defaultChannelNames.extend( ['ADC {0}'.format(i) for i in range(8)] )
        defaultChannelNames.extend( ['PI {0}'.format(i) for i in range(8)] )
        defaultChannelNames.append( 'time Tick' )
        defaultChannelNames.append('ID')
        channelNames = ChainMap( channelNames, dict( ((index, name) for index, name in enumerate(defaultChannelNames)) ) )
        super(CounterTableModel, self).__init__(dataDict, channelNames, size, globalDict, None, False, parent, *args)
        self.columnOffset += 1
        self.idColumn = self.columnOffset-1
        self.setDataLookup.update( {(QtCore.Qt.EditRole, self.idColumn): self.setValue} )

    def currentId(self, index):
        var = self.dataDict.at(index.row())
        return var.data >> 56

    def setCurrentId(self, index, newid):
        var = self.dataDict.at(index.row())
        var.data = (var.data & 0xffffffffffffff) | ((newid & 0xff) << self.size+7)

    def data(self, index, role):
        if index.isValid():
            if index.column() == self.idColumn:
                if role == QtCore.Qt.DisplayRole:
                    return str(self.currentId(index))
                elif role==QtCore.Qt.EditRole:
                    return self.currentId(index)
                elif role==QtCore.Qt.BackgroundRole:
                    dataText = getattr(self.dataDict.at(index.row()), 'text', None)
                    return None if not dataText else self.dependencyColorLookup[0]
            else:
                return super().data(index, role)

    def setValue(self, index, value):
        row = index.row()
        column = index.column()
        var = self.dataDict.at(row)
        if index.isValid() and column==self.idColumn and 0<=value<256:
            self.setCurrentId(index, int(value))
            var.lastText = getattr(var, 'text', None)
            var.text = None
            numericIndex = self.createIndex(row, self.numericDataColumn)
            self.dataChanged.emit(numericIndex, numericIndex)
            return True
        else:
            return super().setValue(index, value)

    def flags(self, index):
        if index.column()==self.idColumn:
            return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        else:
            return super().flags(index)
        return QtCore.Qt.ItemIsEnabled


class BinaryTableView(QtWidgets.QTableView):
    def setupUi(self, globalDict=None):
        self.globalDict = globalDict if globalDict else dict()

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu()
        row = self.currentIndex().row()
        model = self.model()
        var = model.dataDict.at(row)
        varLastText = getattr(var, 'lastText', None)
        mask = model.maskDict.at(row) if model.tristate else None
        maskLastText = getattr(mask, 'lastText', None)
        if not model.tristate or (model.tristate and mask is None):
            if varLastText and varLastText in self.globalDict:
                pushAndSetToLastGlobalAction = self.menu.addAction("push and set to {0}".format(varLastText))
                pushAndSetToLastGlobalAction.triggered.connect(partial(self.pushAndSetToLastGlobal, row, var, varLastText))
        else:
            if varLastText and maskLastText and (varLastText in self.globalDict) and (maskLastText in self.globalDict):
                pushAndSetToLastGlobalAction = self.menu.addAction("push and set to {0}, {1}".format(varLastText, maskLastText))
                pushAndSetToLastGlobalAction.triggered.connect(partial(self.pushAndSetToLastGlobal, row, var, varLastText, mask, maskLastText))
        pushAndSetToGlobalAction = self.menu.addAction("push and set to global...")
        pushAndSetToGlobalAction.triggered.connect(partial(self.pushAndSetToGlobal, row, var, mask))
        self.menu.popup(QtGui.QCursor.pos())

    def pushAndSetToLastGlobal(self, row, var, varLastText, mask=None, maskLastText=None):
        self.globalDict[varLastText] = var.data
        var.text = varLastText
        if mask and maskLastText:
            self.globalDict[maskLastText] = mask.data
            mask.text = maskLastText
        self.model().emitRowChanged(row)

    def pushAndSetToGlobal(self, row, var, mask=None):
        self.selectGlobalDialog = QtWidgets.QDialog()
        self.selectGlobalDialog.setWindowTitle("Select Global")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.selectGlobalDialog)

        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.verticalLayout.addLayout(self.horizontalLayout)
        dataLabel = QtWidgets.QLabel("Data Global")
        self.dataComboBox = QtWidgets.QComboBox()
        self.dataComboBox.addItems(sorted(self.globalDict.keys()))
        if self.model().tristate:
            self.horizontalLayout.addWidget(dataLabel)
            self.horizontalLayoutMask = QtWidgets.QHBoxLayout()
            self.verticalLayout.addLayout(self.horizontalLayoutMask)
            maskLabel = QtWidgets.QLabel("Mask Global")
            self.maskComboBox = QtWidgets.QComboBox()
            self.maskComboBox.addItems(sorted(self.globalDict.keys()))
            self.horizontalLayoutMask.addWidget(maskLabel)
            self.horizontalLayoutMask.addWidget(self.maskComboBox)
        self.horizontalLayout.addWidget(self.dataComboBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.selectGlobalDialog.accept)
        self.buttonBox.accepted.connect(partial(self.setGlobal, row, var, mask))
        self.buttonBox.rejected.connect(self.selectGlobalDialog.reject)
        self.selectGlobalDialog.exec_()

    def setGlobal(self, row, var, mask):
        model = self.model()
        dataText = self.dataComboBox.currentText()
        self.globalDict[dataText] = var.data
        var.text = dataText
        if model.tristate and mask:
            maskText = self.maskComboBox.currentText()
            self.globalDict[maskText] = mask.data
            mask.text = maskText
        model.emitRowChanged(row)


if __name__=='__main__':
    from pulseProgram.TriggerDictionary import TriggerDictionary
    from pulseProgram.ShutterDictionary import ShutterDictionary
    from pulseProgram.CounterDictionary import CounterDictionary
    from pulseProgram.PulseProgram import Variable
    from pulser.ChannelNameDict import ChannelNameDict
    from uiModules.RotatedHeaderView import RotatedHeaderView
    from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
    from modules.quantity import Q
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    splitter = QtWidgets.QSplitter()
    splitter.setOrientation(QtCore.Qt.Vertical)
    window.setCentralWidget(splitter)

    triggerView = BinaryTableView()
    triggerSize=16
    a = Variable(); a.data = 0; a.name = 'My trigger a'
    b = Variable(); b.data = 0; b.name = 'My trigger b'
    triggerChannelNames = {n: "Trigger {0}".format(n) for n in range(triggerSize)}
    triggerDict = TriggerDictionary([
        ('trigger1', a),
        ('trigger2', b) ])
    triggerModel = TriggerTableModel(triggerDict, triggerChannelNames, triggerSize)

    shutterView = BinaryTableView()
    shutterSize = 64
    c = Variable(); c.data = 0; c.name = 'My shutter c'
    c_mask = Variable(); c_mask.data = 0; c_mask.name = 'My shutter_mask c_mask'
    d = Variable(); d.data = 0; d.name = 'My shutter d'
    d_mask = Variable(); d_mask.data = 0; d_mask.name = 'My shutter_mask d_mask'
    e = Variable(); e.data = 0; e.name = 'My shutter e'
    e_mask = None
    shutterChannelNames = ChannelNameDict(DefaultDict={n: "Shutter {0}".format(n) for n in range(shutterSize)})
    shutterDict = ShutterDictionary([
        ('shutter1', (c, c_mask)),
        ('shutter2', (d, d_mask)),
        ('shutter3', (e, e_mask)) ])
    shutterModel = ShutterTableModel(shutterDict, shutterChannelNames, shutterSize)

    counterView = BinaryTableView()
    f = Variable(); f.data = 0; f.name = 'My counter f'
    g = Variable(); g.data = 0; g.name = 'My counter g'
    counterChannelNames = dict()
    counterDict = CounterDictionary([
        ('counter1', f),
        ('counter2', g) ])
    counterModel = CounterTableModel(counterDict, counterChannelNames)

    globalDict = {'a': Q(1), 'b': Q(7), 'c': Q(12), 'd': Q(72057594324259089)}

    for view, model in [(triggerView, triggerModel), (shutterView, shutterModel), (counterView, counterModel)]:
        view.setModel(model)
        delegate = MagnitudeSpinBoxDelegate(globalDict=globalDict)
        view.setItemDelegateForColumn(model.numericDataColumn, delegate)
        if model.tristate:
            view.setItemDelegateForColumn(model.numericMaskColumn, delegate)
        view.clicked.connect(model.onClicked)
        view.setHorizontalHeader( RotatedHeaderView(QtCore.Qt.Horizontal, view ) )
        view.resizeColumnsToContents()
        view.setupUi(globalDict)
        splitter.addWidget(view)
    counterIdDelegate = MagnitudeSpinBoxDelegate()
    counterView.setItemDelegateForColumn(counterModel.idColumn, counterIdDelegate)

    window.show()
    sys.exit(app.exec_())