# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy


def rollingUpdate(a:numpy.array, v:float, maxLength=0):
    if maxLength == len(a):
        a[0] = v
        a = numpy.roll(a, -1)
        return a
    if maxLength == 0 or len(a) < maxLength:
        return numpy.append(a, v)
    if len(a) > maxLength:
        return numpy.append(a[-maxLength+1:], v)

