# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from modules.DataChanged import DataChangedS
from collections import ChainMap
import ast
import inspect
from .UserFuncASTWalker import UserFuncAnalyzer

SystemExprFuncs = dict()
UserExprFuncs = dict()
ExpressionFunctions = ChainMap(UserExprFuncs, SystemExprFuncs)
NamedTraceDict = dict()
ExprFunUpdate = DataChangedS()
NamedTraceUpdate = DataChangedS()

def exprfunc(wrapped):
    fname = wrapped.__name__
    if fname in SystemExprFuncs:
        logging.getLogger(__name__).error("Function '{0}' is already defined as an expression function!".format(fname))
    else:
        SystemExprFuncs[fname] = wrapped
    return wrapped

def NamedTrace(*args, col='y'):
    """NamedTrace(tracename, Line, col='y')
    NamedTrace(parentname, childname, Line, col='y')

    Gets an element from a named trace. If first input method is
    used, tracename must be of the format "parentname_childname"

    Args:
        tracename (str): "parentname_childname" of Named Trace or
                                just the root name if no children exist
        parentname (str): name of Named Trace parent
        childname (str): name of sub trace
        Line (int): index of subtrace to be returned.
        col (str): look up x or y column, takes 'x' or 'y'

    Returns:
        float

    """
    argmapping = list(map(type, args))
    if argmapping == [str, str, int]:
        tracename = args[0]+'_'+args[1]
        Line = args[2]
        if col == 'x':
            return NamedTraceDict[tracename].content.x[Line]
        return NamedTraceDict[tracename].content.y[Line]
    if argmapping == [str, int]:
        tracename = args[0]
        Line = args[1]
        if col == 'x':
            return NamedTraceDict[tracename].content.x[Line]
        return NamedTraceDict[tracename].content.y[Line]
    if argmapping == [str] or argmapping == [str, type(None)]:
        tracename = args[0]
        if col == 'x':
            return NamedTraceDict[tracename].content.x
        return NamedTraceDict[tracename].content.y
    if argmapping == [str, str] or argmapping == [str, str, type(None)]:
        tracename = args[0]+'_'+args[1]
        if col == 'x':
            return NamedTraceDict[tracename].content.x
        return NamedTraceDict[tracename].content.y

def userfunc(func):
    func.__globals__['NamedTrace'] = NamedTrace
    UserFuncCls(func)
    return func

class UserFuncCls:
    def __init__(self, func):
        self.setMissingAttributes(func)
        self._default = func
        self.deps = self.findDeps()
        self.sig = inspect.signature(func)
        UserExprFuncs[func.__name__] = self

    def setMissingAttributes(self, func):
        overwrittenAttrs = {'__doc__'}
        attrlist = set(dir(func)) - set(dir(self)) | overwrittenAttrs
        for attr in attrlist:
            setattr(self, attr, getattr(func, attr))

    def findDeps(self):
        top = ast.parse(inspect.getsource(self._default))
        analyzer = UserFuncAnalyzer()
        analyzer.visit(top)
        return analyzer.ntvar

    def __call__(self, *args, **kwargs):
        return self._default(*args, **kwargs)

