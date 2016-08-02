# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import math
from collections import defaultdict

# see Donald Knuth's Art of Computer Programming, Vol 2, page 232, 3rd edition
class RunningStat(object):
    def __init__(self, zero=0):  # giving zero should allow to pass numpy arrays to be averaged
        self.zero = zero
        self.clear()
        
    def clear(self):
        self.mOld = self.zero
        self.mNew = self.zero
        self.sOld = self.zero
        self.sNew = self.zero
        self._max = None
        self._min = None
        self.count = 0
        self.currentValue = None
        
    @property
    def mean(self):
        return self.mNew
        
    @property
    def variance(self):
        return (self.sNew / (self.count - 1)) if self.count > 1 else 0.0

    @property
    def std(self):
        return math.sqrt((self.sNew / self.count) if self.count > 0 else 0.0)
        
    @property
    def stddev(self):
        return math.sqrt( self.variance )
        
    @property
    def stderr(self):
        return self.stddev / math.sqrt(self.count-1) if self.count>1 else 0
    
    @property
    def min(self):
        return self._min
    
    @property
    def max(self):
        return self._max
        
    def add(self, value):
        if not( value is None or math.isnan(value) or math.isinf(value) ):
            self.currentValue = value
            self.count += 1
            if self.count == 1:
                self.mOld = value
                self.mNew = value
                self.sOld = 0
                self.sNew = 0
                self._max = value
                self._min = value
            else:
                self.mNew = self.mOld + ( value - self.mOld )/self.count
                self.sNew = self.sOld + ( value - self.mOld ) * ( value - self.mNew )
                self._max = max( self._max, value )
                self._min = min( self._min, value )
                
                self.mOld = self.mNew
                self.sOld = self.sNew
        
        
class RunningStatHistogram( RunningStat, object ):
    def __init__(self, zero=0):
        RunningStat.__init__(self, zero)
        self._hist = defaultdict( lambda: 0)
        
    def add(self, value):
        self._hist[value] += 1
        RunningStat.add(self, value) 
        
    @property
    def histogram(self):
        return self._hist
    
    def clear(self):
        RunningStat.clear(self)
        self._hist = defaultdict( lambda: 0)
