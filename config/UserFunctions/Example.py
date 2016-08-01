#Example.py created 2016-07-19 17:18:20.418809
# 
#       This file demonstrates how to make user-defined functions. All user-defined functions must be decorated
#       by @userfunc in order to be recognized in an expression field. Any function that is decorated by @userfunc
#       that shows up in a .py file in the UserFunctions directory (or any subdirectory therein) will be immediately
#       accessible in an expression field once the file is saved.  The expression field below is simply for testing
#       functions during development.

from expressionFunctions.ExprFuncDecorator import userfunc, NamedTraceDict
import math

@userfunc
def root(x, pow=2):
    """Example of a user-defined function that takes the nth root (determined by
       pow) of a number"""
    return x**(1/pow)

@userfunc
def namedTraceLookup(tracename, Line):
    """Example of how the traceLookup function works in order to retrieve a value
       from a NamedTrace object."""
    return NamedTraceDict[tracename].content.y[Line]

@userfunc
def userVoltageArray(tracename, Line):
    """Example of the voltageArray function for use in localAdjustVoltage fields.
       A function is passed to the gui which looks up the appropriate line when 
       calculating shuttling data. The default display value is determined from 
       the Line variable. This particular function looks up the value in a named 
       trace and interpolates between the closest indices of the array corresponding
       to the voltage line."""
    def va(line=Line):
        left = int(math.floor(line))
        right = int(math.ceil(line))
        convexc = line - left
        return namedTraceLookup(tracename, left)*(1-convexc) + \
               namedTraceLookup(tracename, right)*convexc
    return va







