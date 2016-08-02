from PyQt5.QtWidgets import QLabel
from PyQt5 import QtCore
from modules.quantity import is_Q


class NumericLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._precision = None
        self._value = None
        self.formatStrQ = "{:~}"
        self.formatStr = "{}"

    @property
    def precision(self):
        return self._precision

    @precision.setter
    def precision(self, prec):
        self._precision = prec
        self.formatStrQ = "{{:~.{0}f}}".format(int(prec)) if prec is not None else "{:~}"
        self.formatStr = "{{:.{0}f}}".format(int(prec)) if prec is not None else "{}"

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v
        if v is None:
            self.setText("None")
        elif is_Q(v):
            self.setText(self.formatStrQ.format(v))
        else:
            self.setText(self.formatStr.format(v))

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Plus:
            self.precision = self.precision + 1 if self.precision is not None else 1
        elif event.key() == QtCore.Qt.Key_Minus:
            self.precision = self.precision - 1 if self.precision > 0 else None
        else:
            super().keyReleaseEvent(event)
