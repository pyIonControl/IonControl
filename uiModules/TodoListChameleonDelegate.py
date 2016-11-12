# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from functools import partial

from PyQt5 import QtGui, QtCore, QtWidgets

from GlobalVariables.GlobalVariablesModel import GridDelegateMixin
from modules.PyqtUtility import BlockSignals
from uiModules.ComboBoxDelegate import ComboBoxDelegateMixin
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegateMixin

#ModeTypes = enum('ComboBox', 'Magnitude')

class TodoListChameleonDelegate(QtWidgets.QStyledItemDelegate, ComboBoxDelegateMixin, MagnitudeSpinBoxDelegateMixin):
    """Class for combo box editors in models"""
    def __init__(self):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.globalDict = dict()
        self.emptyStringValue = ''

    def createEditor(self, parent, option, index):
        """Create the combo box editor"""
        model = index.model()
        if model.nodeFromIndex(index).entry.scan != 'Rescan':
            return ComboBoxDelegateMixin.createEditor(self, parent, option, index)
        else:
            return MagnitudeSpinBoxDelegateMixin.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        """Set the data in the editor based on the model"""
        #if self.mode == ModeTypes.ComboBox:
        model = index.model()
        if model.nodeFromIndex(index).entry.scan != 'Rescan':
            ComboBoxDelegateMixin.setEditorData(self, editor, index)
        else:
            MagnitudeSpinBoxDelegateMixin.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        """Set the data in the model based on the editor"""
        #if self.mode == ModeTypes.ComboBox:
        model = index.model()
        if model.nodeFromIndex(index).entry.scan != 'Rescan':
            ComboBoxDelegateMixin.setModelData(self, editor, model, index)
        else:
            MagnitudeSpinBoxDelegateMixin.setModelData(self, editor, model, index)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

#class ComboBoxDelegate(QtWidgets.QStyledItemDelegate, ComboBoxDelegateMixin):
    #"""Class for combo box editors in models"""
    #def __init__(self):
        #QtWidgets.QStyledItemDelegate.__init__(self)
#
    #createEditor = ComboBoxDelegateMixin.createEditor
    #setEditorData = ComboBoxDelegateMixin.setEditorData
    #setModelData = ComboBoxDelegateMixin.setModelData
#
    #def updateEditorGeometry(self, editor, option, index):
        #editor.setGeometry(option.rect)

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

    def __init__(self, bold=False):
        self.bold = bold
        super().__init__()

class PlainGridDelegate(QtWidgets.QStyledItemDelegate, ComboBoxGridDelegateMixin):
    """Draws a grid for default delegate"""
    paint = ComboBoxGridDelegateMixin.paint
    def __init__(self, bold=False):
        self.bold = bold
        super().__init__()
