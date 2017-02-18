# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from functools import partial

from PyQt5 import QtGui, QtCore, QtWidgets

from GlobalVariables.GlobalVariablesModel import GridDelegateMixin
from modules.PyqtUtility import BlockSignals


class ComboBoxDelegateMixin(object):
    def createEditor(self, parent, option, index ):
        """Create the combo box editor"""
        editor = QtWidgets.QComboBox(parent)
        if hasattr(index.model(), 'comboBoxEditable'):
            editor.setEditable(index.model().comboBoxEditable(index))
        choice = index.model().choice(index) if hasattr(index.model(), 'choice') else None
        if choice:
            editor.addItems( choice )
        editor.currentIndexChanged['QString'].connect( partial( index.model().setValue, index ))
        return editor

    def setEditorData(self, editor, index):
        """Set the data in the editor based on the model"""
        value = index.model().data(index, QtCore.Qt.EditRole)
        if value:
            with BlockSignals(editor) as e:
                e.setCurrentIndex( e.findText(value) )

    def setModelData(self, editor, model, index):
        """Set the data in the model based on the editor"""
        value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate, ComboBoxDelegateMixin):
    """Class for combo box editors in models"""
    def __init__(self):
        QtWidgets.QStyledItemDelegate.__init__(self)

    createEditor = ComboBoxDelegateMixin.createEditor
    setEditorData = ComboBoxDelegateMixin.setEditorData
    setModelData = ComboBoxDelegateMixin.setModelData

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class ComboBoxGridDelegateMixin(object):
    """Contains methods for drawing a grid and setting the size in a view. Used as part of a delegate in TodoList."""
    gridColor = QtGui.QColor(25, 25, 25, 255) #dark gray
    def paint(self, painter, option, index):
        """Draw the grid if the node is a data node"""
        model = index.model()
        painter.save()
        painter.setBrush(model.colorData(index)) #references data in model to draw background
        if index.column() == 0:
            option.font.setWeight(QtGui.QFont.Bold)
        else:
            option.font.setWeight(QtGui.QFont.Normal)
        painter.setPen(self.gridColor)
        painter.drawRect(option.rect)
        painter.restore()
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)


class ComboBoxGridDelegate(ComboBoxDelegate, ComboBoxGridDelegateMixin):
    """Similar to the grid delegates used in GlobalVariablesModel but for comboboxes"""
    paint = ComboBoxGridDelegateMixin.paint

    def __init__(self, bold=False):
        self.bold = bold
        super().__init__()

class PlainGridDelegate(QtWidgets.QStyledItemDelegate, ComboBoxGridDelegateMixin):
    """Draws a grid for default delegate"""
    paint = ComboBoxGridDelegateMixin.paint
    def __init__(self, bold=False):
        self.bold = bold
        super().__init__()
