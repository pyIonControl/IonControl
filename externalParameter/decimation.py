# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from modules.RunningStat import RunningStatHistogram, RunningStat
from modules.quantity import Q
from PyQt5 import QtCore
from functools import partial

class StaticDecimation:
    name = 'Static'
    def __init__(self, staticTime=None):
        self.lastChangedTime = 0
        self.staticTime = Q(120, 's') if staticTime is None else staticTime
        self.lastValue = None
        self.lastPersistedValue = None
        
    def decimate(self, takentime, value, callback):
        if  self.lastValue is None or value!=self.lastValue:
            self.lastChangedTime = takentime
            self.lastValue = value
            QtCore.QTimer.singleShot( self.staticTime.m_as('ms'), partial(self.bottomHalf, value, callback) )
            
    def bottomHalf(self, value, callback):
        if self.lastValue==value and ( self.lastPersistedValue is None or value!=self.lastPersistedValue ):
            callback( (self.lastChangedTime, value, None, None) )
            self.lastPersistedValue = value
          

class DynamicDecimation:
    name = 'Dynamic'
    def __init__(self):
        self.stat = RunningStatHistogram()
        self.timeStat = RunningStat()
        self.lastRecordingTime = 0
        self.MaxRecordingInterval = Q(300, 's')
        
    def decimate(self, takentime, value, callback):
        self.stat.add( value )
        self.timeStat.add( takentime )
        if takentime-self.lastRecordingTime > self.MaxRecordingInterval.m_as('s') or len(self.stat.histogram)>2:
            self.lastRecordingTime = takentime
            meanVal, minVal, maxVal = self.stat.mean, self.stat.min, self.stat.max
            timeVal = self.timeStat.mean 
            self.stat.clear()
            self.timeStat.clear()
            callback( (timeVal, meanVal, minVal, maxVal) )
    
    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['stat']
        del odict['timeStat']
        return odict
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.stat = RunningStatHistogram()
        self.timeStat = RunningStat()
        
    def paramDef(self):
        return [{'name': 'max gap', 'type': 'magnitude', 'object': self, 'field': 'MaxRecordingInterval', 'value': self.MaxRecordingInterval, 'tip': "max time without recording"}]
        

class Average:
    name = "Average"
    def __init__(self):
        self.stat = RunningStat()
        self.timeStat = RunningStat()
        self.lastRecordingTime = 0
        self.averagePoints = 10
        self.errorBars = 'Min Max'
        
    def decimate(self, takentime, value, callback):
        self.stat.add( value )
        self.timeStat.add( takentime )
        if self.stat.count>=self.averagePoints:
            self.lastRecordingTime = takentime
            self.doCallback(callback)
            
    def doCallback(self, callback):
        if self.errorBars == 'Stddev':
            e = self.stat.stddev
            meanVal, minVal, maxVal = self.stat.mean, self.stat.mean-e, self.stat.mean+e
        elif self.errorBars == 'Stderr':
            e = self.stat.stderr
            meanVal, minVal, maxVal = self.stat.mean, self.stat.mean-e, self.stat.mean+e
        else:   
            meanVal, minVal, maxVal = self.stat.mean, self.stat.min, self.stat.max
        timeVal = self.timeStat.mean 
        self.stat.clear()
        self.timeStat.clear()
        callback( (timeVal, meanVal, minVal, maxVal) )
    
    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['stat']
        del odict['timeStat']
        return odict
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.stat = RunningStat()
        self.timeStat = RunningStat()
        
    def paramDef(self):
        return [{'name': 'points', 'type': 'int', 'object': self, 'field': 'averagePoints', 'value': self.averagePoints, 'tip': "points to average"},
                {'name': 'Error bars', 'type': 'list', 'object': self, 'field': 'errorBars', 'value': self.errorBars, 'tip': 'what is shown as error bars', 'values': ['Min Max', 'Stddev', 'Stderr']}]

class TimeAverage(Average):
    name = "Time Average"
    def __init__(self):
        Average.__init__(self)
        self.averageTime = Q(10, 's')

    def decimate(self, takentime, value, callback):
        self.stat.add( value )
        self.timeStat.add( takentime )
        if takentime-self.lastRecordingTime>self.averageTime.m_as('s'):
            self.lastRecordingTime = takentime
            self.doCallback(callback)
            
    def paramDef(self):
        return [{'name': 'average time', 'type': 'magnitude', 'object': self, 'field': 'averageTime', 'value': self.averageTime, 'tip': "time to average"},
                {'name': 'Error bars', 'type': 'list', 'object': self, 'field': 'errorBars', 'value': self.errorBars, 'tip': 'what is shown as error bars', 'values': ['Min Max', 'Stddev', 'Stderr']}]


decimationDict = { DynamicDecimation.name: DynamicDecimation,
                   Average.name: Average,
                   TimeAverage.name: TimeAverage,
                   StaticDecimation.name: StaticDecimation }
