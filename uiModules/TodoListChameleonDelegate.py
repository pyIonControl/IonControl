# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import re
from functools import partial

from PyQt5 import QtGui, QtCore, QtWidgets

from GlobalVariables.GlobalVariablesModel import GridDelegateMixin
from modules.PyqtUtility import BlockSignals
from uiModules.ComboBoxDelegate import ComboBoxDelegateMixin
from uiModules.MagnitudeSpinBox import MagnitudeSpinBox
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegateMixin

class ListCompleterDelegateMixin(object):
    """Completes individual elements in a comma-separated list"""
    def createEditor(self, parent, option, index ):
        if hasattr( index.model(), 'localReplacementDict' ):
            localDict = dict(self.globalDict)
            localDict.update(index.model().localReplacementDict())
        else:
            localDict = self.globalDict
        editor = ListEditor(parent, globalDict=localDict, valueChangedOnEditingFinished=False, emptyStringValue=self.emptyStringValue)
        editor.dimension = index.model().data(index, QtCore.Qt.UserRole)
        self.completer = CustomCompleter((self.globalDict.keys()), self)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
        lineedit = editor.lineEdit()
        self.completer.cursorPos(lineedit.cursorPosition)
        self.completer.setLineEditor(lineedit)
        #lineedit.setCompleter(self.completer)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        editor.setValue(value)
        editor.lineEdit().setCursorPosition(0)
        #try:
            #numberlen = len(re.split(',', str(value))[1])
            #editor.lineEdit().cursorForward(True, numberlen)
        #except:
            #editor.lineEdit().cursorWordForward(True)

    def setModelData(self, editor, model, index):
        value = str(editor.text())
        model.setData(index, value, QtCore.Qt.EditRole)

class CustomCompleter(QtWidgets.QCompleter):
    def __init__(self, tags, parent):
        self.tags = tags
        self.remainingText = ""
        self.remainingPreText = ""
        self.remainingPostText = ""
        self.cursorposition = None
        self.le = None
        super().__init__(self.tags, parent)

    def setLineEditor(self, le):
        self.le = le

    def updateEditorText(self, txt):
        currentHighlightBounds = (self.cursorposition(), len(self.le.selectedText()))
        with BlockSignals(self):
            self.le.setText(self.remainingPreText + txt +self.remainingPostText)
            self.le.setSelection(currentHighlightBounds[0], len(self.remainingPreText + txt)-currentHighlightBounds[0])

    def cursorPos(self, cp):
        self.cursorposition = cp

    def pathFromIndex(self, QModelIndex):
        path = super().pathFromIndex(QModelIndex)
        return self.remainingPreText+path+self.remainingPostText

    def splitPath(self, path):
        if ',' in path:
            matchlen = len(str(path[0:self.cursorposition()]).split(',')[-1])
            self.remainingPreText = path[0:(self.cursorposition()-matchlen)]
            self.remainingPostText = path[self.cursorposition():]
            return [str(path[0:self.cursorposition()]).split(',')[-1]]
        return [path]

class ListEditor(QtWidgets.QAbstractSpinBox):
    valueChanged = QtCore.pyqtSignal(object)
    textValueChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent=None, globalDict=None, valueChangedOnEditingFinished=True, emptyStringValue=0):
        super(ListEditor, self).__init__(parent)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        if valueChangedOnEditingFinished:
            self.editingFinished.connect(self.onEditingFinished)
        self.redTextPalette = QtGui.QPalette()
        self.redTextPalette.setColor(QtGui.QPalette.Text, QtCore.Qt.red)
        self.orangeTextPalette = QtGui.QPalette()
        self.orangeTextPalette.setColor(QtGui.QPalette.Text, QtGui.QColor(0x7d, 0x05, 0x52))
        self.blackTextPalette = QtGui.QPalette()
        self.blackTextPalette.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
        self._dimension = None  # if not None enforces the dimension
        self.globalDict = globalDict if globalDict is not None else dict()
        self.emptyStringValue = emptyStringValue

    def validate(self, inputstring, pos):
        for item in inputstring.split(','):
            if item not in self.globalDict.keys():
                self.lineEdit().setPalette(self.redTextPalette)
                return (QtGui.QValidator.Intermediate, inputstring, pos)
        self.lineEdit().setPalette(self.blackTextPalette)
        return (QtGui.QValidator.Acceptable, inputstring, pos)

    def value(self):
        self.lineEdit().setPalette(self.blackTextPalette)
        text = str(self.lineEdit().text()).strip()
        retList = []
        for item in text.split(','):
            if item in self.globalDict.keys():
                retList.append(item)
            else:
                self.lineEdit().setPalette(self.redTextPalette)
        return retList

    def text(self):
        return str(self.lineEdit().text()).strip()

    def setText(self, string):
        cursorpos = self.lineEdit().cursorPosition()
        self.lineEdit().setText(string)
        self.lineEdit().setCursorPosition(cursorpos)

    def setValue(self, value):
        cursorpos = self.lineEdit().cursorPosition()
        self.lineEdit().setText(str(value))
        self.lineEdit().setCursorPosition(cursorpos)

    def onEditingFinished(self):
        self.textValueChanged.emit(self.text())
        self.valueChanged.emit(self.value())

    def sizeHint(self):
        fontMetrics = QtGui.QFontMetrics(self.font())
        size = fontMetrics.boundingRect(self.lineEdit().text()).size()
        size += QtCore.QSize(8, 0)
        return size

    #def wheelEvent(self, wheelEvent):
        #self.stepBy(copysign(1, wheelEvent.angleDelta().y()))

class TodoListChameleonDelegate(QtWidgets.QStyledItemDelegate, ComboBoxDelegateMixin, ListCompleterDelegateMixin):# MagnitudeSpinBoxDelegateMixin):
    """Class for combo box editors in models"""
    def __init__(self, labelDict):
        QtWidgets.QStyledItemDelegate.__init__(self)

        self.globalDict = labelDict
        self.emptyStringValue = ''

    def createEditor(self, parent, option, index):
        """Create the combo box editor"""
        model = index.model()
        if model.nodeFromIndex(index).entry.scan == 'Rescan' and index.column()==2:
            return ListCompleterDelegateMixin.createEditor(self, parent, option, index)
        else:
            return ComboBoxDelegateMixin.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        """Set the data in the editor based on the model"""
        model = index.model()
        if model.nodeFromIndex(index).entry.scan == 'Rescan' and index.column()==2:
            ListCompleterDelegateMixin.setEditorData(self, editor, index)
        else:
            ComboBoxDelegateMixin.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        """Set the data in the model based on the editor"""
        model = index.model()
        if model.nodeFromIndex(index).entry.scan == 'Rescan' and index.column()==2:
            ListCompleterDelegateMixin.setModelData(self, editor, model, index)
        else:
            ComboBoxDelegateMixin.setModelData(self, editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class ComboBoxGridDelegateMixin(object):
    """Contains methods for drawing a grid and setting the size in a view. Used as part of a delegate in TodoList."""
    gridColor = QtGui.QColor(25, 25, 25, 255) #dark gray
    def paint(self, painter, option, index):
        """Draw the grid if the node is a data node"""
        model = index.model()
        painter.save()
        if model is None:
            print('model is none!')
        painter.setBrush(model.colorData(index)) #references data in model to draw background
        if index.column() == 0:
            option.font.setWeight(QtGui.QFont.Bold)
        else:
            option.font.setWeight(QtGui.QFont.Normal)
        painter.setPen(self.gridColor)
        painter.drawRect(option.rect)
        painter.restore()
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)


class ComboBoxGridDelegate(TodoListChameleonDelegate, ComboBoxGridDelegateMixin):
    """Similar to the grid delegates used in GlobalVariablesModel but for comboboxes"""
    paint = ComboBoxGridDelegateMixin.paint

    def __init__(self, labelDict):
        super().__init__(labelDict)

class PlainGridDelegate(QtWidgets.QStyledItemDelegate, ComboBoxGridDelegateMixin):
    """Draws a grid for default delegate"""
    paint = ComboBoxGridDelegateMixin.paint
    def __init__(self, bold=False):
        self.bold = bold
        super().__init__()
