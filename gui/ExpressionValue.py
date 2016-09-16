# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from pint import DimensionalityError

import logging

from modules.Expression import Expression
from modules.quantity import Q, is_Q
from modules import WeakMethod
from PyQt5 import QtCore
from copy import deepcopy

class ExpressionValueException(Exception):
    pass


class ExpressionValue(QtCore.QObject):
    expression = Expression()
    valueChanged = QtCore.pyqtSignal(object, object, object, object)

    def __init__(self, name=None, globalDict=None, value=Q(0)):
        super(ExpressionValue, self).__init__()
        self._globalDict = globalDict
        self.name = name
        self._string = None
        self._value = value
        self._updateFloatValue()
        self.registrations = list()        # subscriptions to global variable values

    def _updateFloatValue(self):
        try:
           self.floatValue = float(self._value)  # cached value as float
        except (DimensionalityError, TypeError):
            self.floatValue = None

    def __getstate__(self):
        # if statements used when pickling function objects to avoid errors that occur when
        # user functions haven't already been imported.
        if is_Q(self._value):
            if callable(self._value.m):
                return self.name, self._string, Q(self._value.m(), self._value.u)
        elif callable(self._value):
            return self.name, self._string, self._value()
        return self.name, self._string, self._value
    
    def __setstate__(self, state):
        self.__init__( state[0] )
        self._string = state[1]
        self._value = state[2]
        self._updateFloatValue()

    def __eq__(self, other):
        return other is not None and isinstance(other, ExpressionValue) and (self.name, self._string, self._value) == (other.name, other._string, other._value)

    def __ne__(self, other):
        return not self.__eq__(other)
        
    @property
    def globalDict(self):
        return self._globalDict
    
    @globalDict.setter
    def globalDict(self, d):
        self._globalDict = d
        self.string = self._string 
        
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        if isinstance(v, ExpressionValue):
            self._value = v._value
            self.string = v._string
            #raise ExpressionValueException('cannot assign ExpressionValue value to ExpressionValue')
            #logging.getLogger(__name__).error('cannot assign ExpressionValue value to ExpressionValue')
            #v = mg(0)
        else:
            self._value = v
        self._updateFloatValue()
        self.valueChanged.emit(self.name, self._value, self._string, 'value')
        
    @property 
    def string(self):
        return self._string if self._string is not None else str(self._value)
    
    @string.setter
    def string(self, s):
        if self._globalDict is None:
            raise ExpressionValueException("Global dictionary is not set in {0}".format(self.name))
        self._string = s
        for name, reference in self.registrations:
            self._globalDict.valueChanged(name).disconnect(reference)
        self.registrations[:] = []
        if self._string:
            self._value, dependencies = self.expression.evaluateAsMagnitude(self._string, self._globalDict, listDependencies=True)
            self._updateFloatValue()
            for dep in dependencies:
                reference = WeakMethod.ref(self.recalculate)
                self._globalDict.valueChanged(dep).connect(reference)
                self.registrations.append((dep, reference))
                       
    @property
    def hasDependency(self):
        #return self._string is not None
        return len(self.registrations)>0
    
    @property
    def data(self):
        return (self.name, self._value, self._string )
    
    @data.setter
    def data(self, val):
        self.name, self.value, self.string = val
    
    def recalculate(self, name=None, value=None, origin=None, forceUpdate=False):
        if self._globalDict is None:
            raise ExpressionValueException("Global dictionary is not set in {0}".format(self.name))
        if self._string:
            newValue = self.expression.evaluateAsMagnitude(self._string, self._globalDict)
        if newValue != self._value or forceUpdate:
            self._value = newValue
            self._updateFloatValue()
            self.valueChanged.emit(self.name, self._value, self._string, 'recalculate')

    def __hash__(self):
        return hash(self._value)

    def __str__(self):
        return str(self._value)

    def __deepcopy__(self, memo):
        result = ExpressionValue(globalDict=self.globalDict)
        memo[id(self)] = result
        result.name = deepcopy(self.name)
        result._string = deepcopy(self._string)
        result._value = deepcopy(self._value)
        return result
