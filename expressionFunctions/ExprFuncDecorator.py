# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from modules.DataChanged import DataChangedS

ExpressionFunctions = dict()
NamedTraceDict = dict()
ExprFunUpdate = DataChangedS()
NamedTraceUpdate = DataChangedS()

def exprfunc(wrapped):
    fname = wrapped.__name__
    if fname in ExpressionFunctions:
        logging.getLogger(__name__).error("Function '{0}' is already defined as an expression function!".format(fname))
    else:
        ExpressionFunctions[fname] = wrapped
    return wrapped

def userfunc(wrapped):
    fname = wrapped.__name__
    ExpressionFunctions[fname] = wrapped
    return wrapped
