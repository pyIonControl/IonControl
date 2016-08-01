# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from PyQt5 import QtCore, QtWidgets
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegateMixin
from uiModules.ComboBoxDelegate import ComboBoxDelegateMixin
from uiModules.MultiSelectDelegate import MultiSelectDelegateMixin

class ParameterTableDelegate(QtWidgets.QStyledItemDelegate, MagnitudeSpinBoxDelegateMixin, ComboBoxDelegateMixin, MultiSelectDelegateMixin):
    buttonClicked = QtCore.pyqtSignal(object)
    def __init__(self, globalDict=None, emptyStringValue=0):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.globalDict = globalDict if globalDict is not None else dict()
        self.emptyStringValue = emptyStringValue
        self.pressed = dict()

    def createEditor(self, parent, option, index):
        """Create the combo box editor"""
        dataType = index.model().parameterDict.at(index.row()).dataType
        if dataType == 'magnitude':
            return MagnitudeSpinBoxDelegateMixin.createEditor(self, parent, option, index)
        elif dataType == 'str':
            return QtWidgets.QLineEdit(parent)
        elif dataType == 'select':
            return ComboBoxDelegateMixin.createEditor(self, parent, option, index)
        elif dataType == 'multiselect':
            return MultiSelectDelegateMixin.createEditor(self, parent, option, index)
        elif dataType == 'bool':
            return

    def setEditorData(self, editor, index):
        """Set the data in the editor based on the model"""
        dataType = index.model().parameterDict.at(index.row()).dataType
        if dataType == 'magnitude':
            MagnitudeSpinBoxDelegateMixin.setEditorData(self, editor, index)
        elif dataType == 'str':
            text = index.model().data(index, QtCore.Qt.EditRole)
            editor.setText(text)
        elif dataType == 'select':
            ComboBoxDelegateMixin.setEditorData(self, editor, index)
        elif dataType == 'multiselect':
            MultiSelectDelegateMixin.setEditorData(self, editor, index)
        elif dataType == 'bool':
            return

    def setModelData(self, editor, model, index):
        """Set the data in the model based on the editor"""
        dataType = index.model().parameterDict.at(index.row()).dataType
        if dataType == 'magnitude':
            MagnitudeSpinBoxDelegateMixin.setModelData(self, editor, model, index)
        elif dataType == 'str':
            value = editor.text()
            model.setData(index, value, QtCore.Qt.EditRole)
        elif dataType == 'select':
            ComboBoxDelegateMixin.setModelData(self, editor, model, index)
        elif dataType == 'multiselect':
            MultiSelectDelegateMixin.setModelData(self, editor, model, index)
        elif dataType == 'bool':
            return

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        dataType = index.model().parameterDict.at(index.row()).dataType
        row = index.row()
        if dataType == 'action':
            painter.save()
            opt = QtWidgets.QStyleOptionButton()
            opt.text = index.model().parameterDict.at(index.row()).name
            opt.rect = option.rect
            opt.palette = option.palette
            opt.state = QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_Sunken if self.pressed.get(row, False) else QtWidgets.QStyle.State_Enabled | QtWidgets.QStyle.State_Raised
            QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_PushButton, opt, painter)
            painter.restore()
        else:
            return super(ParameterTableDelegate, self).paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        row = index.row()
        parameter = index.model().parameterDict.at(row)
        dataType = parameter.dataType
        if dataType == 'action':
            if event.type() == QtCore.QEvent.MouseButtonPress:
                self.pressed[row] = True
                self.buttonClicked.emit(parameter)
                return True
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                self.pressed[row] = False
                return True
        return super(ParameterTableDelegate, self).editorEvent(event, model, option, index)