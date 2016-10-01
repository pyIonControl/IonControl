# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from expressionFunctions.ExprFuncDecorator import exprfunc, userfunc
import expressionFunctions.ExprFuncDecorator as trc
import math
import numpy

# constLookup and localFunctions are essentially copies of the lookup tables used in Expression
# this is just to provide data about the builtins that are available in expression fields.
# the functions are imported directly to gain access to the builtin doc strings.

constLookup = ['PI', 'pi', 'E', 'e', 'True', 'False']

# This is just a dummy function for more seamless integration with doc strings
def sign(x):
    """returns 1 if x is greater than 1e-12.
       returns 0 if abs(x) is less than 1e-12.
       returns -1 if x is less than -1e-12."""
    return x

localFunctions = { 'round(x[,n]))': round,
                   'sqrt(x)':    numpy.sqrt,
                   'trunc(x)':   int,
                   'sin(x)':     math.sin,
                   'cos(x)':     math.cos,
                   'tan(x)':     math.tan,
                   'acos(x)':    math.acos,
                   'asin(x)':    math.asin,
                   'atan(x)':    math.atan,
                   'degrees(x)': math.degrees,
                   'radians(x)': math.radians,
                   'erf(x)':     math.erf,
                   'erfc(x)':    math.erfc,
                   'abs(x)':     abs,
                   'exp(x)':     math.exp,
                   'sign(x)':    sign,
                   'sgn(x)':     sign
                   }

@exprfunc
def traceLookup(*args, col='y'):
    """traceLookup(tracename, Line, col='y')
    traceLookup(parentname, childname, Line, col='y')

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
        return trc.NamedTraceDict[tracename].content.x[Line]
    return trc.NamedTraceDict[tracename].content.y[Line]

@exprfunc
def voltageArray(*args, col='y'):
    """voltageArray(tracename, Line, col='y')
    voltageArray(parentname, childname, Line, col='y')

    Gets an element from a named trace and returns an interpolating
    function to a voltage adjust parameter. If first input method is
    used, tracename must be of the format "parentname_childname"

    Args:
        tracename (str): "parentname_childname" of Named Trace or
                                just the root name if no children exist
        parentname (str): name of Named Trace parent
        childname (str): name of sub trace
        Line (int): index of subtrace to be returned.
        col (str): look up x or y column, takes 'x' or 'y'

    Returns:
        function

    """
    if len(args) == 2:
        tracename = args[0]
        Line = args[1]
    elif len(args) == 3:
        tracename = args[0]+'_'+args[1]
        Line = args[2]
    def va(line=Line):
        left = int(math.floor(line))
        right = int(math.ceil(line))
        convexc = Line - left
        return traceLookup(tracename, left, col=col)*(1-convexc) + traceLookup(tracename, right, col=col)*convexc
    return va


