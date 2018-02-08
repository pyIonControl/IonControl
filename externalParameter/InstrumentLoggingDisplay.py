# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui
import PyQt5.uic

from modules.SequenceDict import SequenceDict
from uiModules.KeyboardFilter import KeyListFilter
from collections import defaultdict
from externalParameter.InputData import InputData

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/InstrumentLoggingDisplay.ui')
UiForm, UiBase = PyQt5.uic.loadUiType(uipath)

def defaultFontsize():
    return 10

class InstrumentLoggingDisplayTableModel( QtCore.QAbstractTableModel ):
    valueChanged = QtCore.pyqtSignal(str, object)
    def __init__(self, controlUi, config, parameterList=None, parent=None):
        super(InstrumentLoggingDisplayTableModel, self).__init__(parent)
        self.names = list()
        self.controlUi = controlUi
        self.config = config
        self.headerLookup = ['Name', 'Raw', 'Decimated', 'Calibrated']
        self.dataLookup =  { (QtCore.Qt.DisplayRole, 0): lambda row: self.data.keyAt(row),
                             (QtCore.Qt.DisplayRole, 1): lambda row: str(self.data.at(row).raw),
                             (QtCore.Qt.DisplayRole, 3): lambda row: str(self.data.at(row).calibrated),
                             (QtCore.Qt.DisplayRole, 2): lambda row: str(self.data.at(row).decimated),
                             (QtCore.Qt.FontRole, 0): lambda row: QtGui.QFont("MS Shell Dlg 2", self.fontsizeCache[(self.data.keyAt(row), 0)]),
                             (QtCore.Qt.FontRole, 1): lambda row: QtGui.QFont("MS Shell Dlg 2", self.fontsizeCache[(self.data.keyAt(row), 1)]),
                             (QtCore.Qt.FontRole, 2): lambda row: QtGui.QFont("MS Shell Dlg 2", self.fontsizeCache[(self.data.keyAt(row), 2)]),
                             (QtCore.Qt.FontRole, 3): lambda row: QtGui.QFont("MS Shell Dlg 2", self.fontsizeCache[(self.data.keyAt(row), 3)])
                     }
        self.data = SequenceDict()
        self.fontsizeCache = self.config.get("InstrumentLoggingDisplayTableModel.FontsizeCache", defaultdict(defaultFontsize))
        self.inputChannels = dict()

    def resize(self, index, keyboardkey):
        if keyboardkey==QtCore.Qt.Key_Equal:
            self.fontsizeCache[(self.data.keyAt(index.row()), index.column())] = 10
        elif keyboardkey==QtCore.Qt.Key_Plus:
            self.fontsizeCache[(self.data.keyAt(index.row()), index.column())] += 1
        elif keyboardkey==QtCore.Qt.Key_Minus:
            self.fontsizeCache[(self.data.keyAt(index.row()), index.column())] -= 1
        self.dataChanged.emit(index, index)
            
        
    def setInputChannels(self, inputChannels ):
        self.beginResetModel()
        # drop everything that is not in the enabled parameter keys
        for key in list(self.data.keys()):
            if key not in inputChannels:
                self.data.pop(key)
                channel = self.inputChannels.pop(key)
                channel.newData.disconnect(self.updateHandler)
        for key, channel in inputChannels.items():
            if key not in self.data:
                self.data[key] = InputData() 
                channel.newData.connect(self.updateHandler)
                self.inputChannels[key] = channel
        self.endResetModel()
        
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.data)
    
    def columnCount(self,  parent=QtCore.QModelIndex()):
        return 4
    
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get( (role, index.column()), lambda row: None)(index.row())
        return None

    def flags(self, index ):
        return  QtCore.Qt.ItemIsEnabled |  QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole) and (orientation == QtCore.Qt.Horizontal): 
            return self.headerLookup[section]
        return None #QtCore.QVariant()
 
    def updateHandler(self, name, data):
        if name in self.data and data is not None:
            self.data[name].raw = data[1]
            index = self.data.index(name)
            leftInd = self.createIndex(index, 1)
            rightInd = self.createIndex(index, 3)
            self.dataChanged.emit(leftInd, rightInd) 
 
    def update(self, key, value):
        if key in self.data:
            self.data[key].update(value)
            index = self.data.index(key)
            leftInd = self.createIndex(index, 1)
            rightInd = self.createIndex(index, 3)
            self.dataChanged.emit(leftInd, rightInd) 
            
    def saveConfig(self):
        self.config["InstrumentLoggingDisplayTableModel.FontsizeCache"] = self.fontsizeCache

class InstrumentLoggingDisplay(UiForm, UiBase):   
    def __init__(self, config, parent=None):
        UiBase.__init__(self, parent)
        UiForm.__init__(self)
        self.config = config
    
    def setupUi(self, EnabledParameters, MainWindow):
        UiForm.setupUi(self, MainWindow)
        self.tableModel = InstrumentLoggingDisplayTableModel(self, self.config)
        self.tableView.setModel( self.tableModel )
        self.setupParameters(EnabledParameters)
        self.filter = KeyListFilter( [QtCore.Qt.Key_Plus, QtCore.Qt.Key_Minus, QtCore.Qt.Key_Equal] )
        self.filter.keyPressed.connect( self.onResize )
        self.tableView.installEventFilter(self.filter)
        
    def setupParameters(self, inputChannels ):
        self.tableModel.setInputChannels( inputChannels )
        self.tableView.horizontalHeader().setStretchLastSection(True)
        
    def update(self, key, value):
        self.tableModel.update(key, value)   
        
    def onResize(self, key):
        indexes = self.tableView.selectedIndexes()
        for index in indexes:
            self.tableModel.resize( index, key )
            
    def saveConfig(self):
        self.tableModel.saveConfig()

    
