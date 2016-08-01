# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore


class KeyFilter(QtCore.QObject):
    keyPressed = QtCore.pyqtSignal()
    
    def __init__(self,key,parent=None):
        QtCore.QObject.__init__(self, parent)
        self.key = key
    
    def eventFilter(self, obj, event):
        if event.type()==QtCore.QEvent.KeyRelease and event.key()==self.key:
            self.keyPressed.emit()
            return True
        return False

class KeyListFilter(QtCore.QObject):
    keyPressed = QtCore.pyqtSignal( object )
    controlKeyPressed = QtCore.pyqtSignal( object )
    
    def __init__(self,keys,controlKeys=None,parent=None):
        QtCore.QObject.__init__(self, parent)
        self.keys = keys
        self.alt = False
        self.shift = False
        self.control = False
        self.controlKeys = controlKeys
    
    def eventFilter(self, obj, event):
        if event.type()==QtCore.QEvent.KeyPress:
            if event.key() in self.keys:
                self.keyPressed.emit(event.key())
                return True
            if self.control and self.controlKeys and event.key() in self.controlKeys:
                self.controlKeyPressed.emit(event.key())
                return True
            if event.key() == QtCore.Qt.Key_Alt:
                self.alt = True
            elif event.key() == QtCore.Qt.Key_Control:
                self.control = True
            elif event.key() == QtCore.Qt.Key_Shift:
                self.shift = True
        if event.type()==QtCore.QEvent.KeyRelease:
            if event.key() == QtCore.Qt.Key_Alt:
                self.alt = False
            elif event.key() == QtCore.Qt.Key_Control:
                self.control = False
            elif event.key() == QtCore.Qt.Key_Shift:
                self.shift = False     
        return False
