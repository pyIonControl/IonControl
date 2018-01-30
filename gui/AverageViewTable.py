# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
import PyQt5.uic

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from modules.RunningStat import RunningStat
from modules.round import roundToStdDev, roundToNDigits
from uiModules.KeyboardFilter import KeyListFilter

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/AverageViewTable.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class Settings(AttributeComparisonEquality):
    def __init__(self):
        self.pointSize = 12


class AverageViewTableModel(QtCore.QAbstractTableModel):
    headerDataLookup = [ 'Current Value', 'Sample Mean', 'Standard error', 'Name']
    def __init__(self, stats, config, parent=None, *args): 
        """ datain: a list where each item is a row
        
        """
        QtCore.QAbstractTableModel.__init__(self, parent, *args) 
        self.stats = stats
        self.dataLookup = { (QtCore.Qt.DisplayRole, 0): lambda row: str(roundToNDigits(self.stats[row].currentValue, 3)),
                         (QtCore.Qt.DisplayRole, 1): lambda row: str(roundToStdDev(self.stats[row].mean, self.stats[row].stderr)),
                         (QtCore.Qt.DisplayRole, 2): lambda row: str(roundToNDigits(self.stats[row].stderr, 2)),
                         (QtCore.Qt.DisplayRole, 3): lambda row: self.names[row] if self.names and len(self.names)>row else None,
                         (QtCore.Qt.FontRole, 0):    lambda row: self.dataFont(row),
                         (QtCore.Qt.FontRole, 1):    lambda row: self.dataFont(row),
                         (QtCore.Qt.FontRole, 2):    lambda row: self.dataFont(row)
                         #(QtCore.Qt.SizeHintRole,0): lambda row: 
                         }
        self.names = None
        self.config = config
        self.settings = config.get("AverageViewTableModel", Settings())
 
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda row: None)(index.row())
        return None
        
    def dataFont(self, row):
        font = QtGui.QFont()
        font.setPointSize(self.settings.pointSize)
        return font
    
    def changeSize(self, amount):
        self.settings.pointSize = min( max(self.settings.pointSize+amount, 6), 48 )
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(len(self.stats)-1, 2) )
    
    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None 

    def flags(self, index ):
        return  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.stats) 
        
    def columnCount(self, parent=QtCore.QModelIndex()): 
        return 4
 
    def resize(self, length):
        self.beginResetModel()
        del self.stats[0:]
        self.stats += [RunningStat() for _ in range(length)]
        self.endResetModel()
        
    def add(self, stats):
        if len(stats)!=len(self.stats):
            self.resize( len(stats) )
        for index, element in enumerate(stats):
            self.stats[index].add(element)
        self.dataChanged.emit(self.index(0, 0), self.index(len(stats)-1, 3))
                
    def setNames(self, names):
        self.names = names if names else None
        
    def saveConfig(self):
        self.config["AverageViewTableModel"] = self.settings
        
    def clear(self):
        for stat in self.stats:
            stat.clear()
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(2, len(self.stats)-1))


class AverageViewTable(Form, Base):
    def __init__(self, config):
        Form.__init__(self)
        Base.__init__(self)
        self.stats = list()
        self.config = config
        self.configName = 'AverageView'
    
    def setupUi(self):
        super(AverageViewTable, self).setupUi(self)
        self.model = AverageViewTableModel(self.stats, self.config)
        self.tableView.setModel(self.model)
        #self.tableView.resizeColumnsToContents()
        self.tableView.verticalHeader().hide()
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.clearButton.clicked.connect( self.onClear)
        self.keyFilter = KeyListFilter( [QtCore.Qt.Key_Plus, QtCore.Qt.Key_Minus] )
        self.keyFilter.keyPressed.connect( self.changeSize )
        self.tableView.installEventFilter( self.keyFilter )
        self.tableView.resizeRowsToContents()
        columnWidths = self.config.get(self.configName+'.columnWidths')
        if columnWidths:
            self.tableView.horizontalHeader().restoreState(columnWidths)

    def changeSize(self, key):
        self.model.changeSize( 1 if key==QtCore.Qt.Key_Plus else -1 )
        self.tableView.resizeRowsToContents()
        self.tableView.resizeColumnsToContents()

    def add(self, data):
        if data is not None:
            self.model.add(data)
            self.setCountLabel()
        
    def onClear(self):
        self.model.clear()
        self.setCountLabel()

    def setNames(self, names):
        self.model.setNames(names)
        
    def saveConfig(self):
        self.model.saveConfig()
        self.config[self.configName+'.columnWidths'] = self.tableView.horizontalHeader().saveState()

    def setCountLabel(self):
        self.countLabel.setText( "{0}".format( self.stats[0].count if self.stats else 0))
 

if __name__=="__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = AverageViewTable(dict())
    ui.setupUi()
    ui.setNames(["One", "Two"])
    ui.add( [2, 3] )
    ui.add( [4, 5] )
    ui.add( [6, 7] )
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
