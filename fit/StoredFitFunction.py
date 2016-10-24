# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from modules.HashableDict import HashableDict
from fit.FitFunctionBase import ResultRecord
from fit.FitFunctionBase import fitFunctionMap

class StoredFitFunction(object):
    def __init__(self, name=None, fitfunctionName=None ):
        self.name = name
        self.fitfunctionName = fitfunctionName
        self.startParameters = tuple()
        self.parameters = tuple()
        self.parametersConfidence = tuple()
        self.parameterEnabled = tuple()
        self.results = HashableDict()
        self.startParameterExpressions = None
        self.useSmartStartValues = False
        self.parameterBounds = tuple()
        self.parameterBoundsExpressions = tuple()
        self.usedErrorBars = True
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault( 'parameters', tuple() )
        self.__dict__.setdefault( 'parametersConfidence', tuple() )
        self.__dict__.setdefault( 'startParameterExpressions', None )
        self.__dict__.setdefault( 'useSmartStartValues', False )
        self.__dict__.setdefault( 'parameterBounds', tuple(((None, None) for _ in range(len(self.parameters)))))
        self.__dict__.setdefault( 'parameterBoundsExpressions', tuple(((None, None) for _ in range(len(self.parameters)))))
        self.__dict__.setdefault( 'useErrorBars', True)

    def fitfunction(self):
        fitfunction = fitFunctionMap[self.fitfunctionName]()
        fitfunction.startParameters = list(self.startParameters)
        fitfunction.parameterEnabled = list(self.parameterEnabled)
        fitfunction.useSmartStartValues = self.useSmartStartValues
        fitfunction.startParameterExpressions = list(self.startParameterExpressions) if self.startParameterExpressions is not None else [None]*len(self.startParameters)
        fitfunction.parameters = list(self.parameters)
        fitfunction.parametersConfidence = list(self.parametersConfidence)
        fitfunction.useErrorBars = self.useErrorBars
        for result in list(self.results.values()):
            fitfunction.results[result.name] = ResultRecord(name=result.name, definition=result.definition, value=result.value)
        fitfunction.parameterBounds = [ list(bound) for bound in self.parameterBounds ] if self.parameterBounds else [[None, None] for _ in range(len(fitfunction.parameterNames))]
        fitfunction.parameterBoundsExpressions =  [ list(bound) for bound in self.parameterBoundsExpressions ] if self.parameterBoundsExpressions else [[None, None] for _ in range(len(fitfunction.parameterNames))]
        return fitfunction
    
    @classmethod
    def fromFitfunction(cls, fitfunction):
        fitfunctionName = fitfunction.name if fitfunction else None
        instance = cls( name=None, fitfunctionName=fitfunctionName )
        instance.startParameters = list(fitfunction.startParameters)
        instance.parameterEnabled = list(fitfunction.parameterEnabled)
        instance.startParameterExpressions = list(fitfunction.startParameterExpressions) if fitfunction.startParameterExpressions is not None else list([None]*len(fitfunction.startParameters))
        instance.parameters = list(fitfunction.parameters)
        instance.parametersConfidence = list(fitfunction.parametersConfidence)
        instance.useSmartStartValues = fitfunction.useSmartStartValues
        instance.useErrorBars = fitfunction.useErrorBars
        for result in list(fitfunction.results.values()):
            instance.results[result.name] = ResultRecord(name=result.name, definition=result.definition, value=result.value)
        instance.parameterBounds = list( (list(bound) for bound in fitfunction.parameterBounds) ) if fitfunction.parameterBounds else  tuple((None, None) for _ in range(len(fitfunction.parameterNames)))
        instance.parameterBoundsExpressions = list( (list(bound) for bound in fitfunction.parameterBoundsExpressions) ) if fitfunction.parameterBoundsExpressions else list((None, None) for _ in range(len(fitfunction.parameterNames)))
        return instance
     
    stateFields = ['name', 'fitfunctionName', 'startParameters', 'parameterEnabled', 'results', 'useSmartStartValues', 'startParameterExpressions', 'parameters', 'parametersConfidence',
                   'parameterBounds', 'parameterBoundsExpressions', 'useErrorBars'] 
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))
        
