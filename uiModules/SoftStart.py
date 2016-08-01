# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import math

class SoftStart(object):
    name = ""
    def start(self, edge):
        return
        yield
    
    def stop(self, edge):
        return
        yield

    def effectiveLength(self, length):
        return 0

class SinSqStart(object):
    name = "Sine square"
    
    def start(self, edge ):
        N = edge.startLength * 2
        n = 0
        while n<N:
            yield edge.startLine + (edge.centralStartLine-edge.startLine)*2*(n/(2*float(N))-math.sin(math.pi*n/float(N))/(2*math.pi))
            n += 1
    
    def stop(self, edge ):
        N = edge.stopLength * 2
        n = 1
        while n<=N:
            yield edge.centralStopLine + (edge.stopLine-edge.centralStopLine)*2*(n/(2*float(N))+math.sin(math.pi*n/float(N))/(2*math.pi))
            n += 1
    
    def effectiveLength(self, length):
        return 2*length

class LinearStart(object):
    name = "Linear"
    
    def start(self, edge ):
        N = edge.startLength * 2
        n = 0
        while n<N:
            yield edge.startLine + (edge.centralStartLine-edge.startLine)*(n**2/float(N)**2)
            n += 1
    
    def stop(self, edge ):
        N = edge.stopLength * 2
        n = 1
        while n<=N:
            yield edge.centralStopLine + (edge.stopLine-edge.centralStopLine)*(2*n/float(N)-n**2/float(N)**2)
            n += 1
    
    def effectiveLength(self, length):
        return 2*length

StartTypes = { "": SoftStart, SinSqStart.name: SinSqStart, LinearStart.name: LinearStart }
