# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtGui, QtWidgets


class MemoryProfiler(object):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.profilingMenu = mainWindow.menuBar.addMenu("Profiling")
        self.showGrowthAction = QtWidgets.QAction("Show growth", mainWindow)
        self.showGrowthAction.triggered.connect(self.onShowGrowth)
        self.profilingMenu.addAction(self.showGrowthAction)

    def onShowGrowth(self):
        import gc
        import objgraph
        gc.collect()
        logging.getLogger().info("Added objects since last run")
        objgraph.show_growth(limit=100)

        