# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui
from os.path import exists
from _functools import partial
from modules.firstNotNone import firstNotNone
from modules.enum import enum
import os.path
from dateutil.tz import tzlocal
import pytz

class MeasurementTableModel(QtCore.QAbstractTableModel):
    valueChanged = QtCore.pyqtSignal(object)
    headerDataLookup = ['Plot', 'Study', 'Scan', 'Name', 'Evaluation', 'Target', 'Parameter', 'Pulse Program', 'Started', 'Comment', 'Filename' ]
    column = enum('plot', 'study', 'scan', 'name', 'evaluation', 'target', 'parameter', 'pulseprogram', 'started', 'comment', 'filename')
    coreColumnCount = 11
    measurementModelDataChanged = QtCore.pyqtSignal(str, str, str) #string with trace creation date, change type, new value
    def __init__(self, measurements, extraColumns, traceuiLookup, container=None, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.container = container 
        self.extraColumns = extraColumns  # list of tuples (source, space, name)
        # measurements are given as a list
        self.measurements = measurements
        self.flagsLookup = { self.column.plot: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled,
                             self.column.comment: QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled,
                            }
        self.failedBG =  QtGui.QColor(0xff, 0xa6, 0xa6, 0xff)
        self.defaultBG = QtGui.QColor(QtCore.Qt.white)
        self.dataLookup = {  (QtCore.Qt.CheckStateRole, self.column.plot): lambda row: self.isPlotted(self.measurements[row]),
                             (QtCore.Qt.DisplayRole, self.column.study): lambda row: self.measurements[row].study,
                             (QtCore.Qt.DisplayRole, self.column.scan): lambda row: self.measurements[row].scanType,
                             (QtCore.Qt.DisplayRole, self.column.name): lambda row: self.measurements[row].scanName,
                             (QtCore.Qt.DisplayRole, self.column.evaluation): lambda row: self.measurements[row].evaluation,
                             (QtCore.Qt.DisplayRole, self.column.target): lambda row: self.measurements[row].scanTarget,
                             (QtCore.Qt.DisplayRole, self.column.parameter): lambda row: self.measurements[row].scanParameter,
                             (QtCore.Qt.DisplayRole, self.column.pulseprogram): lambda row: self.measurements[row].scanPP,
                             (QtCore.Qt.DisplayRole, self.column.started): lambda row: self.measurements[row].startDate.astimezone(tzlocal()).strftime('%Y-%m-%d %H:%M:%S'),
                             (QtCore.Qt.DisplayRole, self.column.comment): lambda row: self.measurements[row].comment,
                             (QtCore.Qt.DisplayRole, self.column.filename): self.getFilename,
                             (QtCore.Qt.EditRole, self.column.comment): lambda row: self.measurements[row].comment,
                             (QtCore.Qt.BackgroundColorRole, self.column.plot): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.study): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.scan): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.name): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.evaluation): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.target): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.parameter): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.pulseprogram): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.started): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.comment): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG,
                             (QtCore.Qt.BackgroundColorRole, self.column.filename): lambda row: self.defaultBG if self.measurements[row].failedAnalysis is None else self.failedBG
                             }
        self.setDataLookup = { (QtCore.Qt.CheckStateRole, self.column.plot): self.setPlotted,
                               (QtCore.Qt.EditRole, self.column.comment): self.setComment
                              }
        self.traceuiLookup = traceuiLookup

    def getFilename(self, row):
        filename = self.measurements[row].filename
        if filename is None:
            return None
        return os.path.split(filename)[1]

    @QtCore.pyqtSlot(str, str, str)
    def onTraceModelDataChanged(self, traceCreation, changeType, data):
        """Trace data changed via traceui. Update model."""
        traceCreation = str(traceCreation)
        changeType = str(changeType)
        data=str(data)
        measurement = self.container.measurementDict.get(traceCreation)
        row = self.measurements.index(measurement) if measurement in self.measurements else -1
        if row >= 0:
            if changeType=='comment':
                self.setComment(row, data)
                self.dataChanged.emit(self.index(row, self.column.comment), self.index(row, self.column.comment))
            elif changeType=='isPlotted':
                self.dataChanged.emit(self.index(row, self.column.plot), self.index(row, self.column.plot))
            elif changeType=='filename':
                self.setFilename(row, data)
                self.dataChanged.emit(self.index(row, self.column.filename), self.index(row, self.column.filename))

    @QtCore.pyqtSlot(str)
    def onTraceRemoved(self, traceCreation):
        """If the signal that a trace was removed is received, remove it from the measurement dict"""
        traceCreation = str(traceCreation)
        measurement = self.container.measurementDict.get(traceCreation)
        row = self.measurements.index(measurement) if measurement in self.measurements else -1
        if measurement:
            self.container.measurementDict.pop(traceCreation)
            if row >= 0:
                self.measurements[row].plottedTraceList = []
                self.dataChanged.emit(self.index(row, self.column.plot), self.index(row, self.column.plot))

    def addColumn(self, extraColumn ):
        self.beginInsertColumns( QtCore.QModelIndex(), self.coreColumnCount+len(self.extraColumns), self.coreColumnCount+len(self.extraColumns))
        self.extraColumns.append( extraColumn )
        self.endInsertColumns()
        
    def removeColumn(self, columnIndex):
        self.beginRemoveColumns( QtCore.QModelIndex(), columnIndex, columnIndex )
        self.extraColumns.pop( columnIndex-self.coreColumnCount )
        self.endRemoveColumns()
        
    def isPlotted(self, measurement):
        count = 0
        plottedTraceList = measurement.plottedTraceList
        total = len(plottedTraceList)
        for pt in plottedTraceList:
            if pt.isPlotted:
                count += 1
        if total==0 or count==0:
            return QtCore.Qt.Unchecked
        if count < total:
            return QtCore.Qt.PartiallyChecked
        return QtCore.Qt.Checked
        
    def setPlotted(self, row, value):
        measurement = self.measurements[row]
        plotted = value == QtCore.Qt.Checked
        if not plotted:
            for pt in measurement.plottedTraceList:
                pt.plot(0)
        else:
            plottedTraceList = measurement.plottedTraceList
            if len(plottedTraceList)>0:
                for pt in plottedTraceList:
                    pt.plot(-1)
            else:
                if measurement.filename is not None and exists(measurement.filename):
                    self.loadTrace(measurement)
                    self.container.measurementDict[str(measurement.startDate.astimezone(pytz.utc))] = measurement
        self.measurementModelDataChanged.emit(str(measurement.startDate.astimezone(pytz.utc)), 'isPlotted', '')
        return True
    
    def loadTrace(self, measurement):
        measurement.plottedTraceList = self.traceuiLookup[measurement.scanType].openFile(measurement.filename)
    
    def setComment(self, row, comment):
        """Set the comment at the specified row"""
        measurement = self.measurements[row]
        if measurement.comment != comment:
            measurement.comment = comment
            measurement._sa_instance_state.session.commit()
            self.measurementModelDataChanged.emit(str(measurement.startDate.astimezone(pytz.utc)), 'comment', comment)
            return True
        else:
            return False

    def setFilename(self, row, filename):
        """Set the filename at the specified row"""
        measurement = self.measurements[row]
        if measurement.filename != filename:
            measurement.filename = filename
            measurement._sa_instance_state.session.commit()
            return True
        else:
            return False
        
    def beginInsertRows(self, event):
        self.firstAdded = event.first
        self.lastAdded = event.last
        return QtCore.QAbstractTableModel.beginInsertRows(self, QtCore.QModelIndex(), event.first, event.last )

    def endInsertRows(self):
        return QtCore.QAbstractTableModel.endInsertRows(self)
        
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.measurements) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return self.coreColumnCount + len(self.extraColumns)
 
    def data(self, index, role): 
        if index.isValid():
            if index.column()<self.coreColumnCount:
                return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
            else:
                source, space, name = self.extraColumns[index.column()-self.coreColumnCount]
                if source=='parameter':
                    param = self.measurements[index.row()].parameterByName(space, name)
                    value = param.value if param is not None else None
                elif source=='result':
                    result = self.measurements[index.row()].resultByName(name)
                    value = result.value if result is not None else None
                if role==QtCore.Qt.DisplayRole:
                    return str(value) if value is not None else None
                elif role==QtCore.Qt.EditRole:
                    return value                    
        return None
        
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda row, value: False)(index.row(), value)       
    
    def flags(self, index):
        return self.flagsLookup.get( index.column(), QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled )

    def headerData(self, section, orientation, role):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section] if section<self.coreColumnCount else self.extraColumns[section-self.coreColumnCount][2]
            elif (orientation == QtCore.Qt.Vertical):
                return self.measurements[section].id
        return None  # QtCore.QVariant()
                
    def sort(self, column, order):
        if column == 0 and self.variables:
            self.measurements.sort(reverse=order == QtCore.Qt.DescendingOrder)
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.variables) - 1, 1))
            
    def setMeasurements(self, event):
        self.beginResetModel()
        self.measurements = event.measurements
        self.endResetModel()
        