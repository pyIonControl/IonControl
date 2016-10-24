import ast
import inspect
from copy import copy, deepcopy
from pathlib import Path
import sys

from expressionFunctions.UserFuncASTWalker import FitFuncAnalyzer
from fit.FitFunctionBase import FitFunctionBase, ResultRecord, fitFunctionMap
from functools import wraps, partial

def fitfunc(func=None, *, name=None, description=None, parameterNames=None, units=None, enabledParameters=None,
            parameterConfidence=None, parameterBounds=None, overwriteDefaults=False):
    """Delegate decorator for FitFunctionFactory. By defining a separate decorator function, decorator can be called
       with or without optional arguments in order to simplify @fitfunc implementation on the user side. This separate
       function is necessary because decorating with the FitFunctionFactory class directly requires a static number
       of input arguments since __init__ must return None"""
    if func is None:
        return partial(fitfunc, name=name, description=description, parameterNames=parameterNames, units=units,
                       enabledParameters=enabledParameters, parameterConfidence=parameterConfidence,
                       parameterBounds=parameterBounds, overwriteDefaults=overwriteDefaults)
    return FitFunctionFactory(name, description, parameterNames, units, enabledParameters, parameterConfidence,
                              parameterBounds, overwriteDefaults, func)

class FitFunctionFactory:
    def __init__(self, name, description, parameterNames, units, enabledParameters, parameterConfidence, parameterBounds, overwrite, func):
        self.fitfunc = func
        self.ndefs = self.getOccurences(func)
        self._functionString = description
        self._name = name
        self.origin = func.__name__
        self.parameterNames = parameterNames
        self.smartStartFunc = lambda *args: tuple([0]*len(self.parameterNames))
        self.resultDict = dict()
        self.nparams = func.__code__.co_argcount-1
        self.units = units if units is not None else [None]*self.nparams
        self._parameterEnabled = enabledParameters if enabledParameters is not None else [True]*self.nparams
        self.parametersConfidence = parameterConfidence if parameterConfidence is not None else [None]*self.nparams
        self.parameterBounds = parameterBounds if parameterBounds is not None else[[None, None] for _ in range(self.nparams)]
        self.smartstartEnabled = False
        self.overwrite = overwrite
        self.constructClass(self.fitfunc)

    def constructClass(self, func):
        name = self.getName(func)
        functionString = self.getFuncDesc(func)
        parameterNames = self.parameterNames if self.parameterNames is not None else self.getFuncParameters(func)
        origin = self.origin
        overwrite = self.overwrite
        slots = []

        def __init__(cls):
            FitFunctionBase.__init__(cls)
            cls.resultDict = self.resultDict
            cls.units = self.units
            cls.parameters = [0]*self.nparams
            cls.parameterEnabled = self.parameterEnabled
            cls.parametersConfidence = self.parametersConfidence
            cls.parameterBounds = self.parameterBounds
            cls.startParameters = self.getDefaults(func)
            for resn, resd in cls.resultDict.items():
                cls.results[resn] = ResultRecord(name=resn, definition=resd['def'])

        def functionEval(cls, *args, **kwargs):
            return func(*args, **kwargs)

        def update(cls, parameters=None):
            args = parameters if parameters is not None else cls.parameters
            for resn, resd in cls.resultDict.items():
                cls.results[resn].value = resd['fn'](*args)

        if self.smartstartEnabled:
            def smartStartValues(cls, xin, yin, parameters, enabled):
                return self.smartStartFunc(xin, yin, parameters, enabled)

        attrs = dict(__slots__=tuple(slots),
                     __init__=__init__,
                     name=name,
                     functionEval=functionEval,
                     parameterNames=parameterNames,
                     functionString=functionString,
                     origin=origin,
                     overwrite=overwrite)

        if self.smartstartEnabled:
            attrs.update(dict(smartStartValues=smartStartValues))
        if self.resultDict:
            attrs.update(dict(update=update))

        if self.ndefs < 1: #just a trick to prevent multiple updates to metaclass when additional methods are changed
            return type(name, (FitFunctionBase,), attrs)
        self.ndefs -= 1

    @property
    def parameterEnabled(self):
        return self._parameterEnabled

    @parameterEnabled.setter
    def parameterEnabled(self, val):
        self._parameterEnabled = val
        self.constructClass(self.fitfunc)

    @property
    def functionString(self):
        return self._functionString

    @functionString.setter
    def functionString(self, s):
        self._functionString = s
        self.constructClass(self.fitfunc)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, s):
        self._name = s
        self.constructClass(self.fitfunc)

    def getName(self, func):
        if self._name is not None:
            return self.name
        return func.__name__

    def getFuncDesc(self, func):
        if self._functionString is not None:
            return self.functionString
        fsource = inspect.getsource(func)
        top = ast.parse(fsource)
        analyzer = FitFuncAnalyzer()
        analyzer.visit(top)
        retlines = analyzer.retlines
        if retlines:
            returnStatement = fsource.splitlines()[max(retlines)-1]
            return returnStatement.lstrip('return ').split('#')[0]
        else:
            return ""

    def getDefaults(self, func):
        sg = inspect.signature(func)
        return list(map(lambda x: x.default if x.default is not inspect._empty else 0, sg.parameters.values()))[1:]

    def getFuncParameters(self, func):
        return func.__code__.co_varnames[slice(1, func.__code__.co_argcount)]

    def smartstart(self, func):
        self.smartStartFunc = func
        self.smartstartEnabled = True
        self.constructClass(self.fitfunc)

    def result(self, name, defn=None):
        if defn is None:
            defn = ''
        def wrapped(func):
            self.resultDict.update({name: {'fn': func, 'def': defn}})
            self.constructClass(self.fitfunc)
            return func
        return wrapped

    def getOccurences(self, func):
        fsource = inspect.getfile(func)
        top = ast.parse(Path(fsource).read_text())
        analyzer = FitFuncAnalyzer()
        analyzer.visit(top)
        return len([x for x in analyzer.declist if func.__name__ in x])

