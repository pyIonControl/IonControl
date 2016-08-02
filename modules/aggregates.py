# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

def max_iterable(iterable):
    """return max of iterable, return None if empty"""
    try:
        mymax = max(iterable)
    except ValueError:
        return None
    return mymax


def min_iterable(iterable):
    """return min of iterable, return None if empty"""
    try:
        mymin = min(iterable)
    except ValueError:
        return None
    return mymin

