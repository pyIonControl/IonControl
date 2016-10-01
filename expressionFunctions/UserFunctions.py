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

localFunctions = { 'round': round,
                   'sqrt':    numpy.sqrt,
                   'trunc':   int,
                   'sin':     math.sin,
                   'cos':     math.cos,
                   'tan':     math.tan,
                   'acos':    math.acos,
                   'asin':    math.asin,
                   'atan':    math.atan,
                   'degrees': math.degrees,
                   'radians': math.radians,
                   'erf':     math.erf,
                   'erfc':    math.erfc,
                   'abs':     abs,
                   'exp':     math.exp,
                   'sign':    sign,
                   'sgn':     sign
                   }

@exprfunc
def traceLookup(tracename, Line):
    return trc.NamedTraceDict[tracename].content.y[Line]

@exprfunc
def voltageArray(tracename, Line):
    def va(line=Line):
        left = int(math.floor(line))
        right = int(math.ceil(line))
        convexc = Line - left
        return traceLookup(tracename, left)*(1-convexc) + traceLookup(tracename, right)*convexc
    return va


