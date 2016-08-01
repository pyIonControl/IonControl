# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


import operator

from PyQt5 import QtGui, QtCore, QtWidgets


class TableViewExtended(QtWidgets.QTableView):
    """ Adds Ctrl+C copy functionality to table view"""
    def keyReleaseEvent(self, e):
        if e.key()==QtCore.Qt.Key_C and e.modifiers()&QtCore.Qt.ControlModifier:
            indexes = sorted([(i.row(), i.column()) for i in self.selectedIndexes()])
            indexesbycolumn = sorted(indexes, key=operator.itemgetter(1))
            model = self.model()
            tabledata = list()
            for row in range( indexes[0][0], indexes[-1][0]+1):
                tabledata.append("\t".join([ c if c is not None else '' for c in 
                                                (str(model.data( model.index(row, column), QtCore.Qt.DisplayRole )) for column in  
                                                         range( indexesbycolumn[0][1], indexesbycolumn[-1][1]+1))]))
            QtWidgets.QApplication.clipboard().setText("\n".join(tabledata))
        else:
            QtWidgets.QTableView.keyReleaseEvent(self, e)