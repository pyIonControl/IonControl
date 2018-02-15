# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

"""
Algorithms to evaluate the observed counts from a sequence of experiments:
This is used for simple averaging but also for different state detection algorithms

algorithms are expected to defined the fileds as stated in MeanEvaluation

"""
import math
from collections import Counter
from itertools import repeat

import numpy

from gui.ExpressionValue import ExpressionValue
from modules.quantity import Q
from scan.EvaluationBase import EvaluationBase, EvaluationException, EvaluationResult
from uiModules.ParameterTable import Parameter
from modules.Expression import Expression
from modules.enum import enum
from modules.SequenceDict import SequenceDict

class MeanEvaluation(EvaluationBase):
    name = 'Mean'
    tooltip = "Mean of observed counts" 
    errorBarTypes = ['shotnoise','statistical','min max']
    expression = Expression()
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        self.errorBarTypeLookup = {'shotnoise': self.evaluateShotnoise,
                                   'statistical': self.evaluateStatistical,
                                   'min max': self.evaluateMinMax}
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('errorBarType', 'shotnoise')
        self.settings.setdefault('transformation', "")
        self.settings.setdefault('timestamp_id', 0)
        if type(self.settings['errorBarType']) in (int, float):
            self.settings['errorBarType'] = self.errorBarTypes[self.settings['errorBarType']]
         
    def evaluateShotnoise(self, countarray ):
        summe = numpy.sum(numpy.array(countarray, dtype=numpy.int64))
        l = float(len(countarray))
        mean = summe/l
        stderror = math.sqrt(max(summe, 1))/l  # 1 l
        return EvaluationResult(mean, (stderror/2. if summe>0 else 0, stderror/2.), summe)

    def evaluateStatistical(self, countarray):
        mean = numpy.mean(countarray)
        stderr = numpy.std( countarray, ddof=1 ) / math.sqrt( max( len(countarray)-1, 1) )
        return EvaluationResult(mean, (stderr/2., stderr/2.), numpy.sum(countarray))
    
    def evaluateMinMax(self, countarray):
        mean = numpy.mean(countarray)
        return EvaluationResult(mean, (mean-numpy.min(countarray), numpy.max(countarray)-mean), numpy.sum(countarray))
    
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None):
        countarray = evaluation.getChannelData(data)
        if not countarray:
            return EvaluationResult()
        countarray = list(map(self.intConversionsLookup.get(self.settings['intConversion'], lambda x: x), countarray))
        r = self.errorBarTypeLookup[self.settings['errorBarType']](countarray)
        bottom, top = r.interval
        if self.settings['transformation']!="":
            mydict = { 'y': r.value }
            if ppDict:
                mydict.update( ppDict )
            mean = float(self.expression.evaluate(self.settings['transformation'], mydict))
            mydict['y'] = mean + top
            plus = float(self.expression.evaluate(self.settings['transformation'], mydict))
            mydict['y'] = mean - bottom
            minus = float(self.expression.evaluate(self.settings['transformation'], mydict))
            return EvaluationResult(mean, (mean-minus, plus-mean), r.raw)
        return r

    def parameters(self):
        parameterDict = super(MeanEvaluation, self).parameters()
        if isinstance(self.settings['errorBarType'], int): #preserve backwards compatibility -- previously errorBarType was an int, now it's a string, so we map it over
            self.settings['errorBarType'] = self.errorBarTypes[self.settings['errorBarType']]
        parameterDict['errorBarType'] = Parameter(name='errorBarType', dataType='select',
                                                  choices=self.errorBarTypes, value=self.settings['errorBarType'])
        parameterDict['transformation'] = Parameter(name='transformation', dataType='str',
                                                    value=self.settings['transformation'], tooltip="use y for the result in a mathematical expression")
        parameterDict['timestamp_id'] = Parameter(name='timestamp_id', dataType='magnitude',
                                                  value=self.settings['timestamp_id'])
        return parameterDict

    def detailEvaluate(self, data, evaluation, ppDict=None, globalDict=None):
        countarray = evaluation.getChannelData(data)
        timestamps = data.timeTick.get(int(self.settings['timestamp_id']), None)
        if not timestamps:
            timestamps = data.allTimeTick
        # we will return 3-tuple of lists: value, repeats, timestamp
        # if we do not find a timestamp we will accumulate the data, otherwise send back every event
        if countarray:
            if timestamps is None or len(timestamps) != len(countarray):
                mean, (minus, plus), raw, valid = self.errorBarTypeLookup[self.settings['errorBarType']](countarray)
                if self.settings['transformation'] != "":
                    mydict = {'y': mean}
                    if ppDict:
                        mydict.update(ppDict)
                    mean = float(self.expression.evaluate(self.settings['transformation'], mydict))
                if timestamps:
                    avg_time = sum(timestamps) // len(timestamps)
                else:
                    avg_time = data.creationTimeNs
                return [mean], [avg_time]
            else:
                if self.settings['transformation'] != "":
                    mydict = dict()
                    if ppDict:
                        mydict.update(ppDict)
                    values = list()
                    for value in countarray:
                        mydict['y'] = value
                        values.append(float(self.expression.evaluate(self.settings['transformation'], mydict)))
                else:
                    values = countarray
                return values, timestamps
        return [], []

class NumberEvaluation(EvaluationBase):
    name = 'Number'
    tooltip = "Number of results" 
    sourceType = enum('Counter','Result')
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None):
        countarray = evaluation.getChannelData(data)
        if not countarray:
            return EvaluationResult()
        return EvaluationResult(len(countarray), raw=len(countarray))

class FeedbackEvaluation(EvaluationBase):
    name = 'Feedback'
    tooltip = "Slow feedback on external parameter" 
    sourceType = enum('Counter','Result')
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        self.integrator = None
        self.lastUpdate = None
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('SetPoint', Q(0))
        self.settings.setdefault('P', Q(0))
        self.settings.setdefault('I', Q(0))
        self.settings.setdefault('AveragingTime', Q(10, 's'))
        self.settings.setdefault('GlobalVariable', "")
        self.settings.setdefault('Reset', False)

    def __setstate__(self, state):
        self.__dict__ = state

    def evaluateMinMax(self, countarray):
        mean = numpy.mean( countarray )
        return EvaluationResult(mean, (mean-numpy.min(countarray), numpy.max(countarray)-mean), numpy.sum(countarray))

    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None):
        countarray = evaluation.getChannelData(data)
        globalName = self.settings['GlobalVariable']
        if not countarray:
            return EvaluationResult()
        r = self.evaluateMinMax(countarray)
        if not globalDict or globalName not in globalDict:
            return r
        if self.integrator is None or self.settings['Reset']:
            self.integrator = globalDict[globalName]
            self.settings['Reset'] = False
        errorval = self.settings['SetPoint'].m - r.value
        pOut = self.settings['P'] * errorval
        self.integrator = self.integrator + errorval * self.settings['I'] 
        totalOut = pOut + self.integrator
        globalDict[globalName] = totalOut.to(globalDict[globalName])
        return EvaluationResult(float(totalOut.m), (0.0, 0.0), r.raw)

    def parameters(self):
        parameterDict = super(FeedbackEvaluation, self).parameters()
        if isinstance(self.settings['SetPoint'], ExpressionValue):
            self.settings['SetPoint'] = self.settings['SetPoint'].value
        tooltipLookup = SequenceDict([ ('SetPoint', 'Set point of PI loop'),
                                       ('P', 'Proportional gain'),
                                       ('I', 'Integral gain'),
                                       ('AveragingTime', 'Time spent accumulating data before updating the servo output') ])
        for name, tooltip in tooltipLookup.items():
            parameterDict[name] = Parameter(name=name, dataType='magnitude', value=self.settings[name],
                                            text=self.settings.get( (name, 'text') ), tooltip=tooltip)
        parameterDict['GlobalVariable'] = Parameter(name='GlobalVariable', dataType='select', value=self.settings['GlobalVariable'],
                                                    choices=sorted(self.globalDict.keys()), tooltip="Name of variable to which servo output value should be pushed")
        parameterDict['Reset'] = Parameter(name='Reset', dataType='bool', value=self.settings['Reset'], tooltip="Reset integrator")
        return parameterDict


class ThresholdEvaluation(EvaluationBase):
    """
    simple threshold state detection: if more than threshold counts are observed 
    the ion is considered bright. For threshold photons or less it is considered
    dark.
    """
    name = "Threshold"
    tooltip = "Above threshold is bright"
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('threshold',1)
        self.settings.setdefault('invert',False)
        self.settings.setdefault('timestamp_id', 0)
        self.settings.setdefault('color_box_plot', False)

    def _evaluate(self, data, evaluation, countarray):
        if evaluation.name in data.evaluated:
            return data.evaluated[evaluation.name]
        if self.settings['invert']:
            discriminated = [ 0 if count > self.settings['threshold'] else 1 for count in countarray ]
        else:
            discriminated = [ 1 if count > self.settings['threshold'] else 0 for count in countarray ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        return discriminated


    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        countarray = evaluation.getChannelData(data)
        if not countarray:
            return EvaluationResult()
        N = float(len(countarray))
        discriminated = self._evaluate(data, evaluation, countarray)
        x = numpy.sum( discriminated )
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0            
        return EvaluationResult(p, (p-bottom, top-p), x)

    def qubitEvaluate(self, data, evaluation, ppDict=None, globalDict=None):
        countarray = evaluation.getChannelData(data)
        timestamps = data.timeTick.get(int(self.settings['timestamp_id']), None)
        # we will return 3-tuple of lists: value, repeats, timestamp
        # if we do not find a timestamp we will accumulate the data, otherwise send back every event
        discriminated = self._evaluate(data, evaluation, countarray)
        if timestamps is None or len(timestamps) != len(countarray):
            c = Counter(discriminated)
            return c.keys(), c.values(), repeat(data._creationTime, len(c))
        else:
            return discriminated, [1]*len(discriminated), timestamps

    def parameters(self):
        parameterDict = super(ThresholdEvaluation, self).parameters()
        name='threshold'
        parameterDict[name] = Parameter(name=name, dataType='magnitude',
                                        value=self.settings[name], text=self.settings.get( (name, 'text') ),
                                        tooltip='Threshold evaluation (the threshold value itself is excluded)')
        parameterDict['invert'] = Parameter(name='invert', dataType='bool', value=self.settings['invert'])
        parameterDict['timestamp_id'] = Parameter(name='timestamp_id', dataType='magnitude', value=self.settings['timestamp_id'])
        parameterDict['color_box_plot'] = Parameter(name='color_box_plot', dataType='bool', value=self.settings['color_box_plot'])
        return parameterDict

class RangeEvaluation(EvaluationBase):
    """Evaluate the number of counts that occur in a specified range"""
    name = "Count Range"
    tooltip = ""
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('min',0)
        self.settings.setdefault('max',1)
        self.settings.setdefault('invert',False)
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        countarray = evaluation.getChannelData(data)
        if not countarray:
            return EvaluationResult()
        N = float(len(countarray))
        if self.settings['invert']:
            discriminated = [ 0 if self.settings['min'] <= count <= self.settings['max'] else 1 for count in countarray ]
        else:
            discriminated = [ 1 if self.settings['min'] <= count <= self.settings['max'] else 0 for count in countarray ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = numpy.sum( discriminated )
        p = float(x)/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        # caution: not applicable to this situation, needs to be fixed
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0            
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(RangeEvaluation, self).parameters()
        tooltipLookup = SequenceDict([ ('min', 'Range minimum (inclusive)'),
                                       ('max', 'Range maximum (inclusive)') ])
        for name, tooltip in tooltipLookup.items():
            parameterDict[name] = Parameter(name=name, dataType='magnitude', value=self.settings[name],
                                            text=self.settings.get( (name, 'text') ), tooltip=tooltip)
        parameterDict['invert'] = Parameter(name='invert', dataType='bool', value=self.settings['invert'])
        return parameterDict

class DoubleRangeEvaluation(EvaluationBase):
    """Evaluate the number of counts that occur in two specified ranges"""
    name = "Double Count Range"
    tooltip = ""
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('min_1',0)
        self.settings.setdefault('max_1',1)
        self.settings.setdefault('min_2',0)
        self.settings.setdefault('max_2',1)
        self.settings.setdefault('invert',False)
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        countarray = evaluation.getChannelData(data)
        if not countarray:
            return EvaluationResult()
        N = float(len(countarray))
        if self.settings['invert']:
            discriminated = [ 0 if ( self.settings['min_1'] <= count <= self.settings['max_1'] ) or
                             ( self.settings['min_2'] <= count <= self.settings['max_2'] )  else 1 for count in countarray ]
        else:
            discriminated = [ 1 if ( self.settings['min_1'] <= count <= self.settings['max_1'] ) or
                             ( self.settings['min_2'] <= count <= self.settings['max_2'] )  else 0 for count in countarray ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = numpy.sum( discriminated )
        p = float(x)/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        # caution: not applicable to this situation, needs to be fixed
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0            
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(DoubleRangeEvaluation, self).parameters()
        tooltipLookup = SequenceDict([ ('min_1', 'Range minimum 1 (inclusive)'),
                                       ('max_1', 'Range maximum 1 (inclusive)'),
                                       ('min_2', 'Range minimum 2 (inclusive)'),
                                       ('max_2', 'Range maximum 2 (inclusive)') ])
        for name, tooltip in tooltipLookup.items():
            parameterDict[name] = Parameter(name=name, dataType='magnitude', value=self.settings[name],
                                            text=self.settings.get( (name, 'text') ), tooltip=tooltip)
        parameterDict['invert'] = Parameter(name='invert', dataType='bool', value=self.settings['invert'])
        return parameterDict

class FidelityEvaluation(EvaluationBase):
    """
    simple threshold state detection: if more than threshold counts are observed 
    the ion is considered bright. For threshold photons or less it is considered
    dark.
    In addition it receives the expected state and calculates the fidelity
    """
    name = "Fidelity"
    tooltip = "Above threshold is bright"
    ExpectedLookup = { 'd': 0, 'u' : 1, '1':0.5, '-1':0.5, 'i':0.5, '-i':0.5 }
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('threshold',1)
        self.settings.setdefault('invert',False)
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        countarray = evaluation.getChannelData(data)
        if not countarray:
            return EvaluationResult()
        N = float(len(countarray))
        if self.settings['invert']:
            discriminated = [ 0 if count > self.settings['threshold'] else 1 for count in countarray ]
        else:
            discriminated = [ 1 if count > self.settings['threshold'] else 0 for count in countarray ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = numpy.sum( discriminated )
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0  
        if expected is not None:
            expected = self.ExpectedLookup[expected]
            p = abs(expected-p)
            bottom = abs(expected-bottom)
            top = abs(expected-top)
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(FidelityEvaluation, self).parameters()
        name='threshold'
        parameterDict[name] = Parameter(name=name, dataType='magnitude',
                                        value=self.settings[name], text=self.settings.get( (name, 'text') ),
                                        tooltip='Threshold evaluation (the threshold value itself is excluded)')
        parameterDict['invert'] = Parameter(name='invert', dataType='bool', value=self.settings['invert'])
        return parameterDict

class ParityEvaluation(EvaluationBase):
    """Evaluates the parity, given individual ion signals ion_1 and ion_2"""
    name = "Parity"
    tooltip = "Two ion parity evaluation"
    hasChannel = False
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('Ion_1','')
        self.settings.setdefault('Ion_2','')

    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        name1, name2 = self.settings['Ion_1'], self.settings['Ion_2']
        eval1, eval2 = data.evaluated.get(name1), data.evaluated.get(name2) 
        if eval1 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name1))
        if eval2 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name2))
        if len(eval1)!=len(eval2):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval2)))
        N = float(len(eval1))
        discriminated = [ 1 if e1==e2 else -1 for e1, e2 in zip(eval1, eval2) ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = numpy.sum( discriminated )
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0  
        if expected is not None:
            p = abs(expected-p)
            bottom = abs(expected-bottom)
            top = abs(expected-top)
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(ParityEvaluation, self).parameters()
        parameterDict['Ion_1'] = Parameter(name='Ion_1', dataType='str', value=self.settings['Ion_1'], tooltip='The evaluation for ion 1')
        parameterDict['Ion_2'] = Parameter(name='Ion_2', dataType='str', value=self.settings['Ion_2'], tooltip='The evaluation for ion 2')
        return parameterDict

class TwoIonEvaluation(EvaluationBase):
    """Combines two individual ion evaluations using coefficients on the four possible state (dd, db, bd, and bb)"""
    name = "TwoIon"
    tooltip = "Two ion parity evaluation"
    hasChannel = False
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        
    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('Ion_1','')
        self.settings.setdefault('Ion_2','')
        self.settings.setdefault('dd',1)
        self.settings.setdefault('db',-1)
        self.settings.setdefault('bd',-1)
        self.settings.setdefault('bb',1)
        
    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        name1, name2 = self.settings['Ion_1'], self.settings['Ion_2']
        eval1, eval2 = data.evaluated.get(name1), data.evaluated.get(name2) 
        if eval1 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name1))
        if eval2 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name2))
        if len(eval1)!=len(eval2):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval2)))
        N = float(len(eval1))
        lookup = {(0,0): self.settings['dd'], (0,1): self.settings['db'], (1,0): self.settings['bd'], (1,1):self.settings['bb'] }
        discriminated = [ lookup[pair] for pair in zip(eval1, eval2) ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = float(numpy.sum( discriminated )) # Float converts type "magnitude" to float so as to not break plotting (numpy.isnan fails)
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0  
        if expected is not None:
            p = abs(expected-p)
            bottom = abs(expected-bottom)
            top = abs(expected-top)
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(TwoIonEvaluation, self).parameters()
        parameterDict['Ion_1'] = Parameter(name='Ion_1', dataType='str', value=self.settings['Ion_1'], tooltip='The evaluation for ion 1')
        parameterDict['Ion_2'] = Parameter(name='Ion_2', dataType='str', value=self.settings['Ion_2'], tooltip='The evaluation for ion 2')
        tooltipLookup = SequenceDict([ ('dd', 'multiplier for dd'),
                                       ('db', 'multiplier for db'),
                                       ('bd', 'multiplier for bd'),
                                       ('bb', 'multiplier for bb') ])
        for name, tooltip in tooltipLookup.items():
            parameterDict[name] = Parameter(name=name, dataType='magnitude', value=self.settings[name],
                                            text=self.settings.get( (name, 'text') ), tooltip=tooltip)
        return parameterDict

class CounterSumMeanEvaluation(EvaluationBase):
    """Evaluate the mean of a sum of counters"""
    name = 'Counter Sum Mean'
    tooltip = "Mean of sum of observed counts"
    hasChannel = False
    errorBarTypes = ['shotnoise', 'statistical', 'min max']
    expression = Expression()

    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)
        self.errorBarTypeLookup = {'shotnoise': self.evaluateShotnoise,
                                   'statistical': self.evaluateStatistical,
                                   'min max': self.evaluateMinMax}

    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('errorBarType', 'shotnoise')
        self.settings.setdefault('transformation', "")
        self.settings.setdefault('counters', [])
        self.settings.setdefault('id', 0)

    def evaluateShotnoise(self, countarray):
        summe = numpy.sum(countarray)
        l = float(len(countarray))
        mean = summe / l
        stderror = math.sqrt(max(summe, 1)) / l
        return mean, (stderror / 2. if summe > 0 else 0, stderror / 2.), summe

    def evaluateStatistical(self, countarray):
        mean = numpy.mean(countarray)
        stderr = numpy.std(countarray, ddof=1) / math.sqrt(max(len(countarray) - 1, 1))
        return EvaluationResult(mean, (stderr / 2., stderr / 2.), numpy.sum(countarray))

    def evaluateMinMax(self, countarray):
        mean = numpy.mean(countarray)
        return EvaluationResult(mean, (mean - numpy.min(countarray), numpy.max(countarray) - mean), numpy.sum(countarray))

    def getCountArray(self, data):
        counters = [((self.settings['id']&0xff)<<8) | (int(counter) & 0xff) for counter in self.settings['counters']]
        listOfCountArrays = [data.count[counter] for counter in counters if counter in data.count.keys()]
        countarray = [sum(sublist) for sublist in zip(*listOfCountArrays)]
        return countarray

    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None):
        countarray = self.getCountArray(data)
        if not countarray:
            return EvaluationResult()
        r = self.errorBarTypeLookup[self.settings['errorBarType']](countarray)
        bottom, top = r.interval
        if self.settings['transformation'] != "":
            mydict = {'y': r.value}
            if ppDict:
                mydict.update(ppDict)
            mean = float(self.expression.evaluate(self.settings['transformation'], mydict))
            mydict['y'] = mean + top
            plus = float(self.expression.evaluate(self.settings['transformation'], mydict))
            mydict['y'] = mean - bottom
            minus = float(self.expression.evaluate(self.settings['transformation'], mydict))
            return EvaluationResult(mean, (mean - minus, plus - mean), r.raw)
        return r

    def histogram(self, data, evaluation, histogramBins=50 ):
        countarray = self.getCountArray(data)
        y, x = numpy.histogram( countarray, range=(0, histogramBins), bins=histogramBins)
        return y, x, None   # third parameter is optional function

    def parameters(self):
        parameterDict = super(CounterSumMeanEvaluation, self).parameters()
        parameterDict['id'] = Parameter(name='id', dataType='magnitude', value=self.settings['id'],
                                        text=self.settings.get( ('id', 'text') ), tooltip='id of counters to sum')
        parameterDict['counters'] = Parameter(name='counters', dataType='multiselect',
                                              value=self.settings['counters'], choices=list(map(str, range(16))),
                                              tooltip='counters to sum')
        parameterDict['errorBarType'] = Parameter(name='errorBarType', dataType='select',
                                                  choices=self.errorBarTypes, value=self.settings['errorBarType'])
        parameterDict['transformation'] = Parameter(name='transformation', dataType='str',
                                                    value=self.settings['transformation'],
                                                    tooltip="use y for the result in a mathematical expression")
        return parameterDict

class CounterSumThresholdEvaluation(EvaluationBase):
    """
    simple threshold state detection: if more than threshold counts are observed
    the ion is considered bright. For threshold photons or less it is considered
    dark. Evaluated on a sum of counters.
    """
    name = "Counter Sum Threshold"
    tooltip = "Above threshold is bright"
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)

    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('threshold',1)
        self.settings.setdefault('invert',False)
        self.settings.setdefault('counters', [])
        self.settings.setdefault('id', 0)

    def getCountArray(self, data):
        counters = [((self.settings['id']&0xff)<<8) | (int(counter) & 0xff) for counter in self.settings['counters']]
        listOfCountArrays = [data.count[counter] for counter in counters if counter in data.count.keys()]
        countarray = [sum(sublist) for sublist in zip(*listOfCountArrays)]
        return countarray

    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        countarray = self.getCountArray(data)
        if not countarray:
            return EvaluationResult()
        N = float(len(countarray))
        if self.settings['invert']:
            discriminated = [ 0 if count > self.settings['threshold'] else 1 for count in countarray ]
        else:
            discriminated = [ 1 if count > self.settings['threshold'] else 0 for count in countarray ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = numpy.sum( discriminated )
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(CounterSumThresholdEvaluation, self).parameters()
        parameterDict['id'] = Parameter(name='id', dataType='magnitude', value=self.settings['id'],
                                        text=self.settings.get( ('id', 'text') ), tooltip='id of counters to sum')
        parameterDict['counters'] = Parameter(name='counters', dataType='multiselect',
                                              value=self.settings['counters'], choices=list(map(str, range(16))),
                                              tooltip='counters to sum')
        name='threshold'
        parameterDict[name] = Parameter(name=name, dataType='magnitude',
                                        value=self.settings[name], text=self.settings.get( (name, 'text') ),
                                        tooltip='Threshold evaluation (the threshold value itself is excluded)')
        parameterDict['invert'] = Parameter(name='invert', dataType='bool', value=self.settings['invert'])
        return parameterDict


class ThreeIonEvaluation(EvaluationBase):
    """Straightforward extension of two ion eval to three ions using coefficients on the nine possible states"""
    name = "ThreeIon"
    tooltip = "Three ion evaluation"
    hasChannel = False
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)

    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('Ion_1','')
        self.settings.setdefault('Ion_2','')
        self.settings.setdefault('Ion_3','')
        self.settings.setdefault('---',1)
        self.settings.setdefault('--o',0)
        self.settings.setdefault('-o-',0)
        self.settings.setdefault('o--',0)
        self.settings.setdefault('oo-',0)
        self.settings.setdefault('o-o',0)
        self.settings.setdefault('-oo',0)
        self.settings.setdefault('ooo',0)

    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        name1, name2, name3 = self.settings['Ion_1'], self.settings['Ion_2'], self.settings['Ion_3']
        eval1, eval2, eval3 = data.evaluated.get(name1), data.evaluated.get(name2), data.evaluated.get(name3)

        if eval1 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name1))
        if eval2 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name2))
        if eval3 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name3))

        if len(eval1)!=len(eval2):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval2)))
        if len(eval1)!=len(eval3):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval3)))
        if len(eval2)!=len(eval3):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval2),len(eval3)))

        N = float(len(eval1))
        lookup = {(0,0,0): self.settings['---'],
                  (0,0,1): self.settings['--o'],
                  (0,1,0): self.settings['-o-'],
                  (1,0,0): self.settings['o--'],
                  (1,1,0): self.settings['oo-'],
                  (1,0,1): self.settings['o-o'],
                  (0,1,1): self.settings['-oo'],
                  (1,1,1): self.settings['ooo'] }
        discriminated = [ lookup[trio] for trio in zip(eval1, eval2, eval3) ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = float(numpy.sum( discriminated )) # Float converts type "magnitude" to float so as to not break plotting (numpy.isnan fails)
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0
        if expected is not None:
            p = abs(expected-p)
            bottom = abs(expected-bottom)
            top = abs(expected-top)
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(ThreeIonEvaluation, self).parameters()
        parameterDict['Ion_1'] = Parameter(name='Ion_1', dataType='str', value=self.settings['Ion_1'], tooltip='The evaluation for ion 1')
        parameterDict['Ion_2'] = Parameter(name='Ion_2', dataType='str', value=self.settings['Ion_2'], tooltip='The evaluation for ion 2')
        parameterDict['Ion_3'] = Parameter(name='Ion_3', dataType='str', value=self.settings['Ion_3'], tooltip='The evaluation for ion 3')
        tooltipLookup = SequenceDict([ ('---', 'multiplier for --- (3 ions dark)'),
                                       ('--o', 'multiplier for --o'),
                                       ('-o-', 'multiplier for -o-'),
                                       ('o--', 'multiplier for o--'),
                                       ('oo-', 'multiplier for oo-'),
                                       ('o-o', 'multiplier for o-o'),
                                       ('-oo', 'multiplier for -oo'),
                                       ('ooo', 'multiplier for ooo') ])
        for name, tooltip in tooltipLookup.items():
            parameterDict[name] = Parameter(name=name, dataType='magnitude', value=self.settings[name],
                                            text=self.settings.get( (name, 'text') ), tooltip=tooltip)
        return parameterDict

class FourIonEvaluation(EvaluationBase):
    """Straightforward extension of two ion eval to four ions using coefficients on the sixteen possible states"""
    name = "FourIon"
    tooltip = "Four ion evaluation"
    hasChannel = False
    def __init__(self, globalDict=None, settings=None):
        EvaluationBase.__init__(self, globalDict, settings)

    def setDefault(self):
        super().setDefault()
        self.settings.setdefault('Ion_1','')
        self.settings.setdefault('Ion_2','')
        self.settings.setdefault('Ion_3','')
        self.settings.setdefault('Ion_4','')
        self.settings.setdefault('----',1)
        self.settings.setdefault('o---',1)
        self.settings.setdefault('-o--',1)
        self.settings.setdefault('--o-',1)
        self.settings.setdefault('---o',1)
        self.settings.setdefault('oo--',1)
        self.settings.setdefault('o-o-',1)
        self.settings.setdefault('o--o',1)
        self.settings.setdefault('-oo-',1)
        self.settings.setdefault('-o-o',1)
        self.settings.setdefault('--oo',1)
        self.settings.setdefault('ooo-',1)
        self.settings.setdefault('oo-o',1)
        self.settings.setdefault('o-oo',1)
        self.settings.setdefault('-ooo',1)
        self.settings.setdefault('oooo',1)

    def evaluate(self, data, evaluation, expected=None, ppDict=None, globalDict=None ):
        name1, name2, name3, name4 = self.settings['Ion_1'], self.settings['Ion_2'], self.settings['Ion_3'], self.settings['Ion_4']
        eval1, eval2, eval3, eval4 = data.evaluated.get(name1), data.evaluated.get(name2), data.evaluated.get(name3),data.evaluated.get(name4)

        if eval1 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name1))
        if eval2 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name2))
        if eval3 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name3))
        if eval4 is None:
            raise EvaluationException("Cannot find data '{0}'".format(name4))

        if len(eval1)!=len(eval2):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval2)))
        if len(eval1)!=len(eval3):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval3)))
        if len(eval2)!=len(eval3):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval2),len(eval3)))
        if len(eval1)!=len(eval4):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval1),len(eval4)))
        if len(eval2)!=len(eval4):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval2),len(eval4)))
        if len(eval3)!=len(eval4):
            raise EvaluationException("Evaluated arrays have different length {0}, {1}".format(len(eval3),len(eval4)))

        N = float(len(eval1))
        lookup = {(0,0,0,0): self.settings['----'],
                  (1,0,0,0): self.settings['o---'],
                  (0,1,0,0): self.settings['-o--'],
                  (0,0,1,0): self.settings['--o-'],
                  (0,0,0,1): self.settings['---o'],
                  (1,1,0,0): self.settings['oo--'],
                  (1,0,1,0): self.settings['o-o-'],
                  (1,0,0,1): self.settings['o--o'],
                  (0,1,1,0): self.settings['-oo-'],
                  (0,1,0,1): self.settings['-o-o'],
                  (0,0,1,1): self.settings['--oo'],
                  (1,1,1,0): self.settings['ooo-'],
                  (1,1,0,1): self.settings['oo-o'],
                  (1,0,1,1): self.settings['o-oo'],
                  (0,1,1,1): self.settings['-ooo'],
                  (1,1,1,1): self.settings['oooo'] }
        discriminated = [ lookup[quartet] for quartet in zip(eval1, eval2, eval3, eval4) ]
        if evaluation.name:
            data.evaluated[evaluation.name] = discriminated
        x = float(numpy.sum( discriminated )) # Float converts type "magnitude" to float so as to not break plotting (numpy.isnan fails)
        p = x/N
        # Wilson score interval with continuity correction
        # see http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
        rootp = 3-1/N -4*p+4*N*(1-p)*p
        top = min( 1, (2 + 2*N*p + math.sqrt(rootp))/(2*(N+1)) ) if rootp>=0 else 1
        rootb = -1-1/N +4*p+4*N*(1-p)*p
        bottom = max( 0, (2*N*p - math.sqrt(rootb))/(2*(N+1)) ) if rootb>=0 else 0
        if expected is not None:
            p = abs(expected-p)
            bottom = abs(expected-bottom)
            top = abs(expected-top)
        return EvaluationResult(p, (p-bottom, top-p), x)

    def parameters(self):
        parameterDict = super(FourIonEvaluation, self).parameters()
        parameterDict['Ion_1'] = Parameter(name='Ion_1', dataType='str', value=self.settings['Ion_1'], tooltip='The evaluation for ion 1')
        parameterDict['Ion_2'] = Parameter(name='Ion_2', dataType='str', value=self.settings['Ion_2'], tooltip='The evaluation for ion 2')
        parameterDict['Ion_3'] = Parameter(name='Ion_3', dataType='str', value=self.settings['Ion_3'], tooltip='The evaluation for ion 3')
        parameterDict['Ion_4'] = Parameter(name='Ion_4', dataType='str', value=self.settings['Ion_4'], tooltip='The evaluation for ion 4')
        tooltipLookup = SequenceDict([ ('----', 'multiplier for ---- (4 ions dark)'),
                                       ('o---', 'multiplier for o---'),
                                       ('-o--', 'multiplier for -o--'),
                                       ('--o-', 'multiplier for --o-'),
                                       ('---o', 'multiplier for ---o'),
                                       ('oo--', 'multiplier for oo--'),
                                       ('o-o-', 'multiplier for o-o-'),
                                       ('o--o', 'multiplier for o--o'),
                                       ('-oo-', 'multiplier for -oo-'),
                                       ('-o-o', 'multiplier for -o-o'),
                                       ('--oo', 'multiplier for --oo'),
                                       ('ooo-', 'multiplier for ooo-'),
                                       ('oo-o', 'multiplier for oo-o'),
                                       ('o-oo', 'multiplier for o-oo'),
                                       ('-ooo', 'multiplier for -ooo'),
                                       ('oooo', 'multiplier for oooo (4 ions bright)') ])
        for name, tooltip in tooltipLookup.items():
            parameterDict[name] = Parameter(name=name, dataType='magnitude', value=self.settings[name],
                                            text=self.settings.get( (name, 'text') ), tooltip=tooltip)
        return parameterDict
