# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore

from GlobalVariables.GlobalOutputChannel import GlobalOutputChannel
from externalParameter.persistence import DBPersist
from externalParameter.decimation import StaticDecimation
from modules.quantity import is_Q, Q
from collections import deque, MutableMapping
import lxml.etree as ElementTree
from modules.MagnitudeParser import parse
from expressionFunctions.ExprFuncDecorator import ExprFunUpdate, NamedTraceUpdate, SystemExprFuncs, \
                                                  UserExprFuncs, NamedTraceDict
import time

class GlobalVariablesException(Exception):
    pass


class GlobalVariable(QtCore.QObject):
    """Class for encapsulating a global variable.

    Attributes:
        valueChanged (PyQt signal): emitted when value is changed, with signature (name, new-value, origin-of-change)
        decimation (StaticDecimation): takes care of saving globals to database every 10 seconds
        history (deque): history of the last 10 values the global has been set to
        _value (magnitude): the global's value, accessed via 'value' property
        _name (str): the global's name, accessed via 'name' property
        categories (list[str]): the global's cateogires
        """
    valueChanged = QtCore.pyqtSignal(object, object, object)
    persistSpace = 'globalVar'
    persistence = DBPersist()

    def __init__(self, name, value=Q(0), categories=None):
        super(GlobalVariable, self).__init__()
        self.decimation = StaticDecimation(Q(10, 's'))
        self.history = deque(maxlen=10)
        self._value = value
        self._name = name
        self.categories = categories

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newvalue):
        """set the value and record the change"""
        if isinstance(newvalue, tuple):
            v, o = newvalue
        else:
            v, o = newvalue, None
        if self._value != v or not (type(self._value) is type(v)) or (is_Q(v) and (type(self._value.m) is type(v.m))):
            self._value = v
            self.valueChanged.emit(self.name, v, o)
            self.history.appendleft((v, time.time(), o))
            if o is not None:
                self.persistCallback((time.time(), v, None, None))
            else:
                self.decimation.decimate(time.time(), v, self.persistCallback)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, newname):
        """set the name and record the change in the database"""
        self._name, oldname = newname, self._name
        self.persistence.rename(self.persistSpace, oldname, newname)

    def __getstate__(self):
        return self._name, self._value, self.categories, self.history

    def __setstate__(self, state):
        super(GlobalVariable, self).__init__()
        self.decimation = StaticDecimation(Q(10, 's'))
        self._name, self._value, self.categories, self.history = state

    def persistCallback(self, data):
        time, value, minval, maxval = data
        unit = None
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
        self.persistence.persist(self.persistSpace, self.name, time, value, minval, maxval, unit)

    def toXmlElement(self, element):
        e = ElementTree.SubElement(element, "GlobalVariable", attrib={'type': 'Magnitude', 'name':self._name, 'categories':", ".join(self.categories) if self.categories else ''})
        e.text = repr(self._value)

    @classmethod
    def fromXmlElement(cls, element):
        categories = [s.strip(" ") for s in element.attrib['categories'].split(",")]
        return GlobalVariable(element.attrib['name'], parse(element.text), categories)


class GlobalVariablesLookup(MutableMapping):
    """Class for providing a view into the global variables.

    globalDict is a dict which maps a name to a GlobalVariable class object. GlobalVariablesLookup acts as a dict which maps
    a name to the value of said global variable, instead of to the class object itself, thereby providing controlled access to
    the global variable objects themselves. This is used everywhere in the program with the exception of the global variables
    control structures themselves.
    """
    def __init__(self, globalDict):
        self.globalDict = globalDict
        self.exprFuncsChanged = ExprFunUpdate.dataChanged

    def __getitem__(self, key):
        return self.globalDict[key].value

    def __setitem__(self, key, value):
        self.globalDict[key].value = value

    def __delitem__(self, key):
        raise GlobalVariablesException("Cannot delete globals via the GlobalVariablesLookup class")

    def __len__(self):
        return len(self.globalDict)

    def __contains__(self, x):
        return x in self.globalDict

    def __iter__(self):
        return self.globalDict.__iter__()

    def valueChanged(self, key):
        if key in UserExprFuncs or key in SystemExprFuncs:
            return ExprFunUpdate.dataChanged
        elif key == '__namedtrace__' or '_NT_' in key or key in NamedTraceDict:
            return NamedTraceUpdate.dataChanged
        return self.globalDict[key].valueChanged

    def outputChannels(self):
        self._outputChannels = {key: GlobalOutputChannel(self, key) for key in self.globalDict.keys()}
        return self._outputChannels

