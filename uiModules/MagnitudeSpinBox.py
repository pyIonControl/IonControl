# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

"""
A QSpinBox for Physical quantities. It accepts for example "10 MHz"
Features are: up-down arrows will increase/decrease the digit left to the cursor position
"""

from math import copysign

import PyQt5.uic
from PyQt5 import QtGui, QtCore, QtWidgets

import logging
from modules import Expression
from modules import MagnitudeParser
from modules.quantity import Q, is_Q

debug = False


class DimensionMismatch(Exception):
    pass


class MagnitudeSpinBox(QtWidgets.QAbstractSpinBox):
    valueChanged = QtCore.pyqtSignal(object)
    textValueChanged = QtCore.pyqtSignal(object)
    expression = Expression.Expression()

    def __init__(self, parent=None, globalDict=None, valueChangedOnEditingFinished=True, emptyStringValue=0):
        super(MagnitudeSpinBox, self).__init__(parent)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        if valueChangedOnEditingFinished:
            self.editingFinished.connect(self.onEditingFinished)
        self.redTextPalette = QtGui.QPalette()
        self.redTextPalette.setColor(QtGui.QPalette.Text, QtCore.Qt.red)
        self.orangeTextPalette = QtGui.QPalette()
        self.orangeTextPalette.setColor(QtGui.QPalette.Text, QtGui.QColor(0x7d, 0x05, 0x52))
        self.blackTextPalette = QtGui.QPalette()
        self.blackTextPalette.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
        self._dimension = None  # if not None enforces the dimension
        self.globalDict = globalDict if globalDict is not None else dict()
        self.emptyStringValue = emptyStringValue

    @property
    def dimension(self):
        return self._dimension

    @dimension.setter
    def dimension(self, dim):
        if is_Q(dim) or dim is None:
            self._dimension = dim
        else:
            self._dimension = Q(0, dim)

    def validate(self, inputstring, pos):
        try:
            value = self.expression.evaluateAsMagnitude(inputstring, self.globalDict)
            if self._dimension is not None and value.dimensionality != self._dimension.dimensionality:
                self.lineEdit().setPalette(self.orangeTextPalette)
                return (QtGui.QValidator.Intermediate, inputstring, pos)
            else:
                self.lineEdit().setPalette(self.blackTextPalette)
                return (QtGui.QValidator.Acceptable, inputstring, pos)
        except Exception:
            self.lineEdit().setPalette(self.redTextPalette)
            return (QtGui.QValidator.Intermediate, inputstring, pos)

    def stepBy(self, steps):
        try:
            lineEdit = self.lineEdit()
            value, delta, pos, decimalpos, prec = MagnitudeParser.parseDelta(lineEdit.text(), lineEdit.cursorPosition())
            newvalue = value + (steps * delta)
            newtext = format(newvalue, "~.{}f".format(prec))
            self.lineEdit().setText(newtext)
            value, delta, _, newdecimalpos, prec = MagnitudeParser.parseDelta(newtext, lineEdit.cursorPosition())
            lineEdit.setCursorPosition(pos + newdecimalpos - decimalpos)
            self.valueChanged.emit(newvalue)
        except Exception as e:
            print(e)
            pass  # logging.getLogger(__name__).exception(e)

    def interpretText(self):
        logging.getLogger(__name__).debug("interpret text")

    def fixup(self, inputstring):
        logging.getLogger(__name__).debug("fixup '{0}'".format(inputstring))

    def stepEnabled(self):
        return QtWidgets.QAbstractSpinBox.StepUpEnabled | QtWidgets.QAbstractSpinBox.StepDownEnabled

    def value(self):
        try:
            text = str(self.lineEdit().text()).strip()
            if len(text) > 0:
                value = self.expression.evaluateAsMagnitude(text, self.globalDict)
                if self._dimension is not None and value.dimensionality != self._dimension.dimensionality:
                    raise DimensionMismatch("Got unit '{0}' expected '{1}'".format(value.dimensionality, self._dimension.dimensionality))
            else:
                value = self.emptyStringValue
        except Exception as e:
            self.lineEdit().setPalette(self.redTextPalette)
            logging.getLogger(__name__).exception("value")
            raise e
        self.lineEdit().setPalette(self.blackTextPalette)
        return value

    def text(self):
        return str(self.lineEdit().text()).strip()

    def setText(self, string):
        cursorpos = self.lineEdit().cursorPosition()
        self.lineEdit().setText(string)
        self.lineEdit().setCursorPosition(cursorpos)

    def setValue(self, value):
        cursorpos = self.lineEdit().cursorPosition()
        self.lineEdit().setText(str(value))
        self.lineEdit().setCursorPosition(cursorpos)

    def onEditingFinished(self):
        self.textValueChanged.emit(self.text())
        self.valueChanged.emit(self.value())

    def sizeHint(self):
        fontMetrics = QtGui.QFontMetrics(self.font())
        size = fontMetrics.boundingRect(self.lineEdit().text()).size()
        size += QtCore.QSize(8, 0)
        return size

    def wheelEvent(self, wheelEvent):
        self.stepBy(copysign(1, wheelEvent.angleDelta().y()))
        wheelEvent.accept()


if __name__ == "__main__":
    debug = True
    TestWidget, TestBase = PyQt5.uic.loadUiType(r'..\ui\MagnitudeSpinBoxTest.ui')


    class TestUi(TestWidget, TestBase):
        def __init__(self):
            TestWidget.__init__(self)
            TestBase.__init__(self)

        def setupUi(self, parent):
            super(TestUi, self).setupUi(parent)
            self.updateButton.clicked.connect(self.onUpdate)
            #self.magnitudeSpinBox.dimension = Q(1, "MHz")

        def onUpdate(self):
            self.lineEdit.setText(str(self.magnitudeSpinBox.value()))


    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = TestUi()
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
