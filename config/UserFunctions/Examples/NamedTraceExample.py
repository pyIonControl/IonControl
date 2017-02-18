#
#       This file demonstrates how to access NamedTrace objects with a user function. Any user function defined
#       with the @userfunc decorator has automatic access to the NamedTrace function with the following signatures
#
#           NamedTrace(tracename, Line=None, col='y')
#       or
#           NamedTrace(parentname, childname, Line=None, col='y')
#
#       The first signature can be used with named traces that don't have any children. But if children exist, the
#       tracename parameter must be set with the format "parentname_childname". Optionally, the parent and child
#       names can be passed as separate arguments as indicated in the second signature. The desired element in the
#       trace is determined with the Line variable. If Line is set to None (or left out of the call entirely) then
#       the entire array is returned. In order to specify the x data in a named trace, the col argument can be
#       specified as col='x'.

import numpy


@userfunc
def TraceOffset(parentname, childname, Line, offset=0, col='y'):
    """
    Adds an offset to a named trace.

    Args:
        parentname (str): Parent name of named trace
        childname (str): Child name of named trace
        Line (int): index of traces at which division is calculated
        offset (num): value to be added to the named trace
        col='y' (str): specifies column, ie 'x' or 'y' for x or y data

    Returns:
        float
    """
    return NamedTrace(parentname, childname, Line, col=col) + offset

@userfunc
def TraceDivider(numeratorTrace, denominatorTrace, Line, col='y'):
    """
    Divides two Named Traces. Trace names are specified with
    the underscore notation "parent_child". The division is
    performed element-wise at an index given by the Line variable.

    Args:
        numeratorTrace (str): trace to be used in the numerator
        denominatorTrace (str): divide by this trace
        Line (int): index of traces at which division is calculated
        col='y' (str): specifies column, ie 'x' or 'y' for x or y data

    Returns:
        float
    """
    numerator = NamedTrace(numeratorTrace, Line, col=col)
    denominator = NamedTrace(denominatorTrace, Line, col=col)
    return numerator / denominator

@userfunc
def TraceStd(parentname, childname, col='y'):
    """
    Returns the standard deviation of a named trace
    Args:
        parentname (str): Parent name of named trace
        childname (str): Child name of named trace
        col='y' (str): specifies column, ie 'x' or 'y' for x or y data

    Returns:
        float
    """
    return numpy.std(NamedTrace(parentname, childname, col='y'))



