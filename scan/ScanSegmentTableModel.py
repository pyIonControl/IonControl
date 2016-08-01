# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
from functools import partial
from modules.firstNotNone import firstNotNone

class ScanSegmentTableModel( QtCore.QAbstractTableModel):
    dataChanged = QtCore.pyqtSignal( object, object )
    headerDataLookup = ['Start', 'Stop', 'Center', 'Span', 'steps', 'stepsize' ]
    def __init__(self, updateSaveStatus, globalVariables, scanSegments=None, parent=None):
        super(ScanSegmentTableModel, self).__init__(parent)
        self.scanSegmentList = scanSegments if scanSegments is not None else list()
        self.updateSaveStatus = updateSaveStatus
        self.setDataLookup =  {  (QtCore.Qt.EditRole, 0): partial( self.setField, 'start'),
                                 (QtCore.Qt.EditRole, 1): partial( self.setField, 'stop'),
                                 (QtCore.Qt.EditRole, 2): partial( self.setField, 'center'),
                                 (QtCore.Qt.EditRole, 3): partial( self.setField, 'span'),
                                 (QtCore.Qt.EditRole, 4): partial( self.setField, 'steps'),
                                 (QtCore.Qt.EditRole, 5): partial( self.setField, 'stepsize'),
                                 (QtCore.Qt.UserRole, 0): partial( self.setFieldText, 'startText'),
                                 (QtCore.Qt.UserRole, 1): partial( self.setFieldText, 'stopText'),
                                 (QtCore.Qt.UserRole, 2): partial( self.setFieldText, 'centerText'),
                                 (QtCore.Qt.UserRole, 3): partial( self.setFieldText, 'spanText'),
                                 (QtCore.Qt.UserRole, 4): partial( self.setFieldText, 'stepsText'),
                                 (QtCore.Qt.UserRole, 5): partial( self.setFieldText, 'stepsizeText')
                                }
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda self, column: str(self.scanSegmentList[column].start),
                             (QtCore.Qt.DisplayRole, 1): lambda self, column: str(self.scanSegmentList[column].stop),
                             (QtCore.Qt.DisplayRole, 2): lambda self, column: str(self.scanSegmentList[column].center),
                             (QtCore.Qt.DisplayRole, 3): lambda self, column: str(self.scanSegmentList[column].span),
                             (QtCore.Qt.DisplayRole, 4): lambda self, column: str(self.scanSegmentList[column].steps),
                             (QtCore.Qt.DisplayRole, 5): lambda self, column: str(self.scanSegmentList[column].stepsize),
                             (QtCore.Qt.EditRole, 0):    lambda self, column: firstNotNone( self.scanSegmentList[column].startText, str(self.scanSegmentList[column].start)),
                             (QtCore.Qt.EditRole, 1):    lambda self, column: firstNotNone( self.scanSegmentList[column].stopText, str(self.scanSegmentList[column].stop)),
                             (QtCore.Qt.EditRole, 2):    lambda self, column: firstNotNone( self.scanSegmentList[column].centerText, str(self.scanSegmentList[column].center)),
                             (QtCore.Qt.EditRole, 3):    lambda self, column: firstNotNone( self.scanSegmentList[column].spanText,  str(self.scanSegmentList[column].span)),
                             (QtCore.Qt.EditRole, 4):    lambda self, column: firstNotNone( self.scanSegmentList[column].stepsText, str(self.scanSegmentList[column].steps)),
                             (QtCore.Qt.EditRole, 5):    lambda self, column: firstNotNone( self.scanSegmentList[column].stepsizeText, str(self.scanSegmentList[column].stepsize)),
                             (QtCore.Qt.BackgroundColorRole, 0): lambda self, column: self.backgroundLookup[(self.scanSegmentList[column].inconsistent, self.scanSegmentList[column]._startText is not None)],
                             (QtCore.Qt.BackgroundColorRole, 1): lambda self, column: self.backgroundLookup[(self.scanSegmentList[column].inconsistent, self.scanSegmentList[column]._stopText is not None)],
                             (QtCore.Qt.BackgroundColorRole, 2): lambda self, column: self.backgroundLookup[(self.scanSegmentList[column].inconsistent, self.scanSegmentList[column]._centerText is not None)],
                             (QtCore.Qt.BackgroundColorRole, 3): lambda self, column: self.backgroundLookup[(self.scanSegmentList[column].inconsistent, self.scanSegmentList[column]._spanText is not None)],
                             (QtCore.Qt.BackgroundColorRole, 4): lambda self, column: self.backgroundLookup[(self.scanSegmentList[column].inconsistent, self.scanSegmentList[column]._stepsText is not None)],
                             (QtCore.Qt.BackgroundColorRole, 5): lambda self, column: self.backgroundLookup[(self.scanSegmentList[column].inconsistent, self.scanSegmentList[column]._stepsizeText is not None)],
                             (QtCore.Qt.ToolTipRole, 0): lambda self, column: self.scanSegmentList[column]._startText if self.scanSegmentList[column]._startText is not None else None,
                             (QtCore.Qt.ToolTipRole, 1): lambda self, column: self.scanSegmentList[column]._stopText if self.scanSegmentList[column]._stopText is not None else None,
                             (QtCore.Qt.ToolTipRole, 2): lambda self, column: self.scanSegmentList[column]._centerText if self.scanSegmentList[column]._centerText is not None else None,
                             (QtCore.Qt.ToolTipRole, 3): lambda self, column: self.scanSegmentList[column]._spanText if self.scanSegmentList[column]._spanText is not None else None,
                             (QtCore.Qt.ToolTipRole, 4): lambda self, column: self.scanSegmentList[column]._stepsText if self.scanSegmentList[column]._stepsText is not None else None,
                             (QtCore.Qt.ToolTipRole, 5): lambda self, column: self.scanSegmentList[column]._stepsizeText if self.scanSegmentList[column]._stepsizeText is not None else None,
                             (QtCore.Qt.FontRole, 4): lambda self, column: self.fontLookup[self.scanSegmentList[column]._stepPreference=='steps'],
                             (QtCore.Qt.FontRole, 5): lambda self, column: self.fontLookup[self.scanSegmentList[column]._stepPreference=='stepsize']
                             }
        self.globalDict = globalVariables
        defaultBG = QtGui.QColor(QtCore.Qt.white)
        inconsistentBG = QtGui.QColor(0xff, 0xa6, 0xa6, 0xff)
        textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
        preferenceFont = QtGui.QFont("MS Shell Dlg 2", -1, QtGui.QFont.DemiBold, False)
        regularFont = QtGui.QFont("MS Shell Dlg 2", -1, QtGui.QFont.Normal, False)
        self.fontLookup = { True: preferenceFont, False: regularFont}
        self.backgroundLookup = { (True, True):inconsistentBG, (True, False):inconsistentBG, (False, True):textBG, (False, False):defaultBG}

    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.row()), lambda index, value: False )(index, value)

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 6
    
    def columnCount(self,  parent=QtCore.QModelIndex()):
        return len(self.scanSegmentList)
    
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.row()), lambda self, row: None)(self, index.column())
        return None
        
    def flags(self, index ):
        return  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Horizontal): 
                return str(section)
            elif (orientation == QtCore.Qt.Vertical): 
                return self.headerDataLookup[section]
        return None 
           
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)
                
    def setField(self, fieldname, index, value):
        setattr( self.scanSegmentList[index.column()], fieldname, value )
        self.dataChanged.emit( self.createIndex(0, index.column()), self.createIndex(5, index.column()) )
        self.updateSaveStatus()
        return True
    
    def setFieldText(self, fieldname, index, value):
        setattr( self.scanSegmentList[index.column()], fieldname, value )
        self.scanSegmentList[index.column()].evaluate(self.globalDict)
        self.dataChanged.emit( self.createIndex(0, index.column()), self.createIndex(5, index.column()) )
        self.updateSaveStatus()
        return True
    
    def setScanList(self, scanlist):
        self.beginResetModel()
        self.scanSegmentList = scanlist
        self.endResetModel()
                
    def update(self):
        self.dataChanged.emit( self.createIndex(0, 0), self.createIndex(5, self.columnCount()) )
