# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!
import asyncio

import time

import functools

from PyQt5.QtCore import pyqtSlot
from PyQt5.uic import loadUiType
from PyQt5 import QtCore, QtGui, QtWidgets
from quamash import QEventLoop

uipath = 'untitled.ui'
Form, Base = loadUiType(uipath)

def ensure(func):
    def f(*args, **kwargs):
        asyncio.ensure_future(func(*args, **kwargs))
    return f


class Ui(Form, Base):
    def __init__(self, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.value = 0
        self.can_do_work = True
        self.work_future = None

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.pushButton.clicked.connect(self.onClicked)
        self.workButton.clicked.connect(self.onDoWork)
        self.cancelButton.clicked.connect(self.onCancel)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(self.value)

    def onClicked(self):
        self.value += 1
        self.progressBar.setValue(self.value)

    def onDoWork(self):
        if self.work_future is None:
            self.can_do_work = False
            asyncio.ensure_future(self.doWork())
        else:
            print("already running")

    def done(self):
        print("done.")

    def onCancel(self):
        pass

    async def doWork(self):
        print("worker started")
        for i in range(10):
            await asyncio.sleep(1)
            self.onClicked()
        self.can_do_work = True


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)  # NEW must set the event loop

    MainWindow = QtWidgets.QMainWindow()
    ui = Ui()
    ui.setupUi(ui)
    ui.show()
    with loop:
        loop.run_forever()

