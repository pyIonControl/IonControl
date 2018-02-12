# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy

from modules.quantity import is_Q
from trace.TraceCollection import TraceCollection
from trace.PlottedTrace import PlottedTrace
from trace import pens
from collections import defaultdict
import functools
from modules import WeakMethod
from pyqtgraph.parametertree import Parameter
from PyQt5 import QtCore
from .decimation import decimationDict
from .calibration import calibrationDict
from .persistence import persistenceDict
from functools import partial
from .InputData import InputData

       
class DataHandling(object):
    def __init__(self):
        self.calibration = None
        self.decimation = None
        self.persistenceDecimation = None
        self.plotName = None
        self.persistence = None
        self.calibrationCache = dict()
        self.decimationCache = dict()
        self.persistenceCache = dict()
        self.persistenceDecimationCache = dict()
        self.trace = None
        self.plottedTrace = None
        self.filename = None
        self.maximumPoints = 0
        self.highAlarmThreshold = None
        self.lowAlarmThreshold = None
        
    @property
    def decimationClass(self):
        return self.decimation.name if self.decimation else 'None'
    
    @decimationClass.setter
    def decimationClass(self, name):
        if self.decimation is not None:
            self.decimationCache[self.decimation.name] = self.decimation 
        self.decimation = self.decimationCache.get(name, decimationDict[name]() ) if name != 'None' else None
        self.trace = None
        
    @property
    def persistenceDecimationClass(self):
        return self.persistenceDecimation.name if self.persistenceDecimation else 'None'
    
    @persistenceDecimationClass.setter
    def persistenceDecimationClass(self, name):
        if self.persistenceDecimation is not None:
            self.persistenceDecimationCache[self.persistenceDecimation.name] = self.persistenceDecimation 
        self.persistenceDecimation = self.persistenceDecimationCache.get(name, decimationDict[name]() ) if name != 'None' else None
        
    @property
    def calibrationClass(self):
        return self.decimation.name if self.calibration else 'None'
    
    @calibrationClass.setter
    def calibrationClass(self, name):
        if self.calibration is not None:
            self.calibrationCache[self.calibration.name] = self.calibration 
        self.calibration = self.calibrationCache.get(name, calibrationDict[name]() ) if name != 'None' else None
        
    @property
    def persistenceClass(self):
        return self.persistence.name if self.persistence else 'None'
    
    @persistenceClass.setter
    def persistenceClass(self, name):
        if self.persistence is not None:
            self.persistenceCache[self.persistence.name] = self.persistence 
        self.persistence = self.persistenceCache.get(name, persistenceDict[name]() ) if name != 'None' else None
        
    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['trace']
        del odict['plottedTrace']
        return odict
    
    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__dict__.setdefault('highAlarmThreshold', None)
        self.__dict__.setdefault('lowAlarmThreshold', None)
        self.trace = None
        self.plottedTrace = None

    def finishTrace(self):
        self.trace = None

    def outOfRange(self, source, value):
        if self.lowAlarmThreshold and value < float(self.lowAlarmThreshold):
            return "{} too low {} < {}".format(source, value, self.lowAlarmThreshold)
        if self.highAlarmThreshold and value > float(self.highAlarmThreshold):
            return "{} too high {} > {}".format(source, value, self.highAlarmThreshold)
        return None
        
    def decimate(self, takentime, value, callback):
        if value is not None:
            if self.decimation is None:
                callback( (takentime, value, None, None) )
            else:
                self.decimation.decimate( takentime, value, callback )
    
    def persistenceDecimate(self, takentime, value, callback ):
        if self.persistenceDecimation is None:
            callback( (takentime, value, None, None) )
        else:
            self.persistenceDecimation.decimate(takentime, value, callback)
    
    def persist(self, space, source, time, value, minvalue, maxvalue):
        if self.persistence is not None:
            self.persistence.persist(space, source, time, value, minvalue, maxvalue)
    
    def convert(self, data ):
        takentime, value, minVal, maxVal = data
        if self.calibration is None:
            return data
        calMin = self.calibration.convertMagnitude(minVal)
        calMax = self.calibration.convertMagnitude(maxVal)
        calValue = self.calibration.convertMagnitude(value)
        return (takentime, calValue, calMin, calMax)
        
    def addPoint(self, traceui, plot, data, source ):
        takentime, value, minval, maxval = data
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
            if is_Q(minval):
                minval = minval.m, "{:~}".format(minval.units)
            if is_Q(maxval):
                maxval = maxval.m, "{:~}".format(maxval.units)
        if not isinstance(value, str): #ignore erroneous values like 'oor'
            if self.trace is None:
                self.trace = TraceCollection(record_timestamps=True)
                self.trace.name = source
                self.trace.x = numpy.array( [takentime] )
                self.trace.y = numpy.array( [value] )
                if maxval is not None:
                    self.trace.top = numpy.array( [maxval - value])
                if minval is not None:
                    self.trace.bottom = numpy.array( [value - minval])
                self.plottedTrace = PlottedTrace(self.trace, plot, pens.penList, xAxisUnit = "s", xAxisLabel = "time", windowName=self.plotName) 
                # self.plottedTrace.trace.filenameCallback = functools.partial( WeakMethod.ref(self.plottedTrace.traceFilename), self.filename )
                traceui.addTrace( self.plottedTrace, pen=-1)
                traceui.resizeColumnsToContents()
            else:
                if self.maximumPoints==0 or len(self.trace.x)<self.maximumPoints:
                    self.trace.x = numpy.append( self.trace.x, takentime )
                    self.trace.y = numpy.append( self.trace.y, value )
                    if maxval is not None:
                        self.trace.top = numpy.append( self.trace.top, maxval - value )
                    if minval is not None:
                        self.trace.bottom = numpy.append( self.trace.bottom, value - minval )
                else:
                    maxPoints = int(self.maximumPoints)
                    self.trace.x = numpy.append( self.trace.x[-maxPoints:], takentime )
                    self.trace.y = numpy.append( self.trace.y[-maxPoints:], value )
                    if maxval is not None:
                        self.trace.top = numpy.append( self.trace.top[-maxPoints:], maxval - value )
                    if minval is not None:
                        self.trace.bottom = numpy.append( self.trace.bottom[-maxPoints:], value - minval )                
                self.plottedTrace.replot()            


class InstrumentLoggingHandler(QtCore.QObject):
    paramTreeChanged = QtCore.pyqtSignal()
    newData = QtCore.pyqtSignal(object, object)
    def __init__(self, traceui, plotDict, config, persistSpace, notifications=None):
        super(InstrumentLoggingHandler, self).__init__()
        self.notifications = notifications
        self.traceui = traceui
        self.plotDict = plotDict
        self.config = config
        self.handlerDict = self.config.get("InstrumentLogging.HandlerDict", defaultdict(DataHandling))
        self.notifications.register(self.handlerDict.keys())
        self.persistSpace = persistSpace
        self.subscriptions = set()
        
    def addDataHandler(self, channel, data):
        self.addData(channel, data)
        
    def setInputChannels(self, inputChannels ):
        for key, channel in inputChannels.items():
            if key not in self.subscriptions:
                channel.newData.connect(self.addDataHandler)
        
    def addData(self, source, data ):
        handler = self.handlerDict[source]
        if data is None:
            handler.finishTrace()
        else:
            outOfRangeMessage = handler.outOfRange(source, data[1])
            if outOfRangeMessage:
                self.notifications.notify(origin=source, message=outOfRangeMessage)
            handler.decimate( data[0], data[1], partial(self.dataCallback, source ))
            handler.persistenceDecimate( data[0], data[1], partial(self.persistenceCallback, source ) )
            self.newData.emit( source, InputData(raw=data[1]) )
            
    def dataCallback(self, source, data):
        handler = self.handlerDict[source]
        convdata = handler.convert( data )
        plot = self.plotDict.get( handler.plotName, None ) 
        if plot is None:
            plot = list(self.plotDict.values())[0]
        handler.addPoint( self.traceui, plot, convdata, source )
        self.newData.emit( source, InputData(calibrated=convdata[1], decimated=data[1]) )
                
    def persistenceCallback(self, source, data):
        handler = self.handlerDict[source]
        time, value, minvalue, maxvalue = handler.convert( data )
        handler.persist( self.persistSpace, source, time, value, minvalue, maxvalue )
            
    def saveConfig(self):
        self.config["InstrumentLogging.HandlerDict"] = self.handlerDict

    def paramDef(self, source):
        handler = self.handlerDict[source]
        self.notifications.register(source)
        param = [{'name': 'filename', 'type': 'str', 'object': handler, 'field': 'filename', 'value': handler.filename, 'tip': "Filename to be saved"},
                 {'name': 'low alarm', 'type': 'magnitude', 'object': handler, 'field': 'lowAlarmThreshold', 'value': handler.lowAlarmThreshold, 'tip': "Send notification if value is smaller"},
                 {'name': 'high alarm', 'type': 'magnitude', 'object': handler, 'field': 'highAlarmThreshold', 'value': handler.highAlarmThreshold, 'tip': "Send notification if value is larger"},
                {'name': 'plot window', 'type': 'list', 'object': handler,'field': 'plotName', 'value': handler.plotName, 'values': list(self.plotDict.keys()) },
                {'name': 'max points', 'type': 'int', 'object': handler,'field': 'maximumPoints', 'value': handler.maximumPoints },
                {'name': 'decimation', 'type': 'list', 'object': handler, 'field': 'decimationClass', 
                 'value': handler.decimation.name if handler.decimation else 'None', 'values': ['None'] + list(decimationDict.keys()), 'reload': True }]
        if handler.decimation is not None:
            param.append( {'name': 'Decimation parameters', 'type': 'group', 'children': handler.decimation.paramDef()} )
        param.append( {'name': 'calibration', 'type': 'list', 'object': handler, 'field': 'calibrationClass', 
                       'value': handler.calibration.name if handler.calibration else 'None', 'values': ['None'] + list(calibrationDict.keys()), 'reload': True } )
        if handler.calibration is not None:
            param.append( {'name': 'Calibration parameters', 'type': 'group', 'children': handler.calibration.paramDef()} )
        param.append( {'name': 'persistence', 'type': 'list', 'object': handler, 'field': 'persistenceClass', 
                       'value': handler.persistence.name if handler.persistence else 'None', 'values': ['None'] + list(persistenceDict.keys()) , 'reload': True} )
        if handler.persistence is not None:
            param.append( {'name': 'Persistence parameters', 'type': 'group', 'children': handler.persistence.paramDef()} ) 
        param.append( {'name': 'persist decimation', 'type': 'list', 'object': handler, 'field': 'persistenceDecimationClass', 
                       'value': handler.persistenceDecimation.name if handler.persistenceDecimation else 'None', 'values': ['None'] + list(decimationDict.keys()) , 'reload': True} )
        if handler.persistenceDecimation is not None:
            param.append( {'name': 'Persistence Decimation params', 'type': 'group', 'children': handler.persistenceDecimation.paramDef()} ) 
        return param

    def parameter(self, source):
        # re-create the parameters each time to prevent a exception that says the signal is not connected
        self._parameter = Parameter.create(name=source, type='group', children=self.paramDef(source))     
        self._parameter.sigTreeStateChanged.connect( self.update, QtCore.Qt.UniqueConnection)
        return self._parameter
    
    def update(self, param, changes):
        """
        update the parameter, called by the signal of pyqtgraph parametertree
        """
        for param, change, data in changes:
            if change=='value':
                setattr( param.opts.get('object', self), param.opts.get('field', param.name()), data)
                if param.opts.get('reload', False):
                    self.paramTreeChanged.emit()
                    
        
                
                