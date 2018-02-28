# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtWidgets
import PyQt5.uic
import math

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from modules.quantity import mag_unit
from persist.MeasurementLog import MeasurementContainer
from .MeasurementTableModel import MeasurementTableModel
from .ResultTableModel import ResultTableModel 
from .StudyTableModel import StudyTableModel
from .ParameterTableModel import ParameterTableModel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from datetime import datetime, time, timedelta
from _functools import partial
from modules.firstNotNone import firstNotNone
from modules.Utility import unique
from .ScanNameTableModel import ScanNameTableModel 
from modules.PyqtUtility import updateComboBoxItems
import weakref
import logging
import pytz
import numpy
from trace.TraceCollection import TraceCollection
from trace.PlottedTrace import PlottedTrace
from modules import WeakMethod
from modules.GuiAppearance import saveGuiState, restoreGuiState    

import os
uipath = os.path.join(os.path.dirname(__file__), '..', '..', 'ui/MeasurementLog.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


class Settings(AttributeComparisonEquality):
    def __init__(self):
        self.timespan = 0
        self.fromDateTimeEdit = datetime.combine(datetime.now().date(), time())
        self.toDateTimeEdit = datetime.combine((datetime.now()+timedelta(days=1)).date(), time())
        self.extraColumns = list()
        self.filterByScanName = False
        self.plotXAxis = None
        self.plotYAxis = None
        self.plotWindow = None
        self.xUnit = ""
        self.yUnit = ""
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault( 'timespan', 0)
        self.__dict__.setdefault( 'fromDateTimeEdit', datetime.combine(datetime.now().date(), time()))
        self.__dict__.setdefault( 'toDateTimeEdit', datetime.combine((datetime.now()+timedelta(days=1)).date(), time()))
        self.__dict__.setdefault( 'extraColumns', list())
        self.__dict__.setdefault( 'filterByScanName', False)
        self.__dict__.setdefault( 'plotXAxis', None)
        self.__dict__.setdefault( 'plotYAxis', None)
        self.__dict__.setdefault( 'plotWindow', None)
        self.__dict__.setdefault( 'xUnit', "")
        self.__dict__.setdefault( 'yUnit', "")

class MeasurementLogUi(Form, Base ):
    timespans = ['Today', 'Two days', 'Three days', 'One week', 'One month', 'Three month', 'One year', 'All', 'Custom']
    mySplitters = ['splitterHorizontal', "splitterVertical", "splitterHorizontalParam", "splitterLeftVertical" ]
    myTableViews = ["measurementTableView", "resultTableView", "studyTableView", "parameterTableView", "scanNameTableView"]
    def __init__(self, config, dbConnection, parent=None):
        Form.__init__(self)
        Base.__init__(self, parent)
        self.config = config
        self.configname = 'MeasurementLog'
        self.settings = self.config.get(self.configname, Settings())
        self.dbConnection = dbConnection
        self.container = MeasurementContainer(dbConnection)
        self.container.open()
        self.fromToTimeLookup = [ lambda now: (datetime.combine(now.date(), time()), datetime.combine(now + timedelta(days=1), time())),              # today
                           lambda now: (datetime.combine(now - timedelta(days=1), time()),  datetime.combine(now + timedelta(days=1), time())),  # three days ago
                           lambda now: (datetime.combine(now - timedelta(days=2), time()),  datetime.combine(now + timedelta(days=1), time())),  # three days ago
                           lambda now: (datetime.combine(now - timedelta(days=6), time()),  datetime.combine(now + timedelta(days=1), time())),  # one week
                           lambda now: (datetime.combine(now - timedelta(days=30), time()), datetime.combine(now + timedelta(days=1), time())),   # 30 days
                           lambda now: (datetime.combine(now - timedelta(days=90), time()), datetime.combine(now + timedelta(days=1), time())),   # 90 days
                           lambda now: (datetime.combine(now - timedelta(days=365), time()), datetime.combine(now + timedelta(days=1), time())),   # 1 year
                           lambda now: (datetime(2014, 11, 1, 0, 0),  datetime.combine(now + timedelta(days=1), time())),  # all
                           lambda now: (self.settings.fromDateTimeEdit, self.settings.toDateTimeEdit)
                           ]
        self.sourceLookup = { 'measurement': lambda measurement, space, name: (getattr( measurement, name ), None, None),
                              'parameter': self.getParameter,
                              'result': self.getResult  }        
        self.currentMeasurement = None
        self.traceuiLookup = dict()        # the measurements should insert their traceui into this dictionary
        self.cache = dict()

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        # measurement Table
        self.measurementModel = MeasurementTableModel(self.container.measurements, self.settings.extraColumns, self.traceuiLookup, self.container)
        self.measurementTableView.setModel( self.measurementModel )
        # result Table
        self.resultModel = ResultTableModel( list(), self.container )
        self.resultTableView.setModel( self.resultModel )
        # study table
        self.studyModel = StudyTableModel( list(), self.container )
        self.studyTableView.setModel( self.studyModel )
        # parameter table
        self.parameterModel = ParameterTableModel( list(), self.container )
        self.parameterTableView.setModel( self.parameterModel )
        magnitudeDelegate = MagnitudeSpinBoxDelegate()
        self.parameterTableView.setItemDelegateForColumn( 2, magnitudeDelegate )
        # scanNames table
        self.scanNameTableModel = ScanNameTableModel( self.container.scanNames, self.container)
        self.scanNameTableView.setModel( self.scanNameTableModel )
        self.scanNameTableModel.scanNameFilterChanged.connect( self.onFilterSelection )
        # Context Menu for ScanName table
        self.scanNameTableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.selectAllAction = QtWidgets.QAction( "select all", self)
        self.selectAllAction.triggered.connect( partial( self.scanNameTableModel.showAll, True )  )
        self.scanNameTableView.addAction( self.selectAllAction )
        self.deselectAllAction = QtWidgets.QAction("deselect all", self)
        self.onlyCheckSelectedAction = QtWidgets.QAction("only check selected", self)
        self.deselectAllAction.triggered.connect(partial(self.scanNameTableModel.showAll, False))
        self.onlyCheckSelectedAction.triggered.connect(self.onlyCheckSelected)
        self.scanNameTableView.addAction(self.deselectAllAction)
        self.scanNameTableView.addAction(self.onlyCheckSelectedAction)
        # Context Menu for ResultsTable
        self.resultTableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.addResultToMeasurementAction = QtWidgets.QAction( "add as column to measurement", self)
        self.addResultToMeasurementAction.triggered.connect( self.onAddResultToMeasurement  )
        self.resultTableView.addAction( self.addResultToMeasurementAction )
        # Context Menu for Measurements Table
        self.measurementTableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.removeColumnAction = QtWidgets.QAction( "remove selected column", self)
        self.reAnalyzeAction = QtWidgets.QAction( "re analyze data", self )
        self.removeColumnAction.triggered.connect( self.onRemoveMeasurementColumn  )
        self.reAnalyzeAction.triggered.connect( self.onReAnalyze )
        self.measurementTableView.addAction( self.removeColumnAction )
        self.measurementTableView.addAction( self.reAnalyzeAction )
        # Context Menu for Parameters Table
        self.parameterTableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.addManualParameterAction = QtWidgets.QAction( "add manual parameter", self)
        self.addManualParameterAction.triggered.connect( self.parameterModel.addManualParameter  )
        self.parameterTableView.addAction( self.addManualParameterAction )
        self.addParameterToMeasurementAction = QtWidgets.QAction( "add as column to measurement", self)
        self.addParameterToMeasurementAction.triggered.connect( self.onAddParameterToMeasurement )
        self.parameterTableView.addAction( self.addParameterToMeasurementAction )
        self.timespanComboBox.addItems( self.timespans )
        self.timespanComboBox.setCurrentIndex( self.settings.timespan )
        isCustom = self.timespans[self.settings.timespan] == 'Custom'
        self.timespanComboBox.currentIndexChanged[int].connect( self.onChangeTimespan )
        self.container.beginInsertMeasurement.subscribe( self.measurementModel.beginInsertRows )
        self.container.endInsertMeasurement.subscribe( self.measurementModel.endInsertRows )  
        self.container.measurementsUpdated.subscribe( self.measurementModel.setMeasurements  )
        self.measurementTableView.selectionModel().currentChanged.connect( self.onActiveInstrumentChanged )
        self.refreshButton.clicked.connect( self.onFilterRefresh )
        # DateTimeEdit
        self.fromDateTimeEdit.setDateTime( self.settings.fromDateTimeEdit )
        self.toDateTimeEdit.setDateTime( self.settings.toDateTimeEdit )
        self.fromDateTimeEdit.dateTimeChanged.connect( partial( self.setDateTimeEdit, 'fromDateTimeEdit') )
        self.toDateTimeEdit.dateTimeChanged.connect( partial( self.setDateTimeEdit, 'toDateTimeEdit') )
        self.toDateTimeEdit.setEnabled( isCustom )
        self.fromDateTimeEdit.setEnabled( isCustom )
        self.plainTextEdit.editingFinished.connect( self.onCommentFinished )
        self.onFilterRefresh()
        self.scanNameFilterButton.clicked.connect( self.onFilterButton )
        self.updateComboBoxes()
        self.plotButton.clicked.connect( self.onCreatePlot )
        self.updatePlotButton.clicked.connect( self.onUpdatePlot )
        self.updateAllPlotsButton.clicked.connect( self.onUpdateAll )
        self.xComboBox.currentIndexChanged[str].connect( partial(self.onComboBoxChanged, 'plotXAxis') )
        self.yComboBox.currentIndexChanged[str].connect( partial(self.onComboBoxChanged, 'plotYAxis') )
        self.windowComboBox.currentIndexChanged[str].connect( partial(self.onComboBoxChanged, 'plotWindow') )
        self.xUnitEdit.setText( self.settings.xUnit )
        self.yUnitEdit.setText( self.settings.yUnit )
        self.xUnitEdit.editingFinished.connect( partial(self.onEditingFinished, 'xUnit', 'xUnitEdit'))
        self.yUnitEdit.editingFinished.connect( partial(self.onEditingFinished, 'yUnit', 'yUnitEdit'))
        restoreGuiState( self, self.config.get(self.configname+".guiSate") )

    def onlyCheckSelected(self):
        self.scanNameTableModel.showAll(showOnlyThese=set([i.row() for i in self.scanNameTableView.selectedIndexes()]))

    def addTraceui(self, scan, traceui ):
        self.traceuiLookup[scan] = traceui 
        self.plotWindowIndex = dict( (("{0}.{1}".format(key, item), (ui, item, d)) for key, ui in self.traceuiLookup.items() for item, d in ui.graphicsViewDict.items()) )
        updateComboBoxItems( self.windowComboBox, sorted(self.plotWindowIndex.keys()), self.settings.plotWindow )
        self.settings.plotWindow = firstNotNone( self.settings.plotWindow, str(self.windowComboBox.currentText()) )

    def onEditingFinished(self, attr, uiElem):
        setattr( self.settings, attr, str(getattr(self, uiElem).text()) )
        
    def onComboBoxChanged(self, attr, value):
        setattr( self.settings, attr, str(value) )
        
    def onFilterSelection(self, scanNames ):
        if self.settings.filterByScanName:
            self.container.setScanNameFilter( [name for name, enabled in scanNames.items() if enabled] if self.settings.filterByScanName else None  )            
        
    def onFilterButton(self, value):
        self.settings.filterByScanName = value
        self.container.setScanNameFilter( [name for name, enabled in self.scanNameTableModel.scanNames.items() if enabled] if self.settings.filterByScanName else None )
        
    def onAddParameterToMeasurement(self):
        if self.currentMeasurement is not None:
            for index in sorted(unique([ i.row() for i in self.parameterTableView.selectedIndexes() ])):
                param = self.currentMeasurement.parameters[index]
                self.measurementModel.addColumn( ('parameter', param.space.name, param.name) )
            self.updateComboBoxes()
                
    def updateComboBoxes(self):
        self.axisDict = dict( {"Started": ('measurement', None, 'startDate') } )
        self.axisDict.update( dict( ((col[2], col) for col in self.measurementModel.extraColumns) ) )
        updateComboBoxItems(self.xComboBox, sorted(self.axisDict.keys()), self.settings.plotXAxis)
        updateComboBoxItems(self.yComboBox, sorted(self.axisDict.keys()), self.settings.plotYAxis)
        self.settings.plotXAxis = firstNotNone( self.settings.plotXAxis, str(self.xComboBox.currentText()) )
        self.settings.plotYAxis = firstNotNone( self.settings.plotYAxis, str(self.yComboBox.currentText()) )
        
    def onAddResultToMeasurement(self):
        if self.currentMeasurement is not None:
            for index in sorted(unique([ i.row() for i in self.resultTableView.selectedIndexes() ])):
                result = self.currentMeasurement.results[index]
                self.measurementModel.addColumn( ('result', None, result.name) )
            self.updateComboBoxes()
                        
    def onRemoveMeasurementColumn(self):
        for index in sorted(unique([ i.column() for i in self.measurementTableView.selectedIndexes() if i.column()>=self.measurementModel.coreColumnCount])):
            self.measurementModel.removeColumn(index)
            self.updateComboBoxes()
            
    def onReAnalyze(self):
        for index in sorted(unique([ i.row() for i in self.measurementTableView.selectedIndexes() ])):
            self.container.measurements[index]
                        
    def onCommentFinished(self, document):
        if self.currentMeasurement is not None:
            self.currentMeasurement.longComment = str(document.toPlainText())
            self.plainTextEdit.setModified(False)
            self.currentMeasurement._sa_instance_state.session.commit()

    def setDateTimeEdit(self, attr, value):
        setattr( self.settings, attr, value.toPyDateTime() )

    def onChangeTimespan(self, index):
        self.settings.timespan = index
        isCustom = self.timespans[index] == 'Custom'
        self.toDateTimeEdit.setEnabled( isCustom )
        self.fromDateTimeEdit.setEnabled( isCustom )
        self.onFilterRefresh()

    def saveConfig(self):
        self.config[self.configname] = self.settings
        self.config[self.configname+".guiSate"] = saveGuiState( self )
        
    def onActiveInstrumentChanged(self, modelIndex, modelIndex2 ):
        measurement = self.container.measurements[modelIndex.row()]
        self.parameterModel.setParameters( measurement.parameters )
        self.resultModel.setResults( measurement.results )
        self.plainTextEdit.setPlainText( firstNotNone( measurement.longComment, "" ) )
        self.currentMeasurement = measurement
        
    def onFilterRefresh(self):
        self.container.query( *self.fromToTimeLookup[self.settings.timespan](datetime.now()) )
        
    def onCreatePlot(self): 
        self.doCreatePlot( self.axisDict[self.settings.plotXAxis], self.axisDict[self.settings.plotYAxis], self.settings.plotWindow )
        self.cacheGarbageCollect()
        
    def onUpdatePlot(self):
        self.doCreatePlot( self.axisDict[self.settings.plotXAxis], self.axisDict[self.settings.plotYAxis], self.settings.plotWindow, update=True )
        self.cacheGarbageCollect()        
        
    def cacheGarbageCollect(self):
        for key, (ref, _) in list(self.cache.items()):
            if ref() is None:
                self.cache.pop(key)
        
    def getParameter(self, measurement, space, name):
        param = measurement.parameterByName(space, name)
        return (param.value, None, None) if param is not None and not math.isinf(param.value.m) else (None, None, None)
        
    def getResult(self, measurement, space, name):
        result = measurement.resultByName(name)
        return (result.value, result.bottom, result.top) if result is not None and not math.isinf(result.value.m) else (None, None, None)

    def getData(self, xDataDef, yDataDef):
        xDataList = list()
        yDataList = list()
        bottomList = list()
        topList = list()
        xsource, xspace, xname = xDataDef
        ysource, yspace, yname = yDataDef
        selectedRows = set(unique([ i.row() for i in self.measurementTableView.selectedIndexes() ]))
        selectedRows = None if len(selectedRows)<2 else selectedRows
        for index, measurement in enumerate(self.measurementModel.measurements):
            if not selectedRows or index in selectedRows:
                xData, _, _ = self.sourceLookup[xsource](measurement, xspace, xname)
                yData, bottom, top  = self.sourceLookup[ysource](measurement, yspace, yname)
                if xData is not None and yData is not None:
                    xDataList.append( xData )
                    yDataList.append( yData )
                    if bottom is not None:
                        bottomList.append( bottom )
                    if top is not None:
                        topList.append( top )
        if len(bottomList)==len(topList)==len(xDataList):
            return xDataList, yDataList, bottomList, topList
        return xDataList, yDataList, None, None
            
    def doCreatePlot(self, xDataDef, yDataDef, plotName, update=False ):
        ref, _ = self.cache.get( ( xDataDef, yDataDef ), (lambda: None, None)) 
        plottedTrace = ref() if update else None # get plottedtrace from the weakref if exists       
        # Assemble data
        xData, yData, bottomData, topData = self.getData(xDataDef, yDataDef)
        if len(xData)==0:
            logging.getLogger(__name__).warning("Nothing to plot")
        else:
            if xDataDef==('measurement', None, 'startDate'):
                epoch = datetime(1970, 1, 1) - timedelta(seconds=self.utcOffset) if xData[0].tzinfo is None else datetime(1970, 1, 1).replace(tzinfo=pytz.utc)
                time = numpy.array([(value - epoch).total_seconds() for value in xData])
                if plottedTrace is None:  # make a new plotted trace
                    trace = TraceCollection(record_timestamps=False)
                    trace.name = "{0} versus {1}".format( yDataDef[2], xDataDef[2 ])
                    _, yUnit = (None, self.settings.yUnit) if self.settings.yUnit else (yData[0].m, "{:~}".format(yData[0].units))
                    trace.y = numpy.array([d.m_as(yUnit) for d in yData])
                    trace.x = time
                    if topData is not None and bottomData is not None:
                        trace.top = numpy.array([d.m_as(yUnit) for d in topData])
                        trace.bottom = numpy.array([d.m_as(yUnit) for d in bottomData])
                    traceui, item, view = self.plotWindowIndex[plotName]
                    plottedTrace = PlottedTrace(trace, view, xAxisLabel="local time", windowName=item)
                    #plottedTrace.trace.filenameCallback = partial( WeakMethod.ref(plottedTrace.traceFilename), "" )
                    traceui.addTrace( plottedTrace, pen=-1)
                    traceui.resizeColumnsToContents()
                    self.cache[(xDataDef, yDataDef)] = ( weakref.ref(plottedTrace), (xDataDef, yDataDef, plotName) )
                    trace.description["traceFinalized"] = datetime.now(pytz.utc)
                else:  # update the existing plotted trace
                    trace = plottedTrace.trace
                    _, yUnit = (None, self.settings.yUnit) if self.settings.yUnit else mag_unit(yData[0])
                    trace.y = numpy.array([d.m_as(yUnit) for d in yData])
                    trace.x = time
                    if topData is not None and bottomData is not None:
                        trace.top = numpy.array([d.m_as(yUnit) for d in topData])
                        trace.bottom = numpy.array([d.m_as(yUnit) for d in bottomData])
                    trace.description["traceFinalized"] = datetime.now(pytz.utc)
                    plottedTrace.replot()     
            else:
                if plottedTrace is None:  # make a new plotted trace
                    trace = TraceCollection(record_timestamps=False)
                    trace.name = "{0} versus {1}".format( yDataDef[2], xDataDef[2 ])
                    _, yUnit = (None, self.settings.yUnit) if self.settings.yUnit else mag_unit(yData[0])
                    _, xUnit = (None, self.settings.xUnit) if self.settings.xUnit else mag_unit(xData[0])
                    trace.y = numpy.array([d.m_as(yUnit) for d in yData])
                    trace.x = numpy.array([d.m_as(xUnit) for d in xData])
                    if topData is not None and bottomData is not None:
                        trace.top = numpy.array([d.m_as(yUnit) for d in topData])
                        trace.bottom = numpy.array([d.m_as(yUnit) for d in bottomData])
                    traceui, item, view = self.plotWindowIndex[plotName]
                    plottedTrace = PlottedTrace(trace, view, xAxisLabel=xDataDef[2], windowName=item)
                    traceui.addTrace( plottedTrace, pen=-1)
                    traceui.resizeColumnsToContents()
                    self.cache[(xDataDef, yDataDef)] = ( weakref.ref(plottedTrace), (xDataDef, yDataDef, plotName) )
                    trace.description["traceFinalized"] = datetime.now(pytz.utc)
                else:  # update the existing plotted trace
                    trace = plottedTrace.trace
                    _, yUnit = (None, self.settings.yUnit) if self.settings.yUnit else mag_unit(yData[0])
                    _, xUnit = (None, self.settings.xUnit) if self.settings.xUnit else mag_unit(xData[0])
                    trace.y = numpy.array([d.m_as(yUnit) for d in yData])
                    trace.x = numpy.array([d.m_as(xUnit) for d in xData])
                    if topData is not None and bottomData is not None:
                        trace.top = numpy.array([d.m_as(yUnit) for d in topData])
                        trace.bottom = numpy.array([d.m_as(yUnit) for d in bottomData])
                    plottedTrace.replot()
                    trace.description["traceFinalized"] = datetime.now(pytz.utc)
                
    def onUpdateAll(self):
        for ref, context in list(self.cache.values()):
            if ref() is not None:
                self.doCreatePlot(*context, update=True )
        self.cacheGarbageCollect()

    @QtCore.pyqtSlot(list)
    def onOpenMeasurementLog(self, traceCreationList):
        """Called when traceui emits signal to open the corresponding measurement log entry"""
        self.show()
        self.raise_()
        self.activateWindow()
        measurementDict = self.measurementModel.container.measurementDict
        measurements = self.measurementModel.measurements
        selection = QtCore.QItemSelection()
        self.measurementTableView.selectionModel().select(selection, QtCore.QItemSelectionModel.Clear) #clear selection
        leftInd=None
        for traceCreation in traceCreationList:
            measurement = measurementDict.get(traceCreation)
            row = measurements.index(measurement) if measurement in measurements else -1
            if row >= 0:
                leftInd = self.measurementModel.index(row, 0)
                rightInd = self.measurementModel.index(row, self.measurementModel.columnCount()-1)
                selection.select(leftInd, rightInd) #add the specified measurement to the selection
        self.measurementTableView.selectionModel().select(selection, QtCore.QItemSelectionModel.Select) #select full selection
        if leftInd:
            self.measurementTableView.scrollTo(leftInd) #scroll to left column of last measurement in list
        self.measurementTableView.setFocus(True)