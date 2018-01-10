# -*- coding: utf-8 -*-
"""
Simple example using BarGraphItem
"""
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from pyqtgraphAddons.GSTGraphItem import GSTGraphItem

win = pg.plot()
win.setWindowTitle('pyqtgraph example: GSTGraphItem')

x = [(0, 0, 0, 0), (1, 1, 0, 0), (2, 2, 0, 0), (0, 0, 1, 1), (0, 0, 2, 2), (1, 1, 2, 2)]
y = [0, 1, 2, 3, 4, 5]

#bg1 = GSTGraphItem(x=x, y=y)
#win.addItem(bg1)


# Final example shows how to handle mouse clicks:
class GSTGraph(GSTGraphItem):
    def mouseClickEvent(self, event):
        print("clicked")


bg = GSTGraph(x=x, y=y)
win.addItem(bg)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
