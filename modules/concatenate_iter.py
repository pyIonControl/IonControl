# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

def interleave_iter(*iterables):
    """Interleave elements from iterables, finish when first iterable is exhausted"""
    iterlist = [iter(a) for a in iterables if a is not None]
    while True:
        try:
            for it in iterlist:
                yield next(it)
        except StopIteration:
            return


def concatenate_iter(*iterables):
    """concatenate elements from iterators"""
    iterlist = (iter(a) for a in iterables if a is not None)
    for it in iterlist:
        try:
            while True:
                yield next(it)
        except StopIteration:
            pass
    return
