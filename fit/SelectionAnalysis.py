# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from .FitFunctionBase import FitFunctionBase
import numpy

class SelectLast(FitFunctionBase):
    name = "SelectLastValue"
    functionString =  'Choose last value'
    parameterNames = [ 'value' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [0.0]
        self.startParameters = [0.0]
        
    def residuals(self, p, y, x, sigma):
        value = self.allFitParameters(p)
        if sigma is not None:
            return (y-value)/sigma
        else:
            return y-value
        
    def value(self,x,p=None):
        v,  = self.parameters if p is None else p
        return numpy.array( [v for _ in range(len(x))] )

    def leastsq(self, x, y, parameters=None, sigma=None, filt=None):
        # TODO: need to honor filtering
        if parameters is None:
            parameters = [float(param) for param in self.startParameters]
        self.parameters = [ y[-1] ]
        return self.parameters

class SelectMax(FitFunctionBase):
    name = "SelectMaxValue"
    functionString =  'Choose max value'
    parameterNames = [ 'xAtMaxValue', 'max' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [0.0, 0.0]
        self.startParameters = [0.0, 0.0]

    def value(self,x,p=None):
        v,m  = self.parameters if p is None else p
        return numpy.array( [m for _ in range(len(x))] )

    def leastsq(self, x, y, parameters=None, sigma=None, filt=None):
        # TODO: Need to honor filtering
        if parameters is None:
            parameters = [float(param) for param in self.startParameters]
        self.parameters = [x[numpy.argmax(y)], numpy.max(y)]
        return self.parameters