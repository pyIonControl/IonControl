# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore
from voltageControl.ShuttlingDefinition import ShuttlingGraph
from uiModules.SoftStart import StartTypes

class ShuttleEdgeTableModel(QtCore.QAbstractTableModel):
    def __init__(self, config, shuttlingGraph, parent=None, *args): 
        QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.config = config 
        self.shuttlingGraph = shuttlingGraph
        self.columnHeaders = ['From Name', 'From Line', 'To Name', 'To Line', 'Steps per line', 'Idle count', 'timer per sample', 'total time', 'Start Type', 'Start length', 'Stop Type', 'Stop length' ]
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda row: self.shuttlingGraph[row].startName,
                             (QtCore.Qt.DisplayRole, 1): lambda row: self.shuttlingGraph[row].startLine,
                             (QtCore.Qt.DisplayRole, 2): lambda row: self.shuttlingGraph[row].stopName,
                             (QtCore.Qt.DisplayRole, 3): lambda row: self.shuttlingGraph[row].stopLine,
                             (QtCore.Qt.DisplayRole, 4): lambda row: self.shuttlingGraph[row].steps,
                             (QtCore.Qt.DisplayRole, 5): lambda row: self.shuttlingGraph[row].idleCount,
                             (QtCore.Qt.DisplayRole, 6): lambda row: str(self.shuttlingGraph[row].timePerSample),
                             (QtCore.Qt.ToolTipRole, 6): lambda row: str(1/self.shuttlingGraph[row].timePerSample),
                             (QtCore.Qt.DisplayRole, 7): lambda row: str(self.shuttlingGraph[row].totalTime),
                             (QtCore.Qt.DisplayRole, 8): lambda row: str(self.shuttlingGraph[row].startType),
                             (QtCore.Qt.DisplayRole, 9): lambda row: str(self.shuttlingGraph[row].startLength),
                             (QtCore.Qt.DisplayRole, 10): lambda row: str(self.shuttlingGraph[row].stopType),
                             (QtCore.Qt.DisplayRole, 11): lambda row: str(self.shuttlingGraph[row].stopLength),
                             (QtCore.Qt.EditRole, 0): lambda row: self.shuttlingGraph[row].startName,
                             (QtCore.Qt.EditRole, 1): lambda row: self.shuttlingGraph[row].startLine,
                             (QtCore.Qt.EditRole, 2): lambda row: self.shuttlingGraph[row].stopName,
                             (QtCore.Qt.EditRole, 3): lambda row: self.shuttlingGraph[row].stopLine,
                             (QtCore.Qt.EditRole, 4): lambda row: self.shuttlingGraph[row].steps,
                             (QtCore.Qt.EditRole, 5): lambda row: self.shuttlingGraph[row].idleCount,
                             (QtCore.Qt.EditRole, 8): lambda row: self.shuttlingGraph[row].startType,
                             (QtCore.Qt.EditRole, 9): lambda row: self.shuttlingGraph[row].startLength,
                             (QtCore.Qt.EditRole, 10): lambda row: self.shuttlingGraph[row].stopType,
                             (QtCore.Qt.EditRole, 11): lambda row: self.shuttlingGraph[row].stopLength,
                              }
        self.setDataLookup = {(QtCore.Qt.EditRole, 0): ShuttlingGraph.setStartName,
                             (QtCore.Qt.EditRole, 1): ShuttlingGraph.setStartLine,
                             (QtCore.Qt.EditRole, 2): ShuttlingGraph.setStopName,
                             (QtCore.Qt.EditRole, 3): ShuttlingGraph.setStopLine,
                             (QtCore.Qt.EditRole, 4): ShuttlingGraph.setSteps,
                             (QtCore.Qt.EditRole, 5): ShuttlingGraph.setIdleCount,
                             (QtCore.Qt.EditRole, 8): ShuttlingGraph.setStartType,
                             (QtCore.Qt.EditRole, 9): ShuttlingGraph.setStartLength,
                             (QtCore.Qt.EditRole, 10): ShuttlingGraph.setStopType,
                             (QtCore.Qt.EditRole, 11): ShuttlingGraph.setStopLength
                              }

    def choice(self, index):
        if index.column() in  (8, 10):
            return list(StartTypes.keys())
        return None
                        
    def setShuttlingGraph(self, shuttlingGraph):
        self.beginResetModel()
        self.shuttlingGraph = shuttlingGraph
        self.endResetModel()
                        
    def add(self, edge ):
        if self.shuttlingGraph.isValidEdge(edge):
            self.beginInsertRows(QtCore.QModelIndex(), len(self.shuttlingGraph), len(self.shuttlingGraph))
            self.shuttlingGraph.addEdge(edge)
            self.endInsertRows()
             
    def remove(self, index):
        self.beginRemoveRows(QtCore.QModelIndex(), index, index)
        self.shuttlingGraph.removeEdge(index)
        self.endRemoveRows()
                               
    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.shuttlingGraph) if self.shuttlingGraph else 0
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return len(self.columnHeaders) 

    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
    
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda g, row, value: False)(self.shuttlingGraph, index.row(), value)
        
    def flags(self, index ):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | ( QtCore.Qt.ItemIsEditable if index.column()<6 or index.column()>7 else 0)

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.columnHeaders[section]
            else:
                return str(section)
        return None #QtCore.QVariant()
    
    def setValue(self, index, value):
        return self.setData(index, value, QtCore.Qt.EditRole)
    