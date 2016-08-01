# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtGui, QtWidgets
from uiModules.TableViewExtended import TableViewExtended

def saveColumnWidth( tableView ):
    return [tableView.columnWidth(i) for i in range(0, tableView.model().columnCount())]

def restoreColumnWidth( tableView, widthData, autoscaleOnNone=True ):
    if widthData and len(widthData)==tableView.model().columnCount():
        for column, width in zip( list(range(0, tableView.model().columnCount())), widthData ):
            tableView.setColumnWidth(column, width)
    else:
        tableView.resizeColumnsToContents()
     
     

appearanceHelpers = { QtWidgets.QSplitter: (QtWidgets.QSplitter.saveState, QtWidgets.QSplitter.restoreState),
                      TableViewExtended: (saveColumnWidth, restoreColumnWidth),
                      QtWidgets.QTableView: (saveColumnWidth, restoreColumnWidth)}

ClassAttributeCache = dict()
     
def saveGuiState( obj ):
    data = dict()
    if obj.__class__ in ClassAttributeCache:
        for name in ClassAttributeCache[obj.__class__]:
            attr = getattr(obj, name)
            data[name] = appearanceHelpers[attr.__class__][0](attr)            
    else:
        attrlist = list()
        for name, attr in obj.__dict__.items():
            if hasattr(attr, '__class__') and attr.__class__ in appearanceHelpers:
                data[name] = appearanceHelpers[attr.__class__][0](attr)
                attrlist.append(name)
        ClassAttributeCache[obj.__class__] = attrlist
    return data
            
def restoreGuiState( obj, data ):
    if data:
        for name, value in data.items():
            if hasattr( obj, name):
                attr = getattr( obj, name)
                if hasattr(attr, '__class__') and attr.__class__ in appearanceHelpers:
                    appearanceHelpers[attr.__class__][1](attr, value)
    
