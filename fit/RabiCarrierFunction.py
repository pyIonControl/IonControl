# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools
import logging

from numpy import pi, cos, sqrt, sin, exp, dot, array, log
from scipy import constants
from scipy.special import laguerre

from .FitFunctionBase import ResultRecord
from fit.FitFunctionBase import FitFunctionBase
from modules.quantity import Q


class RabiCarrierFunction(FitFunctionBase):
    name = "RabiCarrier"
    functionString =  'Explicit Carrier Rabi Transition with Lamb-Dicke approximation'
    parameterNames = [ 'A', 'n', 'rabiFreq', 'mass', 'angle', 'trapFrequency', 'wavelength']
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1, 7, 0.28, 40, 0, 1.578, 729]
        self.startParameters = [1, 7, 0.28, 40, 0, Q(1.578, 'MHz'), Q(729, 'nm')]
        self.units = [None, None, None, None, None, 'MHz', 'nm' ]
        self.parameterEnabled = [True, True, True, False, False, False, False]
        self.parametersConfidence = [None]*7
        # constants
        self.results['taufinal'] = ResultRecord( name='taufinal', value=0)
        self.results['scTimeInit'] = ResultRecord( name='scTimeInit', value=0)
        self.results['scIncrement'] = ResultRecord( name='scIncrement', value=0 )
        self.results['numberLoops'] = ResultRecord( name='numberLoops', value=0 )
        self.results['eta'] = ResultRecord( name='eta', value=0 )
        self.update()
        
    def update(self,parameters=None):
        _, n, omega, mass, angle, trapFrequency, wavelength = self.parameters if parameters is None else parameters
        m = mass * constants.m_p
        secfreq = trapFrequency*10**6
        eta = ( (2*pi/(wavelength*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq)) )
        scTimeInit = Q((1 / omega) / (eta*sqrt(n)), 'us')
        taufinal = Q((1 / omega) / eta, 'us')
        nstart = 2*n
        self.results['taufinal'] = ResultRecord( name='taufinal', value=taufinal)
        self.results['scTimeInit'] = ResultRecord( name='scTimeInit', value=scTimeInit)
        self.results['scIncrement'] = ResultRecord( name='scIncrement', value=(taufinal-scTimeInit)/nstart )
        self.results['numberLoops'] = ResultRecord( name='numberLoops', value=nstart )
        self.results['eta'] = ResultRecord( name='eta', value=eta )
                
    def residuals(self, p, y, x, sigma):
        A, n, omega, mass, angle, trapFrequency, wavelength = self.allFitParameters(p)
        secfreq = trapFrequency*10**6
        m = mass * constants.m_p
        eta = ( (2*pi/(wavelength*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq)) )
        eta2 = pow(eta, 2)
        if sigma is not None:
            return (y-( A/2*(1-1/(n+1)*(cos(2*omega*x)*(1-n/(n+1)*cos(2*omega*x*eta2))+(n/(n+1))*sin(2*omega*x)*sin(2*omega*x*eta2))/(1+(n/(n+1))**2
                -2*(n/(n+1))*cos(2*omega*x*eta2))) ))/sigma
        else:
            return y-( A/2*(1-1/(n+1)*(cos(2*omega*x)*(1-n/(n+1)*cos(2*omega*x*eta2))+(n/(n+1))*sin(2*omega*x)*sin(2*omega*x*eta2))/(1+(n/(n+1))**2
                -2*(n/(n+1))*cos(2*omega*x*eta2))) )
        
    def value(self,x,p=None):
        A, n, omega, mass, angle, trapFrequency, wavelength  = self.parameters if p is None else p
        secfreq = trapFrequency*10**6
        m = mass * constants.m_p
        eta = ( (2*pi/(wavelength*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq)) )
        eta2 = pow(eta, 2)
        value = ( A/2.*(1.-1./(n+1.)*(cos(2*omega*x)*(1-n/(n+1.)*cos(2*omega*x*eta2))+(n/(n+1.))*sin(2*omega*x)*sin(2*omega*x*eta2))/(1+(n/(n+1.))**2
                -2*(n/(n+1.))*cos(2*omega*x*eta2))) )
        return value

def getLaguerreTable(mass, trapFrequency, wavelength, angle):
    #secfreq = float(trapFrequency, 'Hz') * 10**6
    secfreq = float(trapFrequency.m_as('Hz')) * 10**6
    m = mass * constants.m_p
    eta = ( (2*pi/(wavelength*10**-9))*cos(angle*pi/180)
                 * sqrt(constants.hbar/(2*m*2*pi*secfreq)) )
    return laguerreTableInternal(eta)


@functools.lru_cache(maxsize=5)
def laguerreTableInternal(eta):
    logger = logging.getLogger(__name__)
    eta2 = pow(eta, 2)
    logger.info( "Calculating Laguerre Table for eta^2={0}".format(eta2) )
    laguerreTable = array([ laguerre(n)(eta2) for n in range(200) ])
    return laguerreTable


@functools.lru_cache(maxsize=5)
def getPnTable(beta):
    logger = logging.getLogger(__name__)
    logger.info( "Calculating Probability Table for beta {0}".format(beta) )
    pnTable = array([ exp(-(n+1)*beta)*(exp(beta)-1) for n in range(200)])
    logger.info( 1-sum(pnTable) )
    return pnTable

        
class FullRabiCarrierFunction(RabiCarrierFunction):
    name = "FullRabiCarrier"
    functionString =  'Numerical Carrier Rabi Transition without Lamb-Dicke approx'
    def __init__(self):
        super(FullRabiCarrierFunction, self).__init__()
        # self.laguerreCacheEta = -1
        # self.laguerreTable = None
        # self.pnCacheBeta = -1
        # self.pnTable = None
        
    # def __setstate__(self, state):
    #     state.pop('laguerreCacheEta', None )
    #     state.pop('laguerreTable', None)
    #     state.pop('pnCacheBeta', None )
    #     state.pop('pnTable', None)
    #     super(self, FullRabiCarrierFunction).__setstate__(state)

    def residuals(self, p, y, x, sigma):
        A, n, omega, mass, angle, trapFrequency, wavelength = self.allFitParameters(self.parameters if p is None else p) #@UnusedVariable
        beta = log(1+1./n)
        pnTable = getPnTable(beta)
        laguerreTable = getLaguerreTable(mass, trapFrequency, wavelength, angle)
        if hasattr(x, '__iter__'):
            result = list()
            for xn in x:
                valueList = sin((omega * xn )* laguerreTable )**2
                value = A*dot( pnTable, valueList )
                result.append(value)
        else:
            valueList = sin(omega * laguerreTable * x)**2
            result = A*dot( pnTable, valueList )
        if sigma is not None:
            return (y-result)/sigma
        else:
            return y-result
        
    def value(self, x, p=None):
        A, n, omega, mass, angle, trapFrequency, wavelength = self.parameters if p is None else p  #@UnusedVariable
        beta = log(1+1./n)
        pnTable = getPnTable(beta)
        laguerreTable = getLaguerreTable(mass, trapFrequency, wavelength, angle)
        if hasattr(x, '__iter__'):
            result = list()
            for xn in x:
                valueList = sin((omega * xn )* laguerreTable )**2
                value = A*dot(pnTable, valueList )
                result.append(value)
        else:
            valueList = sin(omega * laguerreTable * x)**2
            result = A*dot(pnTable, valueList )
        return result
                
        
