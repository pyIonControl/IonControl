# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from itertools import zip_longest, cycle
import logging
from math import sqrt

import numpy
from scipy.optimize import leastsq

from modules.SequenceDict import SequenceDict
import lxml.etree as ElementTree
from modules.Expression import Expression
from modules.Observable import Observable
from modules.quantity import Q
from leastsqbound import leastsqbound
from modules.DataChanged import DataChanged
import collections


class FitFunctionException(Exception):
    pass

class ResultRecord(object):
    def __init__(self, name=None, definition=None, value=None):
        self.name = name
        self.definition = definition
        self.value = value

    stateFields = ['name', 'definition', 'value'] 
        
    def __eq__(self, other):
        return isinstance(other, ResultRecord) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))

fitFunUpdate = DataChanged()

class UniqueOriginDict(collections.UserDict):
    """A custom dictionary for proper updating of user-defined fit functions"""
    def __init__(self):
        super().__init__()
        self.origins = dict()

    def __setitem__(self, key, item):
        if 'origin' in vars(item).keys():
            if item.__dict__['origin'] in self.origins.keys():
                repname = self.origins[item.__dict__['origin']]
                del self.origins[item.__dict__['origin']]
                del self.data[repname]
                fitFunUpdate.dataChanged.emit(repname, False)
            self.origins[item.__dict__['origin']] = key
        self.data[key] = item

fitFunctionMap = UniqueOriginDict()

class FitFunctionMeta(type):
    def __new__(self, name, bases, dct):
        if 'name' not in dct:
            raise FitFunctionException("Fitfunction class needs to have class attribute 'name'")
        instrclass = super(FitFunctionMeta, self).__new__(self, name, bases, dct)
        if name!='FitFunctionBase':
            fitFunctionMap[str(dct['name'])] = instrclass
            overwriteParams = dct.get('overwrite', False)
            fitFunUpdate.dataChanged.emit(str(dct['name']), overwriteParams)
        return instrclass
    
def native(method):
    """Tag a method native to detect function overwrites in derived classes.
    Used to detect whether smartStartValues are implemented"""
    method.isNative = True
    return method    

class FitFunctionBase(object, metaclass=FitFunctionMeta):
    expression = Expression()
    name = 'None'
    parameterNames = list()
    def __init__(self):
        numParameters = len(self.parameterNames)
        self.epsfcn=0.0
        self.parameters = [0] * numParameters
        self.startParameters = [1] * numParameters 
        self.startParameterExpressions = None   # will be initialized by FitUiTableModel if values are available
        self.parameterEnabled = [True] * numParameters
        self.parametersConfidence = [None] * numParameters
        self.units = None
        self.results = SequenceDict({'RMSres': ResultRecord(name='RMSres')})
        self.useSmartStartValues = False
        self.hasSmartStart = not hasattr(self.smartStartValues, 'isNative' )
        self.parametersUpdated = Observable()
        self.parameterBounds = [[None, None] for _ in range(numParameters) ]
        self.parameterBoundsExpressions = None
        self.useErrorBars = True
        
    def __setstate__(self, state):
        state.pop('parameterNames', None )
        state.pop('cov_x', None)
        state.pop('infodict', None)
        state.pop('laguerreCacheEta', None )
        state.pop('laguerreTable', None)
        state.pop('pnCacheBeta', None )
        state.pop('pnTable', None)
        self.__dict__ = state
        self.__dict__.setdefault( 'useSmartStartValues', False )
        self.__dict__.setdefault( 'startParameterExpressions', None )
        self.__dict__.setdefault( 'parameterBounds', [[None, None] for _ in range(len(self.parameterNames)) ]  )
        self.__dict__.setdefault( 'parameterBoundsExpressions', None)
        self.__dict__.setdefault( 'useErrorBars', True)
        self.hasSmartStart = not hasattr(self.smartStartValues, 'isNative' )
 
    def allFitParameters(self, p):
        """return a list where the disabled parameters are added to the enabled parameters given in p"""
        pindex = 0
        params = list()
        for index, (unit, enabled) in enumerate(zip(cycle(self.units if isinstance(self.units, list) else [self.units]), self.parameterEnabled)):
            if enabled:
                params.append(p[pindex])
                pindex += 1
            else:
                params.append(float(self.startParameters[index]) if unit is None else self.startParameters[index].m_as(unit))
        return params
    
    @staticmethod
    def coercedValue( val, bounds ):
        if bounds[1] is not None and val>=bounds[1]:
            val = float(0.95*bounds[1]+0.05*bounds[0] if bounds[0] is not None else bounds[1]-0.01)
        if bounds[0] is not None and val<=bounds[0]:
            val = float(0.95*bounds[0]+0.05*bounds[1] if bounds[1] is not None else bounds[0]+0.01)
        return val
    
    def enabledStartParameters(self, parameters=None, bounded=False):
        """return a list of only the enabled start parameters"""
        if parameters is None:
            parameters = self.startParameters
        params = list()
        if bounded:
            for enabled, param, bounds in zip(self.parameterEnabled, parameters, self.parameterBounds):
                if enabled:
                    params.append(self.coercedValue(float(param), bounds))
        else:
            for enabled, unit, param in zip(self.parameterEnabled, cycle(self.units if isinstance(self.units, list) else [self.units]), parameters):
                if enabled:
                    params.append(float(param) if unit is None else param.m_as(unit))
        return params

    def enabledFitParameters(self, parameters=None):
        """return a list of only the enabled fit parameters"""
        if parameters is None:
            parameters = self.parameters
        params = list()
        for enabled, param in zip(self.parameterEnabled, parameters):
            if enabled:
                params.append(float(param))
        return params

    def enabledParameterNames(self):
        """return a list of only the enabled fit parameters"""
        params = list()
        for enabled, param in zip(self.parameterEnabled, self.parameterNames):
            if enabled:
                params.append(param)
        return params
    
    def setEnabledFitParameters(self, parameters):
        """set the fitted parameters if enabled"""
        pindex = 0
        for index, (unit, enabled) in enumerate(zip(cycle(self.units if isinstance(self.units, list) else [self.units]), self.parameterEnabled)):
            if enabled:
                self.parameters[index] = parameters[pindex]
                pindex += 1
            else:
                self.parameters[index] = float(self.startParameters[index]) if unit is None else self.startParameters[index].m_as(unit)
    
    def setEnabledConfidenceParameters(self, confidence):
        """set the parameter confidence values for the enabled parameters"""
        pindex = 0
        for index, enabled in enumerate(self.parameterEnabled):
            if enabled:
                self.parametersConfidence[index] = confidence[pindex]
                pindex += 1
            else:
                self.parametersConfidence[index] = None        

    @native
    def smartStartValues(self, x, y, parameters, enabled):
        return None
    
    def enabledSmartStartValues(self, x, y, parameters):
        smartParameters = self.smartStartValues(x, y, parameters, self.parameterEnabled)
        return [ smartparam if enabled else param for enabled, param, smartparam in zip(self.parameterEnabled, parameters, smartParameters)] if smartParameters is not None else None

    def evaluate(self, globalDict ):
        myReplacementDict = self.replacementDict()
        if globalDict is not None:
            myReplacementDict.update( globalDict )
        if self.startParameterExpressions is not None:
            self.startParameters = [param if expr is None else self.expression.evaluateAsMagnitude(expr, myReplacementDict ) for param, expr in zip(self.startParameters, self.startParameterExpressions)]
        if self.parameterBoundsExpressions is not None:
            self.parameterBounds = [[bound[0] if expr[0] is None else self.expression.evaluateAsMagnitude(expr[0], myReplacementDict),
                                     bound[1] if expr[1] is None else self.expression.evaluateAsMagnitude(expr[0], myReplacementDict)]
                                     for bound, expr in zip(self.parameterBounds, self.parameterBoundsExpressions)]

    def enabledBounds(self):
        result = [[float(bounds[0]) if bounds[0] is not None else None,
                   float(bounds[1]) if bounds[1] is not None else None] for enabled, bounds in zip(self.parameterEnabled, self.parameterBounds) if enabled]
        enabled = any( (any(bounds) for bounds in result) )
        return result if enabled else None

    def leastsq(self, xin, yin, parameters=None, sigma=None, filt=None):
        if filt is None:
            x, y = map(numpy.asarray, zip(*filter(lambda x: ~numpy.isnan(x[0]) and ~numpy.isnan(x[1]), zip(xin,yin))))
        elif sigma is None:
            x, y, _ = map(numpy.asarray, zip(*filter(lambda x: ~numpy.isnan(x[0]) and ~numpy.isnan(x[1]) and x[2], zip(xin,yin,filt))))
        else:
            x, y, _, sigma = map(numpy.asarray, zip(*filter(lambda x: ~numpy.isnan(x[0]) and ~numpy.isnan(x[1]) and x[2], zip(xin,yin,filt,sigma))))
        logger = logging.getLogger(__name__)
        # Ensure all values of sigma or non zero by replacing with the minimum nonzero value
        if sigma is not None and self.useErrorBars:
            nonzerosigma = sigma[sigma>0]
            sigma[sigma==0] = numpy.min(nonzerosigma) if len(nonzerosigma)>0 else 1.0
        else:
            sigma = None 
        if parameters is None:
            parameters = [float(param) if unit is None else param.m_as(unit) for unit, param in zip(cycle(self.units if isinstance(self.units, list) else [self.units]), self.startParameters)]
        if self.useSmartStartValues:
            smartParameters = self.smartStartValues(x, y, parameters, self.parameterEnabled)
            if smartParameters is not None:
                parameters = [ smartparam if enabled else param for enabled, param, smartparam in zip(self.parameterEnabled, parameters, smartParameters)]
        
        myEnabledBounds = self.enabledBounds()
        if myEnabledBounds:
            enabledOnlyParameters, cov_x, infodict, self.mesg, self.ier = leastsqbound(self.residuals, self.enabledStartParameters(parameters, bounded=True),
                                                                                                 args=(y, x, sigma), epsfcn=self.epsfcn, full_output=True, bounds=myEnabledBounds)
        else:
            enabledOnlyParameters, cov_x, infodict, self.mesg, self.ier = leastsq(self.residuals, self.enabledStartParameters(parameters), args=(y, x, sigma),
                                                                                            epsfcn=self.epsfcn, full_output=True)
        self.setEnabledFitParameters(enabledOnlyParameters)
        self.update(self.parameters)
        logger.info( "chisq {0}".format( sum(infodict["fvec"]*infodict["fvec"]) ) )        
        
        # calculate final chi square
        self.chisq=sum(infodict["fvec"]*infodict["fvec"])
        
        self.dof = max( len(x)-len(parameters), 1)
        RMSres = Q(sqrt(self.chisq/self.dof))
        RMSres.significantDigits = 3
        self.results['RMSres'].value = RMSres
        # chisq, sqrt(chisq/dof) agrees with gnuplot
        logger.info(  "success {0} {1}".format( self.ier, self.mesg ) )
        logger.info(  "Converged with chi squared {0}".format(self.chisq) )
        logger.info(  "degrees of freedom, dof {0}".format( self.dof ) )
        logger.info(  "RMS of residuals (i.e. sqrt(chisq/dof)) {0}".format( RMSres ) )
        logger.info(  "Reduced chisq (i.e. variance of residuals) {0}".format( self.chisq/self.dof ) )
        
        # uncertainties are calculated as per gnuplot, "fixing" the result
        # for non unit values of the reduced chisq.
        # values at min match gnuplot
        enabledParameterNames = self.enabledParameterNames()
        if cov_x is not None:
            enabledOnlyParametersConfidence = numpy.sqrt(numpy.diagonal(cov_x))*sqrt(self.chisq/self.dof)
            self.setEnabledConfidenceParameters(enabledOnlyParametersConfidence)
            logger.info(  "Fitted parameters at minimum, with 68% C.I.:" )
            for i, pmin in enumerate(enabledOnlyParameters):
                logger.info(  "%2i %-10s %12f +/- %10f"%(i, enabledParameterNames[i], pmin, sqrt(max(cov_x[i, i], 0))*sqrt(self.chisq/self.dof)) )
        
            logger.info(  "Correlation matrix" )
            # correlation matrix close to gnuplot
            messagelist = ["               "]
            for i in range(len(enabledOnlyParameters)): messagelist.append( "%-10s"%(enabledParameterNames[i],) )
            logger.info( " ".join(messagelist))
            messagelist = []
            for i in range(len(enabledOnlyParameters)):
                messagelist.append( "%10s"%enabledParameterNames[i] )
                for j in range(i+1):
                    messagelist.append(  "%10f"%(cov_x[i, j]/sqrt(abs(cov_x[i, i]*cov_x[j, j])),) )
                logger.info( " ".join(messagelist))
    
                #-----------------------------------------------
        else:
            self.parametersConfidence = [None]*len(self.parametersConfidence)
 
        return self.parameters
                
    def __str__(self):
        return "; ".join([", ".join([self.name, self.functionString] + [ "{0}={1}".format(name, value) for name, value in zip(self.parameterNames, self.parameters)])])

    def setConstant(self, name, value):
        setattr(self, name, value)
        
    def update(self,parameters=None):
        self.parametersUpdated.fire( values=self.replacementDict() )
    
    def toXmlElement(self, parent):
        myroot  = ElementTree.SubElement(parent, 'FitFunction', {'name': self.name, 'functionString': self.functionString})
        for name, value, confidence, enabled, startExpression, bounds, boundsexpression in zip_longest(self.parameterNames, self.parameters, self.parametersConfidence, self.parameterEnabled, self.startParameterExpressions, self.parameterBounds, self.parameterBoundsExpressions):
            e = ElementTree.SubElement( myroot, 'Parameter', {'name':name, 'confidence':repr(confidence), 'enabled': str(enabled), 'startExpression': str(startExpression), 'bounds': ",".join(map(str, bounds)),
                                                              'boundsExpression': ",".join(map(str, boundsexpression))})
            e.text = str(value)
        for result in list(self.results.values()):
            e = ElementTree.SubElement( myroot, 'Result', {'name':result.name, 'definition':str(result.definition)})
            e.text = str(result.value)
        return myroot

    def toHdf5(self, group):
        fitfunction_group = group.require_group('fitfunction')
        fitfunction_group.attrs['name'] = self.name
        fitfunction_group.attrs['functionString'] = self.functionString
        parameter_group = fitfunction_group.require_group('parameters')
        for index, (name, value, confidence, enabled, startExpression, bounds, boundsexpression) in enumerate(zip_longest(self.parameterNames, self.parameters, self.parametersConfidence, self.parameterEnabled, self.startParameterExpressions, self.parameterBounds, self.parameterBoundsExpressions)):
            g = parameter_group.require_group(name)
            g.attrs['confidence'] = confidence
            g.attrs['enabled'] = enabled
            g.attrs['startExpression'] = str(startExpression)
            g.attrs['bounds'] = bounds
            g.attrs['boundsExpression'] = ",".join(map(str, boundsexpression))
            g.attrs['value'] = value
            g.attrs['index'] = index
        results_group =  fitfunction_group.require_group('results')
        for result in list(self.results.values()):
            g = results_group.requie_group(result.name)
            g.attrs['definition'] = str(result.definition)
            g.attrs['value'] = repr(result.value)

    def residuals(self, p, y, x, sigma):
        p = self.allFitParameters(p)
        if sigma is not None:
            return (y-self.functionEval(x, *p))/sigma
        else:
            return y-self.functionEval(x, *p)
        
    def value(self,x,p=None):
        p = self.parameters if p is None else p
        return self.functionEval(x, *p )

    def replacementDict(self):
        replacement = dict(list(zip(self.parameterNames, self.parameters)))
        replacement.update( dict( ( (v.name, v.value) for v in list(self.results.values()) ) ) )
        return replacement
    
        
        
