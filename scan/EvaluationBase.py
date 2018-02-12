# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import namedtuple

from modules.Observable import Observable
from modules.SequenceDict import SequenceDict
from PyQt5 import QtCore
import logging
import copy
import numpy
from uiModules.ParameterTable import Parameter


EvaluationAlgorithms = {}

class EvaluationException(Exception):
    pass

class EvaluationMeta(type):
    def __new__(self, name, bases, dct):
        evalclass = super(EvaluationMeta, self).__new__(self, name, bases, dct)
        if name!='EvaluationBase':
            if 'name' not in dct:
                raise EvaluationException("Evaluation class needs to have class attribute 'name'")
            EvaluationAlgorithms[dct['name']] = evalclass
        return evalclass


class EvaluationResult(namedtuple("EvaluationResultBase", "value interval raw valid")):
    def __new__(cls, value=float('NaN'), interval=None, raw=None, valid=False):
        is_valid = valid or (value is not None)
        return super(EvaluationResult, cls).__new__(cls, value, interval, raw, is_valid)


def sint12(a):
    return -0x800 + (int(a) & 0x7ff) if (int(a) & 0x800) else (int(a) & 0x7ff)

def sint16(a):
    return -0x8000 + (int(a) & 0x7fff) if (int(a) & 0x8000) else (int(a) & 0x7fff)

def sint32(a):
    return -0x80000000 + (int(a) & 0x7fffffff) if (int(a) & 0x80000000) else (int(a) & 0x7fffffff)

class EvaluationBase(Observable, metaclass=EvaluationMeta):
    hasChannel = True
    intConversionsLookup = {'None': lambda x: x, 'sint12': sint12, 'sint16': sint16, 'sint32': sint32}
    def __init__(self, globalDict=None, settings= None):
        Observable.__init__(self)
        self.settings = settings if settings else dict()
        self.globalDict = globalDict if globalDict else dict()
        self.setDefault()
        self.settingsName = None

    @property
    def useQubitEvaluation(self):
        return hasattr(self, 'qubitEvaluation')

    @property
    def useDetailEvaluation(self):
        return hasattr(self, 'detailEvaluation')

    @property
    def qubitPlotWindow(self):
        return 'Qubit' if self.useQubitEvaluation else None

    def setDefault(self):
        self.settings.setdefault('averageSameX', False)
        self.settings.setdefault('combinePoints', 0)
        self.settings.setdefault('averageType', 0)
        self.settings.setdefault('intConversion', 'None')

    def parameters(self):
        """return the parameter definitions used by the parameterTable"""
        parameterDict = SequenceDict()
        parameterDict['averageSameX'] = Parameter(name='averageSameX', dataType='bool',
                                                    value=self.settings['averageSameX'],
                                                    tooltip="average all values for same x value")
        parameterDict['combinePoints'] = Parameter(name='combinePoints', dataType='magnitude',
                                                  value=self.settings['combinePoints'])
        parameterDict['averageType'] = Parameter(name='averageType', dataType='magnitude',
                                                  value=self.settings['averageType'])
        parameterDict['intConversion'] = Parameter(name='intConversion', dataType='select',
                                                   choices=list(sorted(self.intConversionsLookup.keys())),
                                                   value=self.settings['intConversion'])
        return parameterDict

    def update(self, parameter):
        """update the parameter changed in the parameterTable"""
        if parameter.dataType != 'action':
            self.settings[parameter.name] = parameter.value
            if parameter.text:
                self.settings[(parameter.name,'text')] = parameter.text
            else:
                self.settings.pop((parameter.name,'text'), None)
            self.firebare()
        else:
            getattr(self, parameter.value)()
            
    def setSettings(self, settings, settingsName):
        try:
            for name, value in self.settings.items():
                settings.setdefault(name, value)
            self.settings = settings
            self.settingsName = settingsName if settingsName else "unnamed"
        except Exception as ex:
            logging.getLogger(__name__).exception(ex)
        
    def setSettingsName(self, settingsName):
        self.settingsName = settingsName

    def __deepcopy__(self, memo=None):
        return type(self)( self.globalDict, settings=copy.deepcopy(self.settings, memo) )
  
    def histogram(self, data, evaluation, histogramBins=50 ):
        countarray = evaluation.getChannelData(data)
        y, x = numpy.histogram( countarray, range=(0, histogramBins), bins=histogramBins)
        return y, x, None   # third parameter is optional function 
    