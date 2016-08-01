# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from PyQt5 import QtCore, QtGui, QtWidgets
from functools import partial

class MultiSelectDelegateMixin(object):
    """Mixin delegate for selecting multiple options from a list."""
    def createEditor(self, parent, option, index ):
        """Create the editor as a QToolButton with a menu containing a set of actions which correspond to the list of options."""
        editor = QtWidgets.QToolButton(parent)
        self.toolMenu = QtWidgets.QMenu(parent)
        self.selections = set()
        choices = index.model().choice(index)
        for choice in choices:
            checkBox = QtWidgets.QCheckBox(choice, self.toolMenu)
            checkableAction = QtWidgets.QWidgetAction(self.toolMenu)
            checkableAction.setText(choice)
            checkableAction.setDefaultWidget(checkBox)
            self.toolMenu.addAction(checkableAction)
            checkBox.setCheckable(True)
            checkBox.clicked.connect(partial(self.updateSelection, checkBox.text()))
        editor.setMenu(self.toolMenu)
        editor.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.toolMenu.aboutToHide.connect(partial(self.updateModel, index))
        return editor

    def updateSelection(self, text, checked):
        self.selections.add(text) if checked else self.selections.discard(text)

    def updateModel(self, index):
        selections = sorted(list(self.selections))
        index.model().setData(index, selections, QtCore.Qt.EditRole)

    def setEditorData(self, editor, index):
        """Set the editor actions to be checked based on the model data, and set the editor text to the options already selected."""
        self.selections = set(index.data(QtCore.Qt.EditRole))
        text = index.data(QtCore.Qt.DisplayRole)
        editor.setText(text)
        for action in editor.menu().actions():
            checked = action.text() in self.selections
            action.defaultWidget().setChecked(checked)

    def setModelData(self, editor, model, index):
        """This default function is not used. Rather, selectionChecked is used to set the model data in response to a selection."""
        pass


class MultiSelectDelegate(QtWidgets.QStyledItemDelegate, MultiSelectDelegateMixin):
    """Delegate for selecting multiple options from a list."""
    def __init__(self):
        QtWidgets.QStyledItemDelegate.__init__(self)

    createEditor = MultiSelectDelegateMixin.createEditor
    setEditorData = MultiSelectDelegateMixin.setEditorData
    setModelData = MultiSelectDelegateMixin.setModelData

    def updateEditorGeometry(self, editor, option, index):
        """Set the toolbutton shape to match the size of the cell in the view."""
        editor.setGeometry(option.rect)