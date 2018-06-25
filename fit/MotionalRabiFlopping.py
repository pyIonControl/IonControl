# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from numpy import pi, cos, sqrt, sin, exp, dot, array, outer
from scipy import constants
from scipy.special import genlaguerre

from .FitFunctionBase import ResultRecord
from fit.FitFunctionBase import FitFunctionBase
from modules.quantity import Q, is_Q
import logging
from functools import lru_cache

def factorialRatio(ng, nl):
    r = 1
    for i in range(int(nl)+1, int(ng)+1):
        r *= i
    return r

def transitionAmplitude(eta, n, m):
    eta2 = eta*eta
    nl = min(n, m)
    ng = max(n, m)
    d = abs(n-m)
    if n>=0 and m>=0:
        return exp(-eta2/2) * pow(eta, d) * genlaguerre(nl, d)(eta2) / sqrt( factorialRatio(ng, nl ) ) #if n>=0 and m>=0 else 0
    return 0

@lru_cache(maxsize=20)
def laguerreTable(eta, delta_n):
    logging.getLogger(__name__).info( "Calculating Laguerre Table for eta={0} delta_n={1}".format(eta, delta_n) )
    laguerreTable = array([ transitionAmplitude(eta, n, n+delta_n) for n in range(200) ])
    return laguerreTable

@lru_cache(maxsize=20)
def probabilityTable(nBar):
    logger = logging.getLogger(__name__)
    logger.info( "Calculating Probability Table for nBar {0}".format(nBar) )
    current = 1/(nBar+1.)
    factor = nBar/(nBar+1.)
    a = [current]
    for _ in range(1, 200):
        current *= factor
        a.append( current )
    a = array(a)
    logger.info( 1-sum(a) )
    return a


class MotionalRabiFlopping(FitFunctionBase):
    name = "MotionalRabiFlopping"
    functionString =  'Motional Rabi Flopping'
    parameterNames = [ 'A', 'n', 'rabiFreq', 'mass', 'angle', 'trapFrequency', 'wavelength', 'delta_n']
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1.0, 7.0, 0.28, 40, 0, 1.578, 729, 0.0]
        self.startParameters = [1.0, 7.0, 0.28, 40, 0, Q(1.578, 'MHz'), Q(729, 'nm'), 0.0]
        self.units = [None, None, None, None, None, 'MHz', 'nm', None ]
        self.parameterEnabled = [True, True, True, False, False, False, False, False ]
        self.parametersConfidence = [None]*8
        # constants
        self.results['eta'] = ResultRecord( name='eta', value=0 )
        self.update()
        self.laguerreCacheEta = -1
        self.laguerreTable = None
        self.pnCache_nBar = -1
        self.pnTable = None

    def update(self,parameters=None):
        A, n, omega, mass, angle, trapFrequency, wavelength, delta_n = self.parameters if parameters is None else parameters #@UnusedVariable
        m = mass * constants.m_p
        if not is_Q(trapFrequency):
            trapFrequency = Q(trapFrequency, 'MHz')
        if not is_Q(wavelength):
            wavelength = Q(wavelength, 'nm')
        secfreq = trapFrequency.m_as('Hz')
        eta = (2 * pi / wavelength.m_as('m') * cos(angle * pi / 180)
               * sqrt(constants.hbar / (2 * m * 2 * pi * secfreq)))
        self.results['eta'] = ResultRecord( name='eta', value=eta )
               
    def updateTables(self, nBar):
        _, _, _, mass, angle, trapFrequency, wavelength, delta_n = self.parameters #@UnusedVariable
        if delta_n < 0:
            delta_n = 0
            self.parameters[-1] = 0
        if not is_Q(trapFrequency):
            trapFrequency = Q(trapFrequency, 'MHz')
        if not is_Q(wavelength):
            wavelength = Q(wavelength, 'nm')
        secfreq = trapFrequency.m_as('Hz')
        m = mass * constants.m_p
        eta = (2 * pi / wavelength.m_as('m') * cos(angle * pi / 180)
               * sqrt(constants.hbar / (2 * m * 2 * pi * secfreq)))
        self.laguerreTable = laguerreTable(eta, delta_n)
        self.pnTable = probabilityTable(nBar)
            
    def residuals(self, p, y, x, sigma):
        A, n, omega, _, _, _, _, _ = self.allFitParameters(self.parameters if p is None else p) #@UnusedVariable
        self.updateTables(n)
        if hasattr(x, '__iter__'):
            result = list()
            for xn in x:
                valueList = sin((omega * xn )* self.laguerreTable )**2
                value = A*dot( self.pnTable, valueList )
                result.append(value)
        else:
            valueList = sin(omega * self.laguerreTable * x)**2
            result = A*dot( self.pnTable, valueList )
        if sigma is not None:
            return (y-result)/sigma
        else:
            return y-result
        
    def value(self,x,p=None):
        A, n, omega, mass, angle, trapFrequency, wavelength, delta_n = self.parameters if p is None else p  #@UnusedVariable
        self.updateTables(n)
        if hasattr(x, '__iter__'):
            result = list()
            for xn in x:
                valueList = sin((omega * xn )* self.laguerreTable )**2
                value = A*dot( self.pnTable, valueList )
                result.append(value)
        else:
            valueList = sin(omega * self.laguerreTable * x)**2
            result = A*dot( self.pnTable, valueList )
        return result
                
     
     
     
class TwoModeMotionalRabiFlopping(FitFunctionBase):
    name = "TwoModeMotionalRabiFlopping"
    functionString =  'Two Mode Motional Rabi Flopping'
    parameterNames = [ 'A', 'n', 'rabiFreq', 'mass', 'angle', 'trapFrequency', 'wavelength', 'delta_n', 'n_2', 'trapFrequency_2']
    def __init__(self):
        FitFunctionBase.__init__(self)
        self.parameters = [1.0, 7.0, 0.28, 40, 0.0, 1.578, 729, 0.0, 0.0, 1.5]
        self.startParameters = [1.0, 7.0, 0.28, 40, 0.0, Q(1.578, 'MHz'), Q(729, 'nm'), 0.0, 0.0, Q(1.578, 'MHz')]
        self.units = [None, None, None, None, None, 'MHz', 'nm', None, None, 'MHz' ]
        self.parameterEnabled = [True, True, True, False, False, False, False, False, False, False ]
        self.parametersConfidence = [None]*10
        # constants
        self.results['eta'] = ResultRecord( name='eta', value=0 )
        self.results['eta_2'] = ResultRecord( name='eta_2', value=0 )
        self.update()
        self.laguerreTable = None
        self.laguerreTable2 = None
        self.pnTable = None
        self.pnTable2 = None

    def update(self,parameters=None):
        A, n, omega, mass, angle, trapFrequency, wavelength, delta_n, n_2, trapFrequency_2 = self.parameters if parameters is None else parameters #@UnusedVariable
        m = mass * constants.m_p
        if not is_Q(trapFrequency):
            trapFrequency = Q(trapFrequency, 'MHz')
        if not is_Q(trapFrequency_2):
            trapFrequency_2 = Q(trapFrequency_2, 'MHz')
        if not is_Q(wavelength):
            wavelength = Q(wavelength, 'nm')
        secfreq = trapFrequency*10**6
        secfreq2 = trapFrequency_2*10**6
        eta = ( (2*pi/(wavelength.m_as('m')*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq)) )
        eta2 = ( (2*pi/(wavelength.m_as('m')*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq2)) )
        self.results['eta'] = ResultRecord( name='eta', value=eta )
        self.results['eta_2'] = ResultRecord( name='eta_2', value=eta2 )
               
    def updateTables(self, p):
        A, n, omega, mass, angle, trapFrequency, wavelength, delta_n, n_2, trapFrequency_2 = p #@UnusedVariable
        if not is_Q(trapFrequency):
            trapFrequency = Q(trapFrequency, 'MHz')
        if not is_Q(trapFrequency_2):
            trapFrequency_2 = Q(trapFrequency_2, 'MHz')
        if not is_Q(wavelength):
            wavelength = Q(wavelength, 'nm')
        secfreq = trapFrequency.m_as('Hz') * 10**6
        secfreq2 = trapFrequency_2.m_as('Hz') * 10**6
        m = mass * constants.m_p
        eta = ( (2*pi/(wavelength.m_as('m')*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq)) )
        eta2 = ( (2*pi/(wavelength.m_as('m')*10**-9))*cos(angle*pi/180)
                     * sqrt(constants.hbar/(2*m*2*pi*secfreq2)) )
        self.laguerreTable = laguerreTable(eta, delta_n)
        self.laguerreTable2 = laguerreTable(eta2, 0)
        self.pnTable = probabilityTable(n)
        self.pnTable2 = probabilityTable(n_2)
            
    def residuals(self, p, y, x, sigma):
        result = self.value(x, self.allFitParameters(p))
        if sigma is not None:
            return (y-result)/sigma
        else:
            return y-result
        
    def value(self,x,p=None):
        myp=self.parameters if p is None else p
        A, n, omega, mass, angle, trapFrequency, wavelength, delta_n, n_2, trapFrequency_2 = myp  #@UnusedVariable
        self.updateTables(myp)
        if hasattr(x, '__iter__'):
            result = list()
            for xn in x:
                valueList = sin((omega * xn )* outer( self.laguerreTable, self.laguerreTable2).flatten()  )**2
                value = A*dot( outer( self.pnTable, self.pnTable2).flatten(), valueList )
                result.append(value)
        else:
            valueList = sin(omega * outer( self.laguerreTable, self.laguerreTable2).flatten()  * x)**2
            result = A*dot( outer( self.pnTable, self.pnTable2).flatten(), valueList )
        return result
                
        
   
