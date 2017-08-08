# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import PyQt5.uic
from PyQt5 import QtCore
from functools import partial
from persist.ValueHistory import ValueHistoryStore
from modules.PyqtUtility import updateComboBoxItems
from datetime import datetime
from trace.TraceCollection import TraceCollection
from trace.PlottedTrace import PlottedTrace
import numpy
from collections import defaultdict
import logging
from modules import WeakMethod 
import weakref
from modules.NamedTimespan import getRelativeDatetime, timespans
import pytz
from .persistence import DBPersist
from ProjectConfig.Project import getProject
from copy import deepcopy

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/InstrumentLoggerQueryUi.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class Parameters:
    def __init__(self):
        self.space = None
        self.parameter = None
        self.fromTime = datetime(2014, 8, 30)
        self.toTime = datetime.now()
        self.useToTime = False
        self.plotName = None 
        self.plotUnit = ""
        self.steps = False
        self.spaceParamCache = dict()
        self.updatePrevious = True
        self.autoUpdate = False
        
    def __setstate__(self, s):
        self.__dict__ = s
        self.__dict__.setdefault('updatePrevious', True)
        self.__dict__.setdefault('useToTime', False)
        self.__dict__.setdefault('autoUpdate', False)
        

class InstrumentLoggerQueryUi(Form, Base):
    def __init__(self, config, traceui, plotDict, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.config = config
        self.parameters = self.config.get("InstrumentLoggerQueryUi", Parameters())
        self.traceui = traceui
        self.unsavedTraceCount = 0
        self.plotDict = plotDict
        self.project = getProject()
        self.connection = ValueHistoryStore(self.project.dbConnection)
        self.connection.open_session()
        self.cache = dict()
    
    def setupUi(self, MainWindow):
        Form.setupUi(self, MainWindow)
        self.comboBoxSpace.currentIndexChanged[str].connect( self.onSpaceChanged  )
        self.comboBoxParam.currentIndexChanged[str].connect( partial(self.onValueChangedString, 'parameter') )
        self.comboBoxPlotName.currentIndexChanged[str].connect( partial(self.onValueChangedString, 'plotName') )
        self.toTimeCheckBox.setChecked( self.parameters.useToTime )
        self.toTimeCheckBox.stateChanged.connect( self.onUseToTime )
        self.dateTimeEditTo.setEnabled( self.parameters.useToTime )
        self.fromTimeCombo.addItems( ['Select timespan ...']+timespans )
        self.fromTimeCombo.currentIndexChanged[str].connect( self.onNamedTimespan )
        self.onRefresh()
        if self.parameters.space is not None:
            self.comboBoxSpace.setCurrentIndex( self.comboBoxSpace.findText(self.parameters.space ))
        if self.parameters.parameter is not None:
            self.comboBoxParam.setCurrentIndex( self.comboBoxParam.findText(self.parameters.parameter ))
        if self.parameters.fromTime is not None:
            self.dateTimeEditFrom.setDateTime( self.parameters.fromTime )
        self.dateTimeEditFrom.dateTimeChanged.connect( partial(self.onValueChangedDateTime, 'fromTime')  )
        if self.parameters.toTime is not None:
            self.dateTimeEditTo.setDateTime( self.parameters.toTime )
        self.dateTimeEditTo.dateTimeChanged.connect( partial(self.onValueChangedDateTime, 'toTime')  )
        if self.parameters.plotName is not None:
            self.comboBoxPlotName.setCurrentIndex( self.comboBoxPlotName.findText(self.parameters.plotName ))
        self.lineEditPlotUnit.setText( self.parameters.plotUnit )
        self.lineEditPlotUnit.textChanged.connect( partial(self.onValueChangedString, 'plotUnit') )
        self.pushButtonCreatePlot.clicked.connect( self.onCreatePlot )
        self.pushButtonUpdateAll.clicked.connect( self.onUpdateAll )
        self.toolButtonRefresh.clicked.connect( self.onRefresh )
        self.checkBoxSteps.setChecked( self.parameters.steps )
        self.checkBoxSteps.stateChanged.connect( partial(self.onStateChanged, 'steps') )
        self.checkBoxUpdatePrevious.setChecked( self.parameters.updatePrevious )
        self.checkBoxUpdatePrevious.stateChanged.connect( partial( self.onStateChanged, 'updatePrevious') )
        self.onSpaceChanged(self.parameters.space)
        DBPersist.newPersistData.subscribe(self.handleNewDBData)

    def onNamedTimespan(self, name):
        dt = getRelativeDatetime(str(name), None)
        if dt is not None:
            self.parameters.fromTime = dt
            self.dateTimeEditFrom.setDateTime( self.parameters.fromTime )
            self.fromTimeCombo.setCurrentIndex(0)
        

    def onUseToTime(self, state):
        self.parameters.useToTime = state==QtCore.Qt.Checked
        self.dateTimeEditTo.setEnabled( self.parameters.useToTime )

    def onStateChanged(self, attr, state):
        setattr( self.parameters, attr, state==QtCore.Qt.Checked )
        
    def onValueChangedString(self, param, value):
        setattr( self.parameters, param, str(value) )
        
    def onValueChangedDateTime(self, param, value):
        setattr( self.parameters, param, value.toPyDateTime() )

    def saveConfig(self):
        self.config["InstrumentLoggerQueryUi"] = self.parameters
        
    def onRefresh(self):
        self.parameterNames = defaultdict( list )
        for (space, source) in list(self.connection.refreshSourceDict().keys()):
            self.parameterNames[space].append(source)
        updateComboBoxItems( self.comboBoxSpace, sorted(self.parameterNames.keys()) )
        updateComboBoxItems( self.comboBoxParam, sorted(self.parameterNames[self.parameters.space]) )
        updateComboBoxItems( self.comboBoxPlotName, sorted(self.plotDict.keys()) )        
        
    def onSpaceChanged(self, newSpace):
        newSpace = str(newSpace)
        if self.parameters.space is not None and self.parameters.parameter is not None:
            self.parameters.spaceParamCache[self.parameters.space] = self.parameters.parameter
        self.parameters.space = newSpace
        self.parameters.parameter = self.parameters.spaceParamCache.get( self.parameters.space, self.parameterNames[self.parameters.space][0] if len(self.parameterNames[self.parameters.space])>0 else None )
        updateComboBoxItems( self.comboBoxParam, sorted(self.parameterNames[self.parameters.space]) )
        if self.parameters.parameter is not None:
            self.comboBoxParam.setCurrentIndex( self.comboBoxParam.findText(self.parameters.parameter ))
        
       
    def onCreatePlot(self): 
        self.doCreatePlot(self.parameters.space, self.parameters.parameter, self.parameters.fromTime, self.parameters.toTime if self.parameters.useToTime else None, 
                          self.parameters.plotName, self.parameters.steps)
        self.cacheGarbageCollect()
        
    def cacheGarbageCollect(self):
        for key, (ref, _) in list(self.cache.items()):
            if ref() is None:
                self.cache.pop(key)
        
    def doCreatePlot(self, space, parameter, fromTime, toTime, plotName, steps, forceUpdate=False ):
        ref, _ = self.cache.get( ( space, parameter ), (lambda: None, None)) 
        plottedTrace = ref() if (self.parameters.updatePrevious or forceUpdate) else None # get plottedtrace from the weakref if exists           
        result = self.connection.getHistory( space, parameter, fromTime, toTime )
        if not result:
            logging.getLogger(__name__).warning("Database query returned empty set")
        elif len(result)>0:
            #time = [(pytz.utc.localize(e.upd_date) - datetime(1970,1,1, tzinfo=pytz.utc)).total_seconds() for e in result]
            if result[0].upd_date.tzinfo is not None:
                time = [(e.upd_date - datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds() for e in result]
            else:
                time = [(e.upd_date-datetime.fromtimestamp(0)).total_seconds() for e in result]
            value = [e.value for e in result]
            bottom = [e.value - e.bottom if e.bottom is not None else e.value for e in result]
            top = [e.top -e.value if e.top is not None else e.value for e in result]
            if plottedTrace is None:  # make a new plotted trace
                trace = TraceCollection(record_timestamps=False)
                trace.name = parameter + "_Query"
                trace.y = numpy.array( value )
                if plotName is None:
                    plotName = str(self.comboBoxPlotName.currentText()) 
                if steps:
                    trace.x = numpy.array( time+[time[-1]] )
                    plottedTrace = PlottedTrace( trace, self.plotDict[plotName], xAxisLabel = "local time", plotType=PlottedTrace.Types.steps, fill=False, windowName=plotName) #@UndefinedVariable
                else:
                    trace.x = numpy.array( time )
                    trace.top = numpy.array( top )
                    trace.bottom = numpy.array( bottom )
                    plottedTrace = PlottedTrace( trace, self.plotDict[plotName], xAxisLabel = "local time", windowName=plotName)
                    plottedTrace.trace.autoSave = self.traceui.autoSaveTraces
                    plottedTrace.name = trace.name
                    plottedTrace.trace.filenamePattern = trace.name
                    if not plottedTrace.trace.autoSave: self.unsavedTraceCount+=1
                self.traceui.addTrace( plottedTrace, pen=-1)
                self.traceui.resizeColumnsToContents()
                self.cache[(space, parameter)] = ( weakref.ref(plottedTrace), (space, parameter, fromTime, toTime, plotName, steps) )
            else:  # update the existing plotted trace
                trace = plottedTrace.trace
                trace.y = numpy.array( value )
                if steps:
                    trace.x = numpy.array( time+[time[-1]] )
                else:
                    trace.x = numpy.array( time )
                    trace.top = numpy.array( top )
                    trace.bottom = numpy.array( bottom )
                plottedTrace.replot()     
                
    def onUpdateAll(self):
        for ref, context in list(self.cache.values()):
            if ref() is not None:
                self.doCreatePlot(*context, forceUpdate=True )
        self.cacheGarbageCollect()
            
    def handleNewDBData(self, event ):
        logging.getLogger(__name__).info( "New DB data")