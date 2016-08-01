# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
def zeroCrossings( xarray, yarray, value=0 ):
    """return the x values of value crossings of the y values"""
    if len(xarray)<=2 and len(yarray)<=2:
        return None
    crossings = list()
    xiter, yiter = iter(xarray), iter(yarray)
    oldx, oldy = next(xiter), next(yiter)
    for x, y in zip(xiter, yiter):
        if oldy<value != y<value:
            crossings.append( (x*oldy - oldx*y)/(oldy-y) )
    return crossings
        