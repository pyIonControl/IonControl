# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy

from externalParameter.useTracker import UseTracker
from gui.ExpressionValue import ExpressionValue
from .decimation import StaticDecimation
from .persistence import DBPersist
from pyqtgraph.parametertree import Parameter
from PyQt5 import QtCore
import time
from functools import partial
from modules.quantity import is_Q, Q
from .InstrumentSettings import InstrumentSettings

def nextValue( current, target, stepsize, jump ):
    if (current is None) or jump:
        return (target, True)
    else:
        temp = target-current
        return (target, True) if abs(temp) <= stepsize else (current + numpy.sign(temp) * stepsize, False)


class OutputChannel(QtCore.QObject):
    persistSpace = 'externalOutput'
    valueChanged = QtCore.pyqtSignal(object)
    targetChanged = QtCore.pyqtSignal(object)
    useTracker = UseTracker()

    def __init__(self, device, deviceName, channelName, globalDict, settings=None, outputUnit=''):
    #def __init__(self, device, deviceName, channelName, globalDict, settings=dict(), outputUnit=''):
        super(OutputChannel, self).__init__()
        self.device = device
        self.deviceName = deviceName
        self.channelName = channelName
        self.globalDict = globalDict
        self.expressionValue = ExpressionValue(self.name, self.globalDict, None)
        self.settings = settings if settings is not None else InstrumentSettings()
        self.savedValue = None
        self.decimation = StaticDecimation()
        self.persistence = DBPersist()
        self.outputUnit = outputUnit
        self.setDefaults()
        self.expressionValue.string = self.settings.strValue
        self.expressionValue.value = self.settings.targetValue
        self.expressionValue.valueChanged.connect(self.onExpressionUpdate)


    def setDefaults(self):
        self.settings.__dict__.setdefault('value', Q(0, self.outputUnit))  # the current value
        self.settings.__dict__.setdefault('persistDelay',Q(60, 's'))     # delay for persistency
        self.settings.__dict__.setdefault('strValue', None)                          # requested value as string (formula)
        self.settings.__dict__.setdefault('targetValue', Q(0, self.outputUnit) )  # requested value as string (formula)
        for d in self.device._channelParams.get(self.channelName, tuple()):
            self.settings.__dict__.setdefault(d['name'], d['value'])

    def onExpressionUpdate(self, name, value, string, origin):
        if origin == 'recalculate':
            self.setValue(value)
            self.targetChanged.emit(value)

    @property
    def name(self):
        return "{0}_{1}".format(self.deviceName, self.channelName) if self.channelName else self.deviceName
        
    @property
    def value(self):
        return self.settings.value
    
    def setValue(self, targetValue):
        """
        go stepsize towards the value. This function returns True if the value is reached. Otherwise
        it should return False. The user should call repeatedly until the intended value is reached
        and True is returned.
        """
        self.settings.targetValue = targetValue
        self.expressionValue.value = targetValue
        reportvalue = self.device.setValue(self.channelName, targetValue)
        self.settings.value = reportvalue
        self.valueChanged.emit(self.settings.value)
        return True
    
    def persist(self, channel, value):
        self.decimation.staticTime = self.settings.persistDelay
        decimationName = self.name if channel is None else self.name
        self.decimation.decimate(time.time(), value, partial(self.persistCallback, decimationName) )
        
    def persistCallback(self, source, data):
        time, value, minval, maxval = data
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value)
        else:
            value, unit = value, None
        self.persistence.persist(self.persistSpace, source, time, value, minval, maxval, unit)
           
    def saveValue(self, overwrite=True):
        """
        save current value
        """
        if self.savedValue is None or overwrite:
            self.savedValue = self.value
        return self.savedValue

    def restoreValue(self):
        """
        restore the value saved previously, this routine only goes stepsize towards this value
        if the stored value is reached returns True, otherwise False. Needs to be called repeatedly
        until it returns True in order to restore the saved value.
        """
        if self.expressionValue.hasDependency:
            self.expressionValue.recalculate()
            arrived = self.setValue(self.expressionValue.value)
        else:
            if self.savedValue is None:
                return True
            arrived = self.setValue(self.savedValue)
            if arrived:
                self.savedValue = None
        return arrived
        
    @property
    def externalValue(self):
        return self.device.getExternalValue(self.channelName)
    
    @property
    def dimension(self):
        return self.outputUnit
    
    @property
    def useExternalValue(self):
        return self.device.useExternalValue(self.channelName)

    @property
    def hasDependency(self):
        return self.expressionValue.hasDependency
    
    @property
    def targetValue(self):
        return self.settings.targetValue

    @targetValue.setter
    def targetValue(self, requestval):
        self.setValue(requestval)

    @property
    def string(self):
        return self.expressionValue.string

    @string.setter
    def string(self, s):
        self.settings.strValue = s
        self.expressionValue.string = s
        
    @property
    def strValue(self):
        return self.expressionValue.string

    @strValue.setter
    def strValue(self, s):
        self.settings.strValue = s
        self.expressionValue.string = s

    @property
    def parameter(self):
        # re-create the parameters each time to prevent a exception that says the signal is not connected
        self._parameter = Parameter.create(name=self.name, type='group', children=self.paramDef())     
        self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        return self._parameter                
        
    def paramDef(self):
        """
        return the parameter definition used by pyqtgraph parametertree to show the gui
        """
        myparams = [{'name': 'persistDelay', 'type': 'magnitude', 'value': self.settings.persistDelay }]
        for d in self.device._channelParams.get(self.channelName, tuple()):
            p = dict(d)
            p['value'] = getattr(self.settings, d['name'])
            myparams.append(p)
        return myparams

    def update(self, param, changes):
        """
        update the parameter, called by the signal of pyqtgraph parametertree
        """
        for param, change, data in changes:
            if change=='value':
                setattr( self.settings, param.name(), data)       
        
class SlowAdjustOutputChannel(OutputChannel):
    def __init__(self, device, deviceName, channelName, globalDict, settings, outputUnit):
        super(SlowAdjustOutputChannel, self).__init__(device, deviceName, channelName, globalDict, settings, outputUnit)
        self.timerActive = False
        
    def setDefaults(self):
        super(SlowAdjustOutputChannel, self).setDefaults()
        self.settings.__dict__.setdefault('delay', Q(100, 'ms'))      # s delay between subsequent updates
        self.settings.__dict__.setdefault('jump', False)       # if True go to the target value in one jump
        self.settings.__dict__.setdefault('stepsize', Q(1, self.outputUnit))       # if True go to the target value in one jump
        
    def paramDef(self):
        param = super(SlowAdjustOutputChannel, self).paramDef()
        param.extend([{'name': 'delay', 'type': 'magnitude', 'value': self.settings.delay, 'tip': "between steps"},
                            {'name': 'jump', 'type': 'bool', 'value': self.settings.jump},
                            {'name': 'stepsize', 'type': 'magnitude', 'value': self.settings.stepsize }])
        return param

    @staticmethod
    def encpasulate_value(arg, second=True):
        if not isinstance(arg, tuple):
            return arg, second
        elif len(arg) == 1:
            return arg[0], second
        return arg[0], arg[1] and second

    def setValue(self, targetValue):
        """
        go stepsize towards the value. This function returns True if the value is reached. Otherwise
        it should return False. The user should call repeatedly until the intended value is reached
        and True is returned.
        """
        if targetValue is not None:
            if self.settings.targetValue != targetValue:
                self.settings.targetValue = targetValue
                self.settings.value = self.externalValue
            newvalue, arrived = nextValue(self.settings.value, targetValue, self.settings.stepsize, self.settings.jump)
            reportvalue, arrived = self.encpasulate_value(self.device.setValue(self.channelName, newvalue), second=arrived)
            self.settings.value = reportvalue
            self.expressionValue.value = targetValue  # TODO: still unclear whether that makes sense
            self.valueChanged.emit(self.settings.value)
            if arrived:
                self.persist(self.name, self.settings.value)
                self.useTracker.release(self.name)
            else:
                self.useTracker.take(self.name)
            return arrived
        return True

    def onExpressionUpdate(self, name, value, string, origin):
        if origin == 'recalculate':
            self.settings.targetValue = value
            self.targetChanged.emit(value)
            self.useTracker.take(self.name)
            if not self.timerActive:
                self.timerActive = True
                self.expressionUpdateBottomHalf()

    def expressionUpdateBottomHalf(self):
        if not self.setValue(self.settings.targetValue):
            QtCore.QTimer.singleShot(self.settings.delay.m_as('ms'), self.expressionUpdateBottomHalf)
        else:
            self.useTracker.release(self.name)
            self.timerActive = False
