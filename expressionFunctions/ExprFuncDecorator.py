# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from modules.DataChanged import DataChangedS
from collections import ChainMap
import functools

SystemExprFuncs = dict()
UserExprFuncs = dict()
#ExpressionFunctions = dict()
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
    if len(args) == 2:
        tracename = args[0]
        Line = args[1]
    elif len(args) == 3:
        tracename = args[0]+'_'+args[1]
        Line = args[2]
    if col == 'x':
        return NamedTraceDict[tracename].content.x[Line]
    return NamedTraceDict[tracename].content.y[Line]

def userfunc(wrapped):
    fname = wrapped.__name__
    g = wrapped.__globals__
    g['NamedTrace'] = NamedTrace
    UserExprFuncs[fname] = wrapped
    return wrapped

