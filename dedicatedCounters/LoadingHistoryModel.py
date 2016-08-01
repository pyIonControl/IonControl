# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore
from dateutil.tz import tzlocal

class LoadingHistoryModel(QtCore.QAbstractTableModel):
    def __init__(self, history, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self._history = history

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self._history) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 3
 
    def data(self, index, role): 
        if index.isValid():
            item = self._history[len(self.history)-index.row()-1]
            #print item.trappedAt, item.trappingTime, item.trappingTime
            return { (QtCore.Qt.DisplayRole, 0): item.trappingTime.astimezone(tzlocal()).strftime('%Y-%m-%d %H:%M:%S'),
                     (QtCore.Qt.DisplayRole, 1): self.formatDelta(item.loadingDuration) if item.loadingDuration else None,
                     (QtCore.Qt.DisplayRole, 2): self.formatDelta(item.trappingDuration) if item.trappingDuration else None,
                     }.get((role, index.column()), None)
        return None
        
    def flags(self, index ):
        return  QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return { 0: 'Trapped at',
                         1: 'Loading Time',
                         2: 'Trapping Time' }.get(section)
        return None #QtCore.QVariant()
        
    @property
    def history(self):
        return self._history
        
    @history.setter
    def history(self, value):
        self.beginResetModel()
        self._history = value
        self.endResetModel()
        
    def append(self, value):
        self.beginInsertRows(QtCore.QModelIndex(), 0, 0)
        self.history.append(value)
        self.endInsertRows()
 
    def formatDelta(self, delta):
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        hours += delta.days * 24
        seconds += delta.microseconds * 1e-6
        components = list()
        if (hours>0): components.append("{0}".format(hours))
        components.append("{0:02d}:{1:02.0f}".format(int(minutes), seconds))
        return ":".join(components)

    def updateLast(self):
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0, 2))
        
    def beginInsertRows(self, event):
        super(LoadingHistoryModel, self).beginInsertRows(QtCore.QModelIndex(), event.first, event.last )
        
        