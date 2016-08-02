# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os.path


def bits(number, length=None):
    "yield the bits of a number"
    if length is not None:
        for i in range(length):
            yield number & 1
            number >>= 1
    else:
        while number:
            yield number & 1
            number >>= 1


def path_iter_right(pathname):
    base, end = os.path.split(pathname)
    yield end
    while end:
        base, end = os.path.split(base)
        yield end


def first(iterable, default=None):
    if iterable:
        for item in iterable:
            return item
    return default