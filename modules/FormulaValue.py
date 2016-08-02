# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from .Expression import Expression
from PyQt5 import QtCore

class FormulaValue(object):
    expression = Expression()
    valueChanged = QtCore.pyqtSignal( object )
    def __init__(self, formula, globalVariables, signal=None ):
        self._formula = formula
        self._globalVariables = globalVariables
        if signal is not None:
            signal.connect( self.onGlobalChanged )
        self._value = None
        self._dependencies = set()
        self.evaluate()
            
    def onGlobalChanged(self, name):
        if name in self._dependencies:
            self.evaluate()
            
    def evaluate(self):
        value, self._dependencies = self.expression.evaluate(self._formula, self._globalVariables, True, False) if self._formula else None, set()
        if value != self._value:
            self.valueChanged.emit( value )
        self._value = value
            
    @property
    def value(self):
        return self._value
    
    @property
    def formula(self):
        return self._formula
    
    @formula.setter
    def formula(self, formula):
        if formula != self._formula:
            self._formula = formula
            self.evaluate()


if __name__=="__main__":
    pass
