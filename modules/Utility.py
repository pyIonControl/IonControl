# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from itertools import chain


def unique(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def flatten(listOfLists):
    "Flatten one level of nesting"
    return chain.from_iterable(listOfLists)


def join(s, iterable):
    """join ignoring None values"""
    return s.join((i for i in iterable if i is not None and str(i) != ''))


def indexWithDefault(itemList, item, default=-1):
    """Return the index of item in itemList if it's present, otherwise -1"""
    return itemList.index(item) if item in itemList else default
