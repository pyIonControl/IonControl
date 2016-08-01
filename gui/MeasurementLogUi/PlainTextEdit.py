# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtWidgets, QtCore


class PlainTextEdit( QtWidgets.QPlainTextEdit ):
    editingFinished = QtCore.pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        super( PlainTextEdit, self).__init__(*args, **kwargs)
        
    def focusOutEvent(self, focusEvent):
        if self.document().isModified():
            self.editingFinished.emit(self.document())
        return QtWidgets.QPlainTextEdit.focusOutEvent(self, focusEvent)
    
    def setModified(self, modified):
        self.document().setModified( modified )