# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import functools
import random

import numpy

from modules import enum
from modules.concatenate_iter import interleave_iter
from modules.quantity import is_Q, to_Q

ScanType = enum.enum('LinearUp', 'LinearDown', 'Randomized', 'CenterOut', 'LinearUpDown', 'LinearDownUp')

def shuffle( mylist ):
    random.shuffle(mylist)
    return mylist
    
    
def scanspace( start, stop, steps, scanSelect=0 ):
    if scanSelect==0:
        if is_Q(start) and is_Q(stop):
            return list(to_Q(numpy.linspace(start.m, stop.m_as(start.u), steps), start.u))
        return numpy.linspace(start, stop, steps)
    else:
        mysteps = abs(steps) if stop>start else -abs(steps)
        return numpy.arange(start, stop+mysteps//2, mysteps)
        
def shuffled(start, stop, steps, scanSelect ):
    return shuffle(scanspace(start, stop, steps, scanSelect ))
       
def centerOut(start, stop, steps, scanSelect ):
    full = scanspace(start, stop, steps, scanSelect )
    center = len(full)//2
    return list( interleave_iter(full[center:], reversed(full[:center])) )

def upDownUp(start, stop, steps, scanSelect ):
    return numpy.concatenate( (scanspace(start, stop, steps, scanSelect ), scanspace(stop, start, steps, scanSelect ) ))
    
def downUpDown(start, stop, steps, scanSelect ):
    return numpy.concatenate( (scanspace(stop, start, steps, scanSelect ), scanspace(start, stop, steps, scanSelect ) ))    

def scanList( start, stop, steps, scantype=ScanType.LinearUp, scanSelect=0 ): 
    return { ScanType.LinearUp: functools.partial(scanspace, start, stop, steps, scanSelect ),
             ScanType.LinearDown: functools.partial(scanspace, stop, start, steps, scanSelect ),
             ScanType.Randomized: functools.partial(shuffled, stop, start, steps, scanSelect ),
             ScanType.CenterOut: functools.partial(centerOut, start, stop, steps, scanSelect ),
             ScanType.LinearUpDown: functools.partial(upDownUp, start, stop, steps, scanSelect ),
             ScanType.LinearDownUp: functools.partial(downUpDown, start, stop, steps, scanSelect ),
             }.get(scantype, functools.partial(scanspace, start, stop, steps, scanSelect ))()


if __name__ == "__main__":
    from modules.quantity import Q, is_Q, to_Q

    start = Q(12642, 'MHz')
    stop = Q(12652, 'MHz')
    steps = 11
    stepsmag = Q(500, 'kHz')
    
    l = scanList( 0, 10, -1, 1, 1)
    print("expected: [10 9 8 7 6 5 4 3 2 1 0] obtained", l)
    print(scanList( start, stop, stepsmag, 1, 1))
    print(scanList( start, stop, steps))
    print(scanList( start, stop, steps, ScanType.LinearDown))
    print(scanList( start, stop, steps, ScanType.Randomized))
    print(scanList( start, stop, stepsmag, ScanType.LinearUp, 1))
    
    print(shuffle( [1, 2, 3] ))
    print(random.random())

    print(scanList( Q(0), Q(360), Q(10) ))
    print('CenterOut', scanList( 0, 9, 10, ScanType.CenterOut ))
    print('CenterOut', scanList( 0, 10, 11, ScanType.CenterOut ))