# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtCore, QtWidgets
from .MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegateMixin
from .ComboBoxDelegate import ComboBoxDelegateMixin
from modules.enum import enum

ModeTypes = enum('ComboBox', 'Magnitude')

class CamelionDelegate(QtWidgets.QStyledItemDelegate, ComboBoxDelegateMixin, MagnitudeSpinBoxDelegateMixin):
    """Class for combo box editors in models"""
    def __init__(self, emptyStringValue=0):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.mode = ModeTypes.Magnitude
        self.globalDict = dict()
        self.emptyStringValue = emptyStringValue
        
    def createEditor(self, parent, option, index):
        """Create the combo box editor"""
        choice = index.model().choice(index) if hasattr(index.model(), 'choice') else None
        if choice is not None:
            self.mode = ModeTypes.ComboBox
            return ComboBoxDelegateMixin.createEditor(self, parent, option, index)
        else:
            self.mode = ModeTypes.Magnitude
            return MagnitudeSpinBoxDelegateMixin.createEditor(self, parent, option, index)

    def setEditorData(self, editor, index):
        """Set the data in the editor based on the model"""
        if self.mode == ModeTypes.ComboBox:
            ComboBoxDelegateMixin.setEditorData(self, editor, index)
        else:
            MagnitudeSpinBoxDelegateMixin.setEditorData(self, editor, index)

    def setModelData(self, editor, model, index):
        """Set the data in the model based on the editor"""
        if self.mode == ModeTypes.ComboBox:
            ComboBoxDelegateMixin.setModelData(self, editor, model, index)
        else:
            MagnitudeSpinBoxDelegateMixin.setModelData(self, editor, model, index)
         
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


