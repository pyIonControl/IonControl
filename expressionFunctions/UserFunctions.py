# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from expressionFunctions.ExprFuncDecorator import exprfunc, userfunc
import expressionFunctions.ExprFuncDecorator as trc#import NamedTraceDict
import math

# tempfun, addtwo and kwfun are just dummy functions for test purposes
@exprfunc
def tempfun(a):
    return a*2

@exprfunc
def addtwo(a,b):
    return a+b

@exprfunc
def kwfun(a, b, c=1, d=2, f=3, verbose=False):
    if verbose:
        print("a: {}, b: {}, c: {}, d: {}, f: {}, sum: {}".format(a,b,c,d,f,a+b+c+d+f))
        print(type(a+b+c+d+f))
        print(repr(a+b+c+d+f))
    return a+b+c+d+f

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


