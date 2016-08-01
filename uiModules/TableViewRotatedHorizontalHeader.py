# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtGui, QtCore, QtWidgets

from uiModules.RotatedHeaderView import RotatedHeaderView


class TableViewRotatedHorizontalHeader(QtWidgets.QTableView):
    '''
    TableView with rotated Horizontal Header
    '''


    def __init__(self, parent=None ):
        super(TableViewRotatedHorizontalHeader, self).__init__(parent)
        self.setHorizontalHeader( RotatedHeaderView( QtCore.Qt.Horizontal, self) )
        