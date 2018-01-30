import PyQt5.uic

from PyQt5 import QtCore
from digitalLock.controller.ControllerClient import voltageToBin, binToVoltageV, sampleTime, binToFreqHz
from modules.quantity import Q
from modules.enum import enum
import numpy
from trace.TraceCollection import TraceCollection
from trace.PlottedTrace import PlottedTrace
from modules.PyqtUtility import updateComboBoxItems
import functools

Form, Base = PyQt5.uic.loadUiType(r'digitalLock\ui\TraceControl.ui')

class TraceSettings:
    def __init__(self):
        self.samples = Q(2000)
        self.subsample = Q(0)
        self.triggerLevel = Q(0, 'V')
        self.triggerMode = 0
        self.frequencyPlot = None
        self.errorSigPlot = None

    def __setstate__(self, s):
        self.__dict__ = s
        self.__dict__.setdefault( 'frequencyPlot', None )
        self.__dict__.setdefault( 'errorSigPlot', None )

class TraceControl(Form, Base):
    StateOptions = enum('stopped', 'running', 'single')
    newDataAvailable = QtCore.pyqtSignal( object )
    def __init__(self,controller,config,traceui,plotDict,parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.controller = controller
        self.config = config
        self.traceSettings = self.config.get("TraceControl.Settings", TraceSettings())
        self.state = self.StateOptions.stopped
        self.traceui = traceui
        self.plotDict = plotDict
        self.controller.scopeDataAvailable.connect( self.onData )
        self.trace = None
        self.trace = None
        self.errorSigCurve = None
        self.freqCurve = None
        self.lockSettings = None
    
    def setupSpinBox(self, localname, settingsname, updatefunc, unit ):
        box = getattr(self, localname)
        value = getattr(self.traceSettings, settingsname)
        box.setValue( value )
        box.dimension = unit
        box.valueChanged.connect( updatefunc )
        updatefunc( value )
    
    def setupUi(self):
        Form.setupUi(self, self)
        self.setupSpinBox('magNumberSamples', 'samples', self.setSamples, '')
        self.setupSpinBox('magSubsample', 'subsample', self.setSubSample, '')
        self.setupSpinBox('magTriggerLevel', 'triggerLevel', self.setTriggerLevel, 'V')
        self.comboTriggerMode.currentIndexChanged[int].connect( self.setTriggerMode )
        self.comboTriggerMode.setCurrentIndex( self.traceSettings.triggerMode )
        self.runButton.clicked.connect( self.onRun )
        self.singleButton.clicked.connect( self.onSingle )
        self.stopButton.clicked.connect(self.onStop)
        self.addTraceButton.clicked.connect( self.onAddTrace )
        self.initPlotCombo( self.frequencyPlotCombo, 'frequencyPlot', self.onChangeFrequencyPlot)
        self.initPlotCombo( self.errorSigPlotCombo, 'errorSigPlot', self.onChangeErrorSigPlot)
        
    def initPlotCombo(self, combo, plotAttrName, onChange ):
        combo.addItems( list(self.plotDict.keys()) )
        plotName = getattr(self.traceSettings, plotAttrName)
        if plotName is not None and plotName in self.plotDict:
            combo.setCurrentIndex( combo.findText(plotName))
        else:   
            setattr( self.traceSettings, plotAttrName, str( combo.currentText()) )
        combo.currentIndexChanged[str].connect( onChange )
        
    def onChangeFrequencyPlot(self, name):
        name = str(name)
        if name!=self.traceSettings.frequencyPlot and name in self.plotDict:
            self.traceSettings.frequencyPlot = name
            if self.freqCurve is not None:
                self.freqCurve.setView( self.plotDict[name]['view'])                      
    
    def onChangeErrorSigPlot(self, name):
        name = str(name)
        if name!=self.traceSettings.errorSigPlot and name in self.plotDict:
            self.traceSettings.errorSigPlot = name
            if self.errorSigCurve is not None:
                self.errorSigCurve.setView( self.plotDict[name]['view'])
        
    def onControlChanged(self, value):
        self.lockSettings = value
    
    def setState(self, state):
        self.state = state
        self.statusLabel.setText( self.StateOptions.reverse_mapping[self.state] )

    def onData(self, data):
        if data.errorSig and data.frequency:
            errorSig = list(map( binToVoltageV, data.errorSig ))
            if self.trace is None:
                self.trace = TraceCollection()
                self.trace.name = "Scope"
            self.trace.x = numpy.arange(len(errorSig)) * (sampleTime.m_as('us') * (1 + int(self.traceSettings.subsample)))
            self.trace.y = numpy.array( errorSig )
            if self.errorSigCurve is None:
                self.errorSigCurve = PlottedTrace(self.trace, self.plotDict[self.traceSettings.errorSigPlot], pen=-1, style=PlottedTrace.Styles.lines, name="Error Signal", #@UndefinedVariable
                                                  windowName=self.traceSettings.errorSigPlot)  
                self.errorSigCurve.plot()
                self.traceui.addTrace( self.errorSigCurve, pen=-1 )
            else:
                self.errorSigCurve.replot()                
            self.newDataAvailable.emit( self.trace )                          
            frequency = list(map( binToFreqHz, data.frequency ))
            self.trace['freq'] = numpy.array( frequency )
            if self.freqCurve is None:
                self.freqCurve = PlottedTrace(self.trace, self.plotDict[self.traceSettings.frequencyPlot], pen=-1, style=PlottedTrace.Styles.lines, name="Frequency",  #@UndefinedVariable
                                              xColumn='x', yColumn='freq', windowName=self.traceSettings.frequencyPlot ) 
                self.freqCurve.plot()
                self.traceui.addTrace( self.freqCurve, pen=-1 )
            else:
                self.freqCurve.replot() 
        if self.state==self.StateOptions.running:
            QtCore.QTimer.singleShot(10, self.delayedArm )   # wait 10ms before re-arming
        else:
            self.setState(self.StateOptions.stopped)    
            
    def delayedArm(self):     
        self.controller.armScope()
        
    def onAddTrace(self):
        if self.errorSigCurve:
            self.errorSigCurve = None
            self.trace = None
        if self.freqCurve:
            self.freqCurve = None
            self.trace = None

    def onPlotConfigurationChanged(self, plotDict):
        self.plotDict = plotDict
        if self.traceSettings.frequencyPlot not in self.plotDict:
            self.traceSettings.frequencyPlot = list(self.plotDict.keys())[0]
        if self.traceSettings.errorSigPlot not in self.plotDict:
            self.traceSettings.errorSigPlot = list(self.plotDict.keys())[0]
        updateComboBoxItems( self.frequencyPlotCombo, list(self.plotDict.keys()) )
        updateComboBoxItems( self.errorSigPlotCombo, list(self.plotDict.keys()) )       
        

    def onRun(self):
        self.controller.armScope()
        self.setState(self.StateOptions.running)
    
    def onStop(self):
        self.setState( self.StateOptions.stopped)
    
    def onSingle(self):
        self.controller.armScope()
        self.setState( self.StateOptions.single )

    def setTriggerMode(self, mode):
        self.traceSettings.triggerMode = mode
        self.controller.setTriggerMode(mode)
    
    def setTriggerLevel(self, value):
        self.traceSettings.triggerLevel = value
        self.controller.setTriggerLevel( voltageToBin(value) )
    
    def setSamples(self, samples):
        self.traceSettings.samples = samples
        self.controller.setSamples(int(samples))
    
    def setSubSample(self, subsample):
        self.traceSettings.subsample = subsample
        self.controller.setSubSample(int(subsample))
    
         
    def saveConfig(self):
        self.config["TraceControl.Settings"] = self.traceSettings
