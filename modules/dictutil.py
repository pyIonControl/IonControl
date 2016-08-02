# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


def subdict(fulldict, keys):
    """
    returns the subdict of fulldict containing all entries that are in fulldict and dict
    """
    if keys is not None and fulldict is not None:
        return dict((name, fulldict[name]) for name in keys if name in fulldict)
    else:
        return dict()
    

def setdefault(thisdict, defaultdict):
    for key, value in defaultdict.items():
        thisdict.setdefault(key, value)
    return thisdict


def getOrInsert(thisdict, key, default=None):
    thisdict.setdefault(key, default)
    return thisdict[key]
