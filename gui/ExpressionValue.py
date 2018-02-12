# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from pint import DimensionalityError

import logging
import expressionFunctions.ExprFuncDecorator as trc# NamedTraceDict
from modules.Expression import Expression
from modules.flatten import flattenAll
from modules.quantity import Q, is_Q
from modules import WeakMethod
from PyQt5 import QtCore
from copy import deepcopy, copy

class ExpressionValueException(Exception):
    pass

class ExpressionValue(QtCore.QObject):
    expression = Expression()
    valueChanged = QtCore.pyqtSignal(object, object, object, object)

    def __init__(self, name=None, globalDict=None, value=Q(0)):
        super(ExpressionValue, self).__init__()
        self._globalDict = globalDict
        self.name = name
        self.func = self._returnVal
        self._string = None
        self._value = value
        self._updateFloatValue()
        self.registrations = list()        # subscriptions to global variable values
        self.dependencies = set()

    def _updateFloatValue(self):
        try:
           self.floatValue = float(self._value)  # cached value as float
        except (DimensionalityError, TypeError):
            self.floatValue = None

    def __getstate__(self):
        return self.name, self._string, self._value
    
    def __setstate__(self, state):
        self.__init__(state[0])
        self._string = state[1]
        self._value = state[2]
        self._updateFloatValue()

    def __eq__(self, other):
        try:
            return other is not None and isinstance(other, ExpressionValue) and \
                   (self.name, self._string, self._value) == (other.name, other._string, other._value)
        except ValueError:
            # catches a rare exception that occurs when comparing quantities with nested iterables
            return other is not None and isinstance(other, ExpressionValue) and \
                   self.name == other.name and self.string == other._string and \
                   all(flattenAll([self._value == other._value]))

    def __ne__(self, other):
        return not self.__eq__(other)

    def _returnVal(self, *args):
        return self._value

    def setDefaultFunc(self):
        self.func = self._returnVal

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
        else:
            if callable(v):
                self._value = v()
                self.func = deepcopy(v)
            else:
                self._value = v
                self.func = self._returnVal
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
            val, dependencies = self.expression.evaluateAsMagnitude(self._string, self._globalDict, listDependencies=True)
            if hasattr(val, 'm') and callable(val.m):
                self.func = deepcopy(val.m)
                if any('NamedTraceDict' in key for key in val.m.__code__.co_names) or \
                   'NamedTrace' in val.m.__code__.co_names:
                    dependencies.add('__namedtrace__')
                    if trc.NamedTraceDict: #hold off if function depends on NamedTraceDict and NamedTraces haven't been loaded
                        self._value = Q(val.m())
                else:
                    self._value = Q(val.m())
            else:
                self._value = val
                self.func = self._returnVal
                for dep in dependencies:
                    if dep in trc.ExpressionFunctions:
                        if 'NamedTrace' in trc.ExpressionFunctions[dep].__code__.co_names or \
                                any('NamedTraceDict' in key for key in trc.ExpressionFunctions[dep].__code__.co_names):
                            dependencies.add('__namedtrace__')
                            break
            self._updateFloatValue()
            self.dependencies = copy(dependencies)
            for dep in dependencies:
                reference = WeakMethod.ref(self.recalculate)
                self._globalDict.valueChanged(dep).connect(reference)
                self.registrations.append((dep, reference))

    @property
    def hasDependency(self):
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
        if name is None or name in self.dependencies:
            if self._string:
                newValue  = self.expression.evaluateAsMagnitude(self._string, self._globalDict)
                if callable(newValue.m):
                    if not (not trc.NamedTraceDict and ('__namedtrace__' in (dep[0] for dep in self.registrations)
                                                            or '_NT_' in (dep[0] for dep in self.registrations))):
                        self.func = deepcopy(newValue.m)
                        self._value = Q(newValue.m())
                    self._updateFloatValue()
                    self.valueChanged.emit(self.name, self._value, self._string, 'recalculate')
                else:
                    self.func = self._returnVal
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
        if self._globalDict is not None:
            result.string = deepcopy(self._string)
            if result._string is None:
                result._value = deepcopy(self._value)
        else:
            result._string = deepcopy(self._string)
            result._value = deepcopy(self._value)
        return result
