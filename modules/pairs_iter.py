# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

def pairs_iter(lst):
    i = iter(lst)
    prev = item = next(i)
    for item in i:
        yield prev, item
        prev = item
