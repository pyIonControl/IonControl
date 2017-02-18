# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy

from .FitFunctionBase import ResultRecord, fitFunctionMap
from fit.FitFunctionBase import FitFunctionBase
from fit.RabiCarrierFunction import RabiCarrierFunction, FullRabiCarrierFunction  #@UnusedImport
from fit.MotionalRabiFlopping import MotionalRabiFlopping, TwoModeMotionalRabiFlopping #@UnusedImport
from modules import MagnitudeParser
from modules.XmlUtilit import stringToStringOrNone
import logging
from . import SelectionAnalysis  #@UnusedImport

class CosFit(FitFunctionBase):
    name = "Cos"
    functionString =  'A*cos(2*pi*k*x+theta)+O'
    parameterNames = [ 'A', 'k', 'theta', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 1, 0, 0]
        self.startParameters = [1, 1, 0, 0]
        
    def residuals(self, p, y, x, sigma):
        A, k, theta, O = self.allFitParameters(p)
        if sigma is not None:
            return (y-A*numpy.cos(2*numpy.pi*k*x+theta)-O)/sigma
        else:
            return y-A*numpy.cos(2*numpy.pi*k*x+theta)-O
        
    def value(self,x,p=None):
        A, k, theta, O = self.parameters if p is None else p
        return A*numpy.cos(2*numpy.pi*k*x+theta)+O

    def smartStartValues(self, xIn, yIn, parameters, enabled):
        A, k, theta, O = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        maximum = numpy.amax(y)
        minimum = numpy.amin(y)
        A=(maximum-minimum)/2
        O=(maximum+minimum)/2
        #minindex = numpy.argmin(y)
        maxindex = numpy.argmax(y)
        theta = x[maxindex]
        threshold = (maximum+minimum)/2.0
        NewZeroCrossing = x[0]
        PreviousZeroCrossing = x[0]
        maxZeroCrossingDelta = 0
        for ind in range(len(y)-1):
            if (y[ind] <= threshold <= y[ind+1]) or (y[ind+1] <= threshold <= y[ind]):
                NewZeroCrossing = x[ind]
                NewZeroCrossingDelta = NewZeroCrossing-PreviousZeroCrossing
                if NewZeroCrossingDelta > maxZeroCrossingDelta:
                    maxZeroCrossingDelta = NewZeroCrossingDelta 
                PreviousZeroCrossing = NewZeroCrossing
        k = 1.0/(2.0*maxZeroCrossingDelta)
#        theta = numpy.remainder(x0,T)
        logging.getLogger(__name__).info("smart start values A={0}, k={1}, theta={2}, O={3}".format(A, k, theta, O))
        return (A, k, theta, O )

class SinCosFit(FitFunctionBase):
    name = "SinCos"
    functionString =  'A*sin(2*pi*k*x)+B*cos(2*pi*k*x)+O'
    parameterNames = [ 'A', 'B', 'k', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 1, 1, 0]
        self.startParameters = [1, 1, 1, 0]
        self.results['phase'] = ResultRecord(name='phase')
        self.results['amplitude'] = ResultRecord(name='amplitude')

    def residuals(self, p, y, x, sigma):
        A, B, k, O = self.allFitParameters(p)
        if sigma is not None:
            return (y-A*numpy.sin(2*numpy.pi*k*x)-B*numpy.cos(2*numpy.pi*k*x)-O)/sigma
        else:
            return y-A*numpy.sin(2*numpy.pi*k*x)-B*numpy.cos(2*numpy.pi*k*x)-O

    def value(self,x,p=None):
        A, B, k, O = self.parameters if p is None else p
        return A*numpy.sin(2*numpy.pi*k*x)+B*numpy.cos(2*numpy.pi*k*x)+O

    def update(self,parameters=None):
        A, B, k, O = parameters if parameters is not None else self.parameters
        self.results['phase'].value = numpy.arctan2(B, A)
        self.results['amplitude'].value = numpy.sqrt(A*A+B*B)

#     def smartStartValues(self, xIn, yIn, parameters, enabled):
#         A,B,k,O = parameters   #@UnusedVariable
#         x,y = zip(*sorted(zip(xIn, yIn)))
#         x = numpy.array(x)
#         y = numpy.array(y)
#         maximum = numpy.amax(y)
#         minimum = numpy.amin(y)
#         A=(maximum-minimum)/2
#         O=(maximum+minimum)/2
#         #minindex = numpy.argmin(y)
#         maxindex = numpy.argmax(y)
#         #theta = x[maxindex]
#         B=0;
#         threshold = (maximum+minimum)/2.0
#         NewZeroCrossing = x[0]
#         PreviousZeroCrossing = x[0]
#         maxZeroCrossingDelta = 0
#         for ind in range(len(y)-1):
#             if (y[ind] <= threshold <= y[ind+1]) or (y[ind+1] <= threshold <= y[ind]):
#                 NewZeroCrossing = x[ind]
#                 NewZeroCrossingDelta = NewZeroCrossing-PreviousZeroCrossing
#                 if NewZeroCrossingDelta > maxZeroCrossingDelta:
#                     maxZeroCrossingDelta = NewZeroCrossingDelta
#                 PreviousZeroCrossing = NewZeroCrossing
#         k = 1.0/(2.0*maxZeroCrossingDelta)
# #        theta = numpy.remainder(x0,T)
#         logging.getLogger(__name__).info("smart start values A={0}, B={1}, k={2}, O={3}".format(A,B,k,O))
#         return (A,B,k,O )

class CosSqFit(FitFunctionBase):
    name = "Cos2"
    functionString =  'A*cos^2(pi*x/(2*T)+theta)+O'
    parameterNames = [ 'A', 'T', 'theta', 'O' ]    
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 100, 0, 0]
        self.startParameters = [1, 1, 0, 0]
       
    def functionEval(self, x, A, T, theta, O ):
        return A*numpy.square(numpy.cos(numpy.pi/2/T*x+theta))+O

class CosSqPeakFit(FitFunctionBase):
    name = "Cos2 Peak"
    functionString =  'A*cos^2(pi*(x-x0)/(2*T))+O'
    parameterNames = [ 'A', 'T', 'x0', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 100, 0, 0]
        self.startParameters = [1, 1, 0, 0]
       
    def functionEval(self, x, A, T, x0, O ):
        return A*numpy.square(numpy.cos(numpy.pi/2/T*(x-x0)))+O


class SinSqFit(FitFunctionBase):
    name = "Sin2"
    functionString = '(max-min)*sin^2( pi*(x-x0)/(2*T) )+min'
    parameterNames = [  'T', 'x0', 'max', 'min' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [100, 0, 1, 0]
        self.startParameters = [100, 0, 1, 0]
        
    def functionEval(self, x, T, x0, max_, min_ ):
        return (max_-min_)*numpy.square(numpy.sin(numpy.pi/2/T*(x-x0)))+min_

    def smartStartValues(self, xIn, yIn, parameters, enabled):
        T, x0, maximum, minimum = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        maximum = numpy.amax(y)
        minimum = numpy.amin(y)
        minindex = numpy.argmin(y)
        x0 = x[minindex]
        threshold = (maximum+minimum)/2.0
        NewZeroCrossing = x[0]
        PreviousZeroCrossing = x[0]
        maxZeroCrossingDelta = 0
        for ind in range(len(y)-1):
            if (y[ind] <= threshold <= y[ind+1]) or (y[ind+1] <= threshold <= y[ind]):
                NewZeroCrossing = x[ind]
                NewZeroCrossingDelta = NewZeroCrossing-PreviousZeroCrossing
                if NewZeroCrossingDelta > maxZeroCrossingDelta:
                    maxZeroCrossingDelta = NewZeroCrossingDelta 
                PreviousZeroCrossing = NewZeroCrossing
        T = maxZeroCrossingDelta
        x0 = numpy.remainder(x0, 2*T)
        logging.getLogger(__name__).info("smart start values T={0}, x0={1}, maximum={2}, minimum={3}".format(T, x0, maximum, minimum))
        return (T, x0, maximum, minimum)

class DualToneSinSqFit(FitFunctionBase):
    name = "Dual Sin2"
    functionString = '(max-min)*sin^2( pi*(x-x0)/(2*T) )+min'
    parameterNames = [  'T', 'x0', 'max', 'min', 'dT' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [100, 0, 1, 0]
        self.startParameters = [100, 0, 1, 0]
        
    def functionEval(self, x, T, x0, max_, min_, dT ):
        return (max_-min_)*(numpy.square(numpy.sin(numpy.pi/2/(T-dT/2)*(x-x0)))+numpy.square(numpy.sin(numpy.pi/2/(T+dT/2)*(x-x0))) )/2+min_

class ChripedSinSqFit(FitFunctionBase):
    name = "ChirpedSin2"
    functionString = '(max-min)*sin^2( pi*(x-x0)/(2*(T+dt*x) ))+min'
    parameterNames = [  'T', 'x0', 'max', 'min', 'dt' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [100, 0, 1, 0, 0]
        self.startParameters = [100, 0, 1, 0, 0]
        
    def functionEval(self, x, T, x0, max_, min_, dt ):
        return (max_-min_)*numpy.square(numpy.sin(numpy.pi/2/(T+dt*x)*(x-x0)))+min_
    
class SaturationFit(FitFunctionBase):
    name = "Saturation"
    functionString = 'A*(x/s)/(1+(x/s))+O'
    parameterNames = [  'A', 's', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [10, 10, 0]
        self.startParameters = [10, 10, 0]
        
    def functionEval(self, x, A, s, O ):
        return A*(x/s)/(1+(x/s))+O
    
    def smartStartValues(self, xIn, yIn, parameters, enabled):
        A, s, O = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        A = 2*y[-1]
        s = A*(x[-1]-x[0])/(y[-1]-y[0])
        O = y[0]-(A*x[0]/s)
        logging.getLogger(__name__).info("smart start values A={0}, s={1}, O={2}".format(A, s, O))
        return (A, s, O)
  
class SinSqExpFit(FitFunctionBase):
    name = "Sin2 Exponential Decay"
    functionString =  'A * exp(-x/tau) * sin^2(pi/(2*T)*x+theta) + O'
    parameterNames = [ 'A', 'T', 'theta', 'O', 'tau' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 100, 0, 0, 1000]
        self.startParameters = [1, 100, 0, 0, 1000]
        
    def functionEval(self, x, A, T, theta, O, tau ):
        return A*numpy.exp(-x/tau)*numpy.square(numpy.sin(numpy.pi/2/T*x+theta))+O

class CosExpFit(FitFunctionBase):
    name = "Cos Exponential Decay"
    functionString =  '(A/2) * (1 - exp(-x/tau)Cos(pi*t/(2*T)+theta)) + O'
    parameterNames = [ 'A', 'T', 'theta', 'O', 'tau' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 100, 0, 0, 1000]
        self.startParameters = [1, 100, 0, 0, 1000]
        
    def functionEval(self, x, A, T, theta, O, tau ):
        return (A/2.0)*(1-numpy.exp(-x/tau)*numpy.cos(numpy.pi*x/(T)+theta))+O  

class SinSqGaussFit(FitFunctionBase):
    name = "Sin2 Gaussian Decay"
    functionString =  'A * exp(-x^2/tau^2) * sin^2(pi/(2*T)*x+theta) + O'
    parameterNames = [ 'A', 'T', 'theta', 'O', 'tau' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 100, 0, 0, 1000]
        self.startParameters = [1, 100, 0, 0, 1000]
        
    def functionEval(self, x, A, T, theta, O, tau ):
        return A*numpy.exp(-numpy.square(x/tau))*numpy.square(numpy.sin(numpy.pi/2/T*x+theta))+O


class GaussianFit(FitFunctionBase):
    name = "Gaussian"
    functionString =  'A*exp(-(x-x0)**2/s**2)+O'
    parameterNames = [ 'A', 'x0', 's', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [0]*4
        self.startParameters = [1, 0, 1, 0]
        
    def functionEval(self, x, A, x0, s, O ):
        return A*numpy.exp(-numpy.square((x-x0)/s))+O

    def smartStartValues(self, xIn, yIn, parameters, enabled):
        A, x0, s, O = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        maxindex = numpy.argmax(y)
        minimum = numpy.amin(y)
        maximum = y[maxindex]
        x0 = x[maxindex]
        A = maximum-minimum
        O = minimum
        threshold = (maximum+minimum)/2.
        indexplus = -1 #If the threshold point is never found, indexplus is set to the index of the last element
        for ind, val in enumerate(y[maxindex:]):
            if val < threshold:
                indexplus = ind + maxindex
                break
        indexminus = 0 #If the threshold point is never found, indexplus is set to the index of the first element
        for ind, val in enumerate(y[maxindex::-1]):
            if val < threshold:
                indexminus = maxindex-ind
                break
        s = 0.60056*(x[indexplus]-x[indexminus])
        logging.getLogger(__name__).info("smart start values A={0}, x0={1}, s={2}, O={3}".format(A, x0, s, O))
        return (A, x0, s, O)

class InvertedGaussianFit(FitFunctionBase):
    name = "InvertedGaussian"
    functionString =  'A*exp(-(x-x0)**2/s**2)+O'
    parameterNames = [ 'A', 'x0', 's', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [0]*4
        self.startParameters = [1, 0, 1, 0]
        
    def functionEval(self, x, A, x0, s, O ):
        return A*numpy.exp(-numpy.square((x-x0)/s))+O

    def smartStartValues(self, xIn, yIn, parameters, enabled):
        A, x0, s, O = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        maxindex = numpy.argmax(y)
        minindex = numpy.argmin(y)
        minimum = y[minindex]
        maximum = y[maxindex]
        x0 = x[minindex]
        A = minimum-maximum
        O = maximum
        threshold = (maximum+minimum)/2.
        indexplus = -1 #If the threshold point is never found, indexplus is set to the index of the last element
        for ind, val in enumerate(y[minindex:]):
            if val > threshold:
                indexplus = ind + minindex
                break
        indexminus = 0 #If the threshold point is never found, indexplus is set to the index of the first element
        for ind, val in enumerate(y[minindex::-1]):
            if val > threshold:
                indexminus = minindex-ind
                break
        s = 0.60056*(x[indexplus]-x[indexminus])
        logging.getLogger(__name__).info("smart start values A={0}, x0={1}, s={2}, O={3}".format(A, x0, s, O))
        return (A, x0, s, O)

class SquareRabiFit(FitFunctionBase):
    name = "Square Rabi"
    functionString =  'A/(1+(2*pi*(x-C)/R)**2) * sin**2(sqrt(1+(2*pi*(x-C)/R)**2)*R*t/2) + O where R=pi/T'
    parameterNames = [ 'T', 'C', 'A', 'O', 't' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.startParameters = [1.0, 42.0, 1.0, 0.0, 100.0]
        self.results['maxVal'] = ResultRecord( name='maxVal', definition='maximum value of function' )
          
    def __setstate__(self, state):
        super(SquareRabiFit, self ).__setstate__(state)
        self.results.setdefault( 'maxVal', ResultRecord( name='maxVal', definition='maximum value of function' ))
        
    def functionEval(self, x, T, C, A, O, t ):
        R = numpy.pi/T
        u = numpy.square(2*numpy.pi*(x-C)/R)
        return ((A/(1+u))*numpy.square(numpy.sin(numpy.sqrt(1+u)*R*t/2.))) + O  
    
    def smartStartValues(self, xIn, yIn, parameters, enabled):
        T, C, A, O, t = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        maxindex = numpy.argmax(y)
        minimum = numpy.amin(y)
        maximum = y[maxindex]
        C = x[maxindex]
        A = maximum-minimum
        O = minimum
        threshold = (maximum+minimum)/2.
        if not enabled[4]:  # if t is fixed we can estimate T
            indexplus = -1 #If the threshold point is never found, indexplus is set to the index of the last element
            for ind, val in enumerate(y[maxindex:]):
                if val < threshold:
                    indexplus = ind + maxindex
                    break
            indexminus = 0 #If the threshold point is never found, indexplus is set to the index of the first element
            for ind, val in enumerate(y[maxindex::-1]):
                if val < threshold:
                    indexminus = maxindex-ind
                    break
            if x[indexplus]-x[indexminus] != 0:
                T = 0.79869/(x[indexplus]-x[indexminus])
        logging.getLogger(__name__).info("smart start values T={0}, C={1}, A={2}, O={3}, t={4}".format(T, C, A, O, t))
        return (T, C, A, O, t)
    
    def update(self,parameters=None):
        T, C, A, O, t = parameters if parameters is not None else self.parameters #@UnusedVariable
        R = numpy.pi/T
        self.results['maxVal'].value = (A*numpy.square(numpy.sin(R*t/2.))) + O

class SquareRabiFitAmp(FitFunctionBase):
    name = "Square Rabi w/Amp"
    functionString =  '(A/(1+(2*pi*(x-C)/R)**2))/(sin**2(R*t/2)) * sin**2(sqrt(1+(2*pi*(x-C)/R)**2)*R*t/2) + O where R=pi/T'
    parameterNames = [ 'T', 'C', 'A', 'O', 't' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.startParameters = [1.0,42.0,1.0,0.0,100.0]
        self.results['maxVal'] = ResultRecord( name='maxVal',definition='maximum value of function' )

    def __setstate__(self, state):
        super(SquareRabiFitAmp, self ).__setstate__(state)
        self.results.setdefault( 'maxVal', ResultRecord( name='maxVal',definition='maximum value of function' ))

    def functionEval(self, x, T, C, A, O, t ):
        R = numpy.pi/T
        u = numpy.square(2*numpy.pi*(x-C)/R)
        return (((A/(1+u))/(numpy.square(numpy.sin(R*t/2.0))))*numpy.square(numpy.sin(numpy.sqrt(1+u)*R*t/2.))) + O

    def smartStartValues(self, xIn, yIn, parameters, enabled):
        T, C, A, O, t = parameters   #@UnusedVariable
        x,y = zip(*sorted(zip(xIn, yIn)))
        x = numpy.array(x)
        y = numpy.array(y)
        maxindex = numpy.argmax(y)
        minimum = numpy.amin(y)
        maximum = y[maxindex]
        C = x[maxindex]
        A = maximum-minimum
        O = minimum
        threshold = (maximum+minimum)/2.
        if not enabled[4]:  # if t is fixed we can estimate T
            indexplus = -1 #If the threshold point is never found, indexplus is set to the index of the last element
            for ind, val in enumerate(y[maxindex:]):
                if val < threshold:
                    indexplus = ind + maxindex
                    break
            indexminus = 0 #If the threshold point is never found, indexplus is set to the index of the first element
            for ind, val in enumerate(y[maxindex::-1]):
                if val < threshold:
                    indexminus = maxindex-ind
                    break
            if x[indexplus]-x[indexminus] != 0:
                T = 0.79869/(x[indexplus]-x[indexminus])
        logging.getLogger(__name__).info("smart start values T={0}, C={1}, A={2}, O={3}, t={4}".format(T, C, A, O, t))
        return (T, C, A, O, t)

    def update(self,parameters=None):
        T, C, A, O, t = parameters if parameters is not None else self.parameters #@UnusedVariable
        R = numpy.pi/T
        self.results['maxVal'].value = (A*numpy.square(numpy.sin(R*t/2.))) + O

class LorentzianFit(FitFunctionBase):
    name = "Lorentzian"
    functionString =  'A*s**2*1/(s**2+(x-x0)**2)+O'
    parameterNames = [ 'A', 's', 'x0', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.startParameters = [1, 1, 0, 0]
        
    def functionEval(self, x, A, s, x0, O ):
        s2 = numpy.square(s)
        return A*s2/(s2+numpy.square(x-x0))+O

class AsymLorentzianFit(FitFunctionBase):
    name = "Asymmetric Lorentzian"
    functionString =  'A*s**2*1/(s**2+(x-x0)**2)+O s=s1 for x<x0, s=s2 x>x0'
    parameterNames = [ 'A', 's1', ' s2', 'x0', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.startParameters = [1, 1, 1, 0, 0]
        
    def functionEval(self, x, A, s1, s2, x0, O ):
        s1sq = numpy.square(s1)
        s2sq = numpy.square(s2)
        return numpy.piecewise(x, [x<=x0, x>x0], [lambda x: A*s1sq/(s1sq+numpy.square(x-x0))+O, lambda x: A*s2sq/(s2sq+numpy.square(x-x0))+O] )

       
class TruncatedLorentzianFit(FitFunctionBase):
    name = "Truncated Lorentzian"
    functionString =  'A*s**2*1/(s**2+(x-x0)**2)+O'
    parameterNames = [ 'A', 's', 'x0', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.startParameters = [1, 1, 0, 0]
        self.epsfcn=10.0
        
    def functionEval(self, x, A, s, x0, O):
        s2 = numpy.square(s)
        return (A*s2/(s2+numpy.square(x-x0)))*(1-numpy.sign(x-x0))/2+O

class LinearFit(FitFunctionBase):
    """class for fitting to a line
    """
    name = "Line"
    functionString =  'm*x + b'
    parameterNames = [ 'm', 'b' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 0]
        self.startParameters = [1, 0]
        self.halfpoint = 0        
        self.results['halfpoint'] = ResultRecord(name='halfpoint')
        
    def functionEval(self, x, m, b ):
        return m*x + b
        
    def update(self,parameters=None):
        m, b = parameters if parameters is not None else self.parameters
        self.results['halfpoint'].value = (0.5-b)/m

class RabiFieldProfileFit(FitFunctionBase):
    name = "RabiFieldProfileFit"
    functionString =  'A*sin(c*exp(-(x-x0)**2/w**2)**2+O'
    parameterNames = [ 'A', 'c', 'x0', 'w', 'O' ]
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.startParameters = [1, 1, 0, 1, 0]
        
    def functionEval(self, x, A, c, x0, w, O ):
        return A*numpy.square(numpy.sin(c*numpy.exp(-numpy.square((x-x0)/w)))) + O

    def smartStartValues(self, xIn, yIn, parameters, enabled):
        A, c, x0, w, O = parameters   #@UnusedVariable
        x, y = list(zip(*sorted(zip(xIn, yIn))))
        x = numpy.array(x)
        y = numpy.array(y)
        maxindex = numpy.argmax(y)
        minimum = numpy.amin(y)
        maximum = y[maxindex]
        x0 = x[maxindex]
        A = 1
        O = minimum
        c = numpy.arcsin(numpy.sqrt(maximum))
        threshold = (maximum+minimum)/2.
        indexplus = -1 #If the threshold point is never found, indexplus is set to the index of the last element
        for ind, val in enumerate(y[maxindex:]):
            if val < threshold:
                indexplus = ind + maxindex
                break
        indexminus = 0 #If the threshold point is never found, indexplus is set to the index of the first element
        for ind, val in enumerate(y[maxindex::-1]):
            if val < threshold:
                indexminus = maxindex-ind
                break
        w = 0.60056*(x[indexplus]-x[indexminus])
        logging.getLogger(__name__).info("smart start values A={0}, c={1}, x0={2}, w={3}, O={4}".format(A, c, x0, w, O))
        return (A, c, x0, w, O)
               
def fitFunctionFactory(text):
    """
    Creates a FitFunction Object from a saved string representation
    """
    parts = text.split(';')
    components = parts[0].split(',')
    name = components[0].strip()
    function = fitFunctionMap[name]()
    for index, arg in enumerate(components[2:]):
        value = float(arg.split('=')[1].strip())
        function.parameters[index] = value
    if len(parts)>1 and len(parts[1])>0:
        components = parts[1].split(',')
        for item in components:
            name, value = item.split('=')
            setattr(function, name.strip(), MagnitudeParser.parse(value.strip()))
    return function

def fromXmlElement(element):
    """
    Creates a FitFunction Object from a saved string representation
    """
    name = element.attrib['name']
    if name not in fitFunctionMap.keys():
        return None
    function = fitFunctionMap[name]()
    function.parametersConfidence = [None]*len(function.parameters)
    function.parameterEnabled = [True]*len(function.parameters)
    function.startParameterExpressions = [None]*len(function.parameters)
    function.parameterBounds = [[None, None]]*len(function.parameters)
    function.parameterBoundsExpressions = [[None, None]]*len(function.parameters)
    for index, parameter in enumerate(element.findall("Parameter")):
        value = float(parameter.text)
        function.parameters[index] = value
        #function.parameterNames[index] = parameter.attrib['name']
        function.parametersConfidence[index] = float(parameter.attrib['confidence']) if parameter.attrib['confidence'] != 'None' else None
        function.parameterEnabled[index] = parameter.attrib['enabled'] == "True"
        function.startParameterExpressions[index] = stringToStringOrNone( parameter.attrib.get('startExpression', 'None') )
        function.parameterBounds[index] = list(map( stringToStringOrNone, parameter.attrib.get('bounds', 'None,None').split(",") ))
        function.parameterBoundsExpressions[index] = list(map( stringToStringOrNone, parameter.attrib.get('boundsExpression', 'None,None').split(",") ))
    for index, parameter in enumerate(element.findall("Result")):
        name= parameter.attrib['name']
        function.results[name] = ResultRecord( name=name,
                               definition = stringToStringOrNone( parameter.attrib['definition'] ),
                               value = MagnitudeParser.parse(parameter.text) )
    return function

def fromHdf5(group):
    name = group.attrs['name']
    function = fitFunctionMap[name]()
    function.parametersConfidence = [None]*len(function.parameters)
    function.parameterEnabled = [True]*len(function.parameters)
    function.startParameterExpressions = [None]*len(function.parameters)
    function.parameterBounds = [[None, None]]*len(function.parameters)
    function.parameterBoundsExpressions = [[None, None]]*len(function.parameters)
    for name, g in group['parameters']:
        index = g.attrs['index']
        function.parameters[index] = g.attrs['value']
        function.parametersConfidence[index] = g.attrs.get('confidence', None)
        function.parameterEnabled[index] = g.attrs['enabled']
        function.startParameterExpressions[index] = g.attrs['startExpression']
        function.parameterBounds[index] = list(g.attrs['bounds'])
        function.parameterBoundsExpressions[index] = list(map( stringToStringOrNone, g.attrs.get('boundsExpression', 'None,None').split(",") ))
    for name, g in group['results']:
        function.results[name] = ResultRecord( name=name,
                               definition = stringToStringOrNone( g.attribs['definition'] ),
                               value = MagnitudeParser.parse(g.attribs['value']) )
    return function

        
if __name__ == "__main__":
    x = numpy.arange(0, 6e-2, 6e-2/30)
    A, k, theta = 10, 1.0/3e-2, numpy.pi/6
    y_true = A*numpy.sin(2*numpy.pi*k*x+theta)
    y_meas = y_true + 2*numpy.random.randn(len(x))
    
    f = CosFit()
    p = [8, 1/2.3e-2, 1]
    ls, n = f.leastsq(x, y_meas, p )
    
    import matplotlib.pyplot as plt
    plt.plot(x, f.value(x, ls), x, y_meas, 'o', x, y_true)
    plt.title('Least-squares fit to noisy data')
    plt.legend(['Fit', 'Noisy', 'True'])
    plt.show() 
