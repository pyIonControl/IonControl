from PyQt5 import QtCore

class qtHelper(QtCore.QObject):
    newData = QtCore.pyqtSignal(object, object)
    def __init__(self):
        super(qtHelper, self).__init__()
