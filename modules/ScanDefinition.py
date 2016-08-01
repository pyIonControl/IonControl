# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import math
from modules.quantity import Q
from modules import Expression
from builtins import staticmethod

class ScanSegmentDefinition(object):
    expression = Expression.Expression()
    def __init__(self):
        self._start = Q(0)
        self._stop = Q(1)
        self._center = Q(0.5)
        self._span = Q(1)
        self._steps = Q(2)
        self._stepsize = Q(1)
        self._stepPreference = 'stepsize'
        self._inconsistent = False
        self._startText = None
        self._stopText = None
        self._centerText = None
        self._spanText = None
        self._stepsText = None
        self._stepsizeText = None
        
    def __setstate__(self, d):
        self.__dict__ = d
        self.__dict__.setdefault('_inconsistent', False)
        self.__dict__.setdefault('_startText', None)
        self.__dict__.setdefault('_stopText', None)
        self.__dict__.setdefault('_centerText', None)
        self.__dict__.setdefault('_spanText', None)
        self.__dict__.setdefault('_stepsText', None)
        self.__dict__.setdefault('_stepsizeText', None)
        
    stateFields = ['_start', '_stop', '_center', '_span', '_steps', '_stepsize', '_stepPreference', '_startText', '_stopText', '_centerText', '_spanText', '_stepsText', '_stepsizeText'] 
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))
    
    @property
    def startText(self):
        return self._startText if self._startText is not None else str(self._start)

    @startText.setter
    def startText(self, text):
        self._startText = text

    @property
    def stopText(self):
        return self._stopText if self._stopText is not None else str(self._stop)

    @stopText.setter
    def stopText(self, text):
        self._stopText = text

    @property
    def centerText(self):
        return self._centerText if self._centerText is not None else str(self._center)

    @centerText.setter
    def centerText(self, text):
        self._centerText = text
        
    @property
    def spanText(self):
        return self._spanText if self._spanText is not None else str(self._span)

    @spanText.setter
    def spanText(self, text):
        self._spanText = text

    @property
    def stepsText(self):
        return self._stepsText if self._stepsText is not None else str(self._steps)

    @stepsText.setter
    def stepsText(self, text):
        self._stepsText = text

    @property
    def stepsizeText(self):
        return self._stepsizeText if self._stepsizeText is not None else str(self._stepsize)

    @stepsizeText.setter
    def stepsizeText(self, text):
        self._stepsizeText = text

    @property
    def start(self):
        return self._start
    
    @start.setter
    def start(self, start):
        self._start = start
        self.calculateCenterSpan()
                
    @property
    def stop(self):
        return self._stop
    
    @stop.setter
    def stop(self, stop):
        self._stop = stop
        self.calculateCenterSpan()
        
    def calculateCenterSpan(self):
        try:
            self._span = abs(self._stop - self._start)
            self._center = self._start + (self._stop-self._start)/2
            if self._stepPreference=='steps' and self._steps>1:
                self._stepsize = self._span / (self._steps-1)
            else:
                self._steps = math.ceil(self._span / self._stepsize + 1) 
            self.checkConsistency()
            self._centerText = None
            self._spanText = None
        except (TypeError, ValueError):
            self._inconsistent = True
          
    @property
    def center(self):
        return self._center
        
    @center.setter  
    def center(self, center):
        self._center = center
        try:
            self.calculateStartStop()
            self.checkConsistency()
        except ValueError:
            self._inconsistent = True
        
    @property
    def span(self):
        return self._span
    
    @span.setter
    def span(self, span):
        self._span = span
        try:
            self.calculateStartStop()
            if self._stepPreference=='steps' and self._steps>1:
                self._stepsize = self._span / (self._steps-1)
            else:
                self._steps = math.ceil(self._span / self._stepsize) + 1
            self.checkConsistency()
        except ValueError:
            self._inconsistent = True
            
        
    def calculateStartStop(self):
        self._start = self._center - self._span/2
        self._stop = self._center + self._span/2
        self._startText = None
        self._stopText = None
        
    @property
    def steps(self):
        return self._steps
    
    @steps.setter
    def steps(self, steps):
        try:
            self._steps = max( steps, 2 )
            self._stepPreference = 'steps'
            self._stepsize = self._span / (self._steps-1)
            self._stepsizeText = None
            self.checkConsistency()
        except ValueError:
            self._inconsistent = True
        
    @property
    def stepsize(self):
        return self._stepsize
    
    @stepsize.setter
    def stepsize(self, stepsize):
        try:
            self._stepsize = stepsize
            self._stepPreference = 'stepsize'
            self._steps = math.ceil(self._span / self._stepsize+1) 
            self._stepsText = None
            self.checkConsistency()
        except ValueError:
            self._inconsistent = True
        
    @property
    def inconsistent(self):
        return self._inconsistent
    
    def checkConsistency(self):
        try:
            self._inconsistent = not (self._start.dimensionality == self._stop.dimensionality ==
                                      self._center.dimensionality == self._span.dimensionality ==
                                      self._stepsize.dimensionality)
        except Exception:
            self._inconsistent = True
        
    def evaluate(self, globalDict ):
        changed = False
        try:
            if self._startText:
                self.start = self.expression.evaluateAsMagnitude(self._startText, globalDict )
                changed = True
            if self._stopText:
                self.stop = self.expression.evaluateAsMagnitude(self._stopText, globalDict )
                changed = True
            if self._centerText:
                self.center = self.expression.evaluateAsMagnitude(self._centerText, globalDict )
                changed = True
            if self._spanText:
                self.span = self.expression.evaluateAsMagnitude(self._spanText, globalDict )
                changed = True
            if self._stepsText:
                self.steps = self.expression.evaluateAsMagnitude(self._stepsText, globalDict )
                changed = True
            if self._stepsizeText:
                self.stepsize = self.expression.evaluateAsMagnitude(self._stepsizeText, globalDict )
                changed = True
        except KeyError:  # happens if globalVariable not found
            pass
        except ZeroDivisionError:
            pass
        return changed
           
        