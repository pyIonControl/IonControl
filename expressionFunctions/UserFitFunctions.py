import ast
import inspect
from copy import copy, deepcopy
from pathlib import Path
import sys

from expressionFunctions.UserFuncASTWalker import FitFuncAnalyzer
from fit.FitFunctionBase import FitFunctionBase, ResultRecord, fitFunctionMap
#import fit.FitFunctionBase
from functools import wraps, partial

class fitfunc:
    def __init__(self, func):#=None, *, name=None):
        #if func is None:
            #return partial(self.__init__, name=name)
        self.fitfunc = func
        self.ndefs = 0#self.getOccurences(func)
        self._functionString = None
        self._name = None
        self.origin = func.__name__
        self.parameterNames = self.getFuncParameters(func)
        self.smartStartFunc = lambda *args: tuple([0]*len(self.parameterNames))
        self.resultDict = dict()
        self.nparams = len(self.parameterNames)
        self.units = [None]*self.nparams
        self._parameterEnabled = [True]*self.nparams
        self.parametersConfidence = [None]*self.nparams
        self.smartstartEnabled = False
        self.constructClass(self.fitfunc)#, deepcopy(self.smartStartFunc))

    def constructClass(self, func):
        name = self.getName(func)
        functionString = self.getFuncDesc(func)
        parameterNames = self.parameterNames
        parameters = [0]*self.nparams
        origin = self.origin
        slots = []

        def __init__(cls):
            FitFunctionBase.__init__(cls)
            #cls.parameters = [0]*self.nparams
            cls.resultDict = self.resultDict
            cls.units = self.units
            cls.parameterEnabled = self.parameterEnabled
            cls.parametersConfidence = self.parametersConfidence
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
                     parameters=parameters,
                     origin=origin)

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

    def getFuncParameters(self, func):
        return func.__code__.co_varnames[slice(1, func.__code__.co_argcount)]

    def smartstart(self, func):
        self.smartStartFunc = func
        self.smartstartEnabled = True
        self.constructClass(self.fitfunc)#, self.smartStartFunc)

    def result(self, name, defn=None):
        if defn is None:
            defn = ''
        def wrapped(func):
            self.resultDict.update({name: {'fn': func, 'def': defn}})
            self.constructClass(self.fitfunc)#, self.smartStartFunc)
            return func
        return wrapped

    def getOccurences(self, func):
        fsource = inspect.getfile(func)
        top = ast.parse(Path(fsource).read_text())
        analyzer = FitFuncAnalyzer()
        analyzer.visit(top)
        return len([x for x in analyzer.declist if func.__name__ in x])


"""
def classdec(cls):
    for k, v in vars(cls).items():
        if callable(v):
            setattr(cls, key, debug(val))
    return cls

class FitFnMeta(type):
    def __new__(cls, clsname, bases, clsdict):
        clsobj = super().__new__(cls, clsname, bases, clsdict)
        clsobj = classdec(clsobj)
        return clsobj

class fitfunc:
    def __init__(self, func):
        self.fitfunc = func
        self.ndefs = self.getOccurences(func)
        self.parameterNames = self.getFuncParameters(func)
        self.smartStartFunc = lambda *args: tuple([0]*len(self.parameterNames))
        self.resultDict = dict()
        self.nparams = len(self.parameterNames)
        self.constructClass(self.fitfunc, deepcopy(self.smartStartFunc))

    def cls__init__(self, func):
        @wraps(func)
    def constructClass(self, func, smartstart=None):
        name = self.getName(func)
        functionString = self.getFuncDesc(func)
        parameterNames = self.parameterNames
        slots = []

        def __init__(cls):
            FitFunctionBase.__init__(cls)
            cls.parameters = [0]*self.nparams
            cls.resultDict = self.resultDict
            for resn, resd in cls.resultDict.items():
                cls.results[resn] = ResultRecord(name=resn, definition=resd['def'])

        def functionEval(cls, *args, **kwargs):
            return func(*args, **kwargs)

        def update(cls, parameters=None):
            args = parameters if parameters is not None else cls.parameters
            for resn, resd in cls.resultDict.items():
                cls.results[resn].value = resd['fn'](*args)

        if smartstart:
            def smartStartValues(cls, xin, yin, parameters, enabled):
                return smartstart(xin, yin, parameters, enabled)

        attrs = dict(__slots__=tuple(slots),
                     __init__=__init__,
                     name=name,
                     functionEval=functionEval,
                     parameterNames=parameterNames,
                     functionString=functionString)
        if smartstart:
            attrs.update(dict(smartStartValues=smartStartValues))
        if self.resultDict:
            attrs.update(dict(update=update))

        if self.ndefs < 1: #just a trick to prevent multiple updates to metaclass when additional methods are changed
            return type(name, (FitFunctionBase,), attrs)
        self.ndefs -= 1

    def getName(self, func):
        if hasattr(func, 'name'):
            return func.name
        return func.__name__

    def getFuncDesc(self, func):
        if hasattr(func, 'functionString'):
            return func.functionString
        fsource = inspect.getsource(func)
        top = ast.parse(fsource)
        analyzer = FitFuncAnalyzer()
        analyzer.visit(top)
        retlines = analyzer.retlines
        if retlines:
            returnStatement = fsource.splitlines()[max(retlines)-1]
            return returnStatement.lstrip('return ').split('#')[0]
        return ""

    def getFuncParameters(self, func):
        return func.__code__.co_varnames[slice(1, func.__code__.co_argcount)]

    def smartstart(self, func):
        self.smartStartFunc = func
        self.constructClass(self.fitfunc, self.smartStartFunc)

    def result(self, name, defn=None):
        if defn is None:
            defn = ''
        def wrapped(func):
            self.resultDict.update({name: {'fn': func, 'def': defn}})
            self.constructClass(self.fitfunc, self.smartStartFunc)
            return func
        return wrapped

    def getOccurences(self, func):
        fsource = inspect.getfile(func)
        top = ast.parse(Path(fsource).read_text())
        analyzer = FitFuncAnalyzer()
        analyzer.visit(top)
        return len([x for x in analyzer.declist if func.__name__ in x])
"""
