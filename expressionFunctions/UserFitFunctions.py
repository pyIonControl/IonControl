# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import ast
import inspect
from pathlib import Path
from expressionFunctions.UserFuncASTWalker import FitFuncAnalyzer
from fit.FitFunctionBase import FitFunctionBase, ResultRecord
from functools import partial

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
    """Generates Fit Function classes from user-defined fit functions"""
    def __init__(self, name, description, parameterNames, units, enabledParameters, parameterConfidence, parameterBounds, overwrite, func):
        self.fitfunc = func #function to be evaluted for fit
        self.ndefs = self.getOccurences(func) #Calculates number calls to smartstart() and result() to minimize repeated class definitions
        self._functionString = description #description that shows up in FitUi
        self._name = name #name that shows up in FitUi combobox
        self.origin = func.__name__ #used to prevent multiple functions from showing up in metaclass if name is changed
        self.parameterNames = parameterNames #names that show up in FitUi 'Var' fields
        self.smartStartFunc = lambda *args: tuple([0]*len(self.parameterNames))
        self.resultDict = dict() #dictionary that contains information about user-defined Result fields
        self.nparams = func.__code__.co_argcount-1 #number of parameters in fit function not including the dependent variable
        self.units = units if units is not None else [None]*self.nparams #used to specify units on variables
        self._parameterEnabled = enabledParameters if enabledParameters is not None else [True]*self.nparams
        self.parametersConfidence = parameterConfidence if parameterConfidence is not None else [None]*self.nparams #doesn't appear to work
        self.parameterBounds = parameterBounds if parameterBounds is not None else[[None, None] for _ in range(self.nparams)]
        self.smartstartEnabled = False #controls default setting in FitUi
        self.overwrite = overwrite  #if True, will overwrite saved parameter values with those specified in function definition
        self.constructClass(self.fitfunc)

    def constructClass(self, func):
        """This function actually generates the class. If called N times with self.ndefs = N-1,
            it will only call the class constructor on the Nth call."""
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
            """Actual function used for fitting"""
            return func(*args, **kwargs)

        def update(cls, parameters=None):
            """Writes values to Result fields"""
            args = parameters if parameters is not None else cls.parameters
            for resn, resd in cls.resultDict.items():
                cls.results[resn].value = resd['fn'](*args)

        #Generate smart start function with appropriate class parameter
        if self.smartstartEnabled:
            def smartStartValues(cls, xin, yin, parameters, enabled):
                return self.smartStartFunc(xin, yin, parameters, enabled)

        #Construct the class dictionary
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
            return type(name, (FitFunctionBase,), attrs) #generate the class
        self.ndefs -= 1

    # The following @property calls were used to set class defaults before they were
    # included in the decorator. Currently deprecated but might be useful again later
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
        """If name is not set in fitfunc decorator, returns the name of the user-defined function"""
        if self._name is not None:
            return self.name
        return func.__name__

    def getFuncDesc(self, func):
        """If the description field is not set in the fitfunc decorator, this function
           generates a description that matches the return statement"""
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
        """Determines default parameters from default values in the function definition"""
        sg = inspect.signature(func)
        return list(map(lambda x: x.default if x.default is not inspect._empty else 0, sg.parameters.values()))[1:]

    def getFuncParameters(self, func):
        """This function reads parameter names from the function signature in the event that
           the user did not specify parameterNames in the fitfunc decorator"""
        return func.__code__.co_varnames[slice(1, func.__code__.co_argcount)]

    def smartstart(self, func):
        """Decorator for smart start values"""
        self.smartStartFunc = func
        self.smartstartEnabled = True
        self.constructClass(self.fitfunc)

    def result(self, name, defn=None):
        """Decorator for a Result field, defn is used to specify the Definition field of the result"""
        if defn is None:
            defn = ''
        def wrapped(func):
            self.resultDict.update({name: {'fn': func, 'def': defn}})
            self.constructClass(self.fitfunc)
            return func
        return wrapped

    def getOccurences(self, func):
        """Counts the number of instantiations made by the class object, this way if the user specifies
           a smart start function and numerous result fields, the class is constructed only after the last call"""
        fsource = inspect.getfile(func)
        top = ast.parse(Path(fsource).read_text())
        analyzer = FitFuncAnalyzer()
        analyzer.visit(top)
        return len([x for x in analyzer.declist if func.__name__ in x])

