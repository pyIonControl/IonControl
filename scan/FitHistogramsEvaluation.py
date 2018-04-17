# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from modules.quantity import Q
from .EvaluationBase import EvaluationBase, EvaluationResult
import numpy
import logging
from scipy.optimize import leastsq
from math import sqrt
from trace.TraceCollection import TraceCollection
import lxml.etree as ElementTree
from itertools import zip_longest
from copy import deepcopy
from os import path
from uiModules.ParameterTable import Parameter

class HistogramFitFunction:
    name = "HistogramApproximation"
    functionString = "p0*H(0)+p1*H(1)+p2*H(2)"
    def __init__(self):
        self.param = (0, 0, 0)
        self.totalCounts = 1
    
    def value(self, x):
        return self.functionEval(x, self.param) * self.totalCounts
    
    def functionEval(self, x, p ):
        return numpy.array( [ p[0] * self.ZeroBright[el] + p[1] * self.OneBright[el] + (1-p[0]-p[1]) * self.TwoBright[el] for el in x.astype(int) ] )

    def residuals(self, p, y, x):
        penalty = 0
        if p[0]<0:
            penalty += abs(p[0])*1
        if p[0]>1:
            penalty += (p[0]-1)*1
        if p[1]<0:
            penalty += abs(p[1])*1
        if p[1]>1:
            penalty += (p[1]-1)*1
        if p[0]+p[1]>1:
            penalty += (p[0]+p[1]-1)*1  
        return y-self.functionEval(x, p)+penalty

    def toXmlElement(self, parent):
        myroot  = ElementTree.SubElement(parent, 'FitFunction', {'name': self.name, 'functionString': self.functionString})
        for name, value in zip_longest(["p0", "p1", "p2", "totalCounts"], self.param+[self.totalCounts]):
            e = ElementTree.SubElement( myroot, 'Parameter', {'name':name, 'enabled': str(True)})
            e.text = str(value)
        return myroot
 
class FitHistogramEvaluation(EvaluationBase):
    """Evaluation which fits histograms to two ion data to determine populations in zero, one, and two bright.
    Runs in five different modes:
    Zero: Will return the population in 00
    One: Will return the population in 01 + 10
    Two: Will return the population in 11
    Parity: Will return the value of P_00 + P_11 - (P_01 + P_10)
    Residuals: Will return the goodness of histogram fit
    """
    name = "FitHistogram"
    tooltip = "Fit measured histograms to data"
    modes = ['Zero', 'One', 'Two', 'Parity', 'Residuals']
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        self.epsfcn=0.0
        self.fitFunction = HistogramFitFunction()
        self.dataLoaded = False
        
    def __setstate__(self, d):
        self.__dict__ = d
        self.__dict__.setdefault('fitFunction', HistogramFitFunction())
        self.dataLoaded = False
        
    def loadReferenceData(self):
        for name in ['ZeroBright', 'OneBright', 'TwoBright']:
            filename = path.join(self.settings['Path'], self.settings[name])
            if filename:
                if path.exists(filename):
                    t = TraceCollection()
                    t.loadTrace(filename)
                    yColumnName = t.plottingList[0]._yColumn
                    setattr(self.fitFunction, name, self.normalizeHistogram(t[yColumnName]))
                else:
                    logging.getLogger(__name__).error("Reference data file '{0}' does not exist.".format(filename))
            else:
                logging.getLogger(__name__).error("Reference filename invalid.")
        self.dataLoaded = True
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('Path', r'C:\Users\Public\Documents')
        self.settings.setdefault('ZeroBright', 'ZeroBright')
        self.settings.setdefault('OneBright', 'OneBright')
        self.settings.setdefault('TwoBright', 'TwoBright')
        self.settings.setdefault('HistogramBins', 50)
        self.settings.setdefault('Mode', 'Zero')
        
    def update(self, parameter):
        super( FitHistogramEvaluation, self ).update(parameter)
        if parameter.name in ['ZeroBright', 'OneBright', 'TwoBright', 'Path']:
            self.loadReferenceData()

    def normalizeHistogram(self, hist, longOutput=False):
        hist = numpy.array(hist, dtype=float)
        histsum = numpy.sum( hist )
        return (hist / histsum, histsum) if longOutput else hist/histsum
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        if not self.dataLoaded:
            self.loadReferenceData()
        params, confidence, reducedchisq = data.evaluated['FitHistogramsResult'].get(evaluation.channelKey, (None, None, None))
        if params is None:
            countarray = evaluation.getChannelData(data)
            y, x = numpy.histogram( countarray, range=(0, self.settings['HistogramBins']), bins=self.settings['HistogramBins']) 
            y, self.fitFunction.totalCounts = self.normalizeHistogram(y, longOutput=True)
            params, confidence = self.leastsq(x[0:-1], y, [0.3, 0.3])
            params = list(params) + [ 1-params[0]-params[1] ]     # fill in the constrained parameter
            confidence = list(confidence)
            confidence.append( (confidence[0]+confidence[1]) if confidence[0] is not None and confidence[1] is not None else None)  # don't know what to do :(
            data.evaluated['FitHistogramsResult'][evaluation.channelKey] = (params, confidence, self.chisq/self.dof)
        if self.settings['Mode']=='Parity':
            return EvaluationResult(params[0]+params[2]-params[1], None, params[0]+params[2]-params[1])
        elif self.settings['Mode']=='Zero':
            return EvaluationResult(params[0], (confidence[0],  confidence[0]), params[0])
        elif self.settings['Mode']=='One':
            return EvaluationResult(params[1], (confidence[1],  confidence[1]), params[1])
        elif self.settings['Mode']=='Two':
            return EvaluationResult(params[2], (confidence[2],  confidence[2]), params[2])
        elif self.settings['Mode']=='Residuals':
            return EvaluationResult(reducedchisq, None, reducedchisq)

    def parameters(self):
        parameterDict = super(FitHistogramEvaluation, self).parameters()
        parameterDict['Path'] = Parameter(name='Path', dataType='str', value=str(self.settings['Path']), tooltip='Path for histogram files')
        parameterDict['ZeroBright'] = Parameter(name='ZeroBright', dataType='str', value=str(self.settings['ZeroBright']), tooltip='filename for ZeroBright data')
        parameterDict['OneBright'] = Parameter(name='OneBright', dataType='str', value=str(self.settings['OneBright']), tooltip='filename for OneBright data')
        parameterDict['TwoBright'] = Parameter(name='TwoBright', dataType='str', value=str(self.settings['TwoBright']), tooltip='filename for TwoBright data')
        parameterDict['HistogramBins'] = Parameter(name='HistogramBins', dataType='magnitude',
                                                   value=int(self.settings['HistogramBins']), text=self.settings.get( ('HistogramBins', 'text') ),
                                                   tooltip='Number of histogram bins in data')
        parameterDict['Mode'] = Parameter(name='Mode', dataType='select', value=str(self.settings['Mode']), choices=self.modes, tooltip='Evaluation mode')
        parameterDict['Load Reference Data'] = Parameter(name='Load Reference Data', dataType='action', value='loadReferenceData')
        return parameterDict

    def leastsq(self, x, y, parameters=None, sigma=None, filt=None):
        # TODO: Need to honor filtering
        logger = logging.getLogger(__name__)
        if parameters is None:
            parameters = [0.3, 0.3]
        
        params, cov_x, infodict, self.mesg, self.ier = leastsq(self.fitFunction.residuals, parameters, args=(y, x), epsfcn=self.epsfcn, full_output=True)
        logger.info( "chisq {0}".format( sum(infodict["fvec"]*infodict["fvec"]) ) )        
        self.fitFunction.param = params
        
        # calculate final chi square
        self.chisq=sum(infodict["fvec"]*infodict["fvec"])
        
        self.dof=len(x)-len(parameters)
        RMSres = Q(sqrt(self.chisq/self.dof))
        RMSres.significantDigits = 3
        self.RMSres = RMSres
        # chisq, sqrt(chisq/dof) agrees with gnuplot
        logger.info(  "success {0} {1}".format( self.ier, self.mesg ) )
        logger.info(  "Converged with chi squared {0}".format(self.chisq) )
        logger.info(  "degrees of freedom, dof {0}".format( self.dof ) )
        logger.info(  "RMS of residuals (i.e. sqrt(chisq/dof)) {0}".format( RMSres ) )
        logger.info(  "Reduced chisq (i.e. variance of residuals) {0}".format( self.chisq/self.dof ) )
        
        # uncertainties are calculated as per gnuplot, "fixing" the result
        # for non unit values of the reduced chisq.
        # values at min match gnuplot
        if cov_x is not None:
            self.fitFunction.parametersConfidence = numpy.sqrt(numpy.diagonal(cov_x))*sqrt(self.chisq/self.dof)
            logger.info(  "Fitted parameters at minimum, with 68% C.I.:" )
            for i, pmin in enumerate(params):
                logger.info(  "%2i %-10s %12f +/- %10f"%(i, params[i], pmin, sqrt(max(cov_x[i, i], 0))*sqrt(self.chisq/self.dof)) )
        
            logger.info(  "Correlation matrix" )
            # correlation matrix close to gnuplot
            messagelist = ["               "]
            for i in range(len(params)): messagelist.append( "%-10s"%(params[i],) )
            logger.info( " ".join(messagelist))
            messagelist = []
            for i in range(len(params)):
                messagelist.append( "%10s"%params[i] )
                for j in range(i+1):
                    messagelist.append(  "%10f"%(cov_x[i, j]/sqrt(cov_x[i, i]*cov_x[j, j]),) )
                logger.info( " ".join(messagelist))
    
                #-----------------------------------------------
        else:
            self.fitFunction.parametersConfidence = [None]*2
 
        return params, self.fitFunction.parametersConfidence

    def histogram(self, data, counter=0, histogramBins=50 ):
        y, x, _ = super(FitHistogramEvaluation, self).histogram( data, counter, histogramBins)
        return y, x, deepcopy(self.fitFunction)   # third parameter is optional function 

  
class TwoIonFidelityEvaluation(EvaluationBase):
    name = "TwoIonFidelity"
    tooltip = "Above threshold is bright"
    modes = ['Zero', 'One', 'Two', 'All']
    ExpectedLookup = { '424': [0.25, 0.5, 0.25], '202': [0.5, 0.0, 0.5], '001': [0.0, 0.0, 1.0], '100': [1.0, 0.0, 0.0] }
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        self.settings.setdefault('Path', r'C:\Users\Public\Documents')
        self.settings.setdefault('ZeroBright', 'ZeroIonHistogram')
        self.settings.setdefault('OneBright', 'OneIonHistogram')
        self.settings.setdefault('TwoBright', 'TwoIonHistogram')
        self.settings.setdefault('HistogramBins', 50)
        self.settings.setdefault('Mode', 'Zero')
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        #countarray = evaluation.getChannelData(data)
        params, confidence, reducedchisq = data.evaluated['FitHistogramsResult'].get(evaluation.channelKey, (None, None, None))
        if params is None:
            return EvaluationResult()
        elif expected is not None:
            if self.settings['Mode']=='Zero':
                p = 1.0-abs(params[0] - self.ExpectedLookup[expected][0])
                pbottom = confidence[0]
                ptop = confidence[0]
                x = params[0]
            elif self.settings['Mode']=='One':
                p = 1.0-abs(params[1] - self.ExpectedLookup[expected][1])
                pbottom = confidence[1]
                ptop = confidence[1]
                x = params[1]
            elif self.settings['Mode']=='Two':
                p = 1.0-abs(params[2] - self.ExpectedLookup[expected][2])
                pbottom = confidence[2]
                ptop = confidence[2]
                x = params[2]
            elif self.settings['Mode']=='All':
                p = 1.0-(abs(params[0] - self.ExpectedLookup[expected][0]) + abs(params[1] - self.ExpectedLookup[expected][1]) + abs(params[2] - self.ExpectedLookup[expected][2]))/3.0
                pbottom = confidence[2]
                ptop = confidence[2]
                x = params[0]+params[1]+params[2]
        else:
            return EvaluationResult()
        return EvaluationResult(p, (pbottom, ptop), x)

    def parameters(self):
        parameterDict = super(TwoIonFidelityEvaluation, self).parameters()
        parameterDict['Path'] = Parameter(name='Path', dataType='str', value=str(self.settings['Path']), tooltip='Path for histogram files')
        parameterDict['ZeroBright'] = Parameter(name='ZeroBright', dataType='str', value=str(self.settings['ZeroBright']), tooltip='filename for ZeroBright data')
        parameterDict['OneBright'] = Parameter(name='OneBright', dataType='str', value=str(self.settings['OneBright']), tooltip='filename for OneBright data')
        parameterDict['TwoBright'] = Parameter(name='TwoBright', dataType='str', value=str(self.settings['TwoBright']), tooltip='filename for TwoBright data')
        parameterDict['HistogramBins'] = Parameter(name='HistogramBins', dataType='magnitude',
                                                   value=int(self.settings['HistogramBins']), text=self.settings.get( ('HistogramBins', 'text') ),
                                                   tooltip='Number of histogram bins in data')
        parameterDict['Mode'] = Parameter(name='Mode', dataType='select', value=str(self.settings['Mode']), choices=self.modes, tooltip='Evaluation mode')
        return parameterDict