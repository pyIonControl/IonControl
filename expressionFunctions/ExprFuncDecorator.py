# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from modules.DataChanged import DataChangedS
from collections import ChainMap

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

def userfunc(wrapped):
    fname = wrapped.__name__
    UserExprFuncs[fname] = wrapped
    return wrapped
