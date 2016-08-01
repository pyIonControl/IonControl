# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore


class DataChanged( QtCore.QObject ):
    dataChanged = QtCore.pyqtSignal( object, object )
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)


class DataChangedS(QtCore.QObject):
    dataChanged = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)