# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtWidgets


class MainWindowWidget(QtWidgets.QMainWindow):

    def __init__(self, toolBar=None, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.dockWidgetList = list()
        self.actionList = list()
        self.toolBar = toolBar
        
    def activate(self):
        for widget in self.dockWidgetList:
            if widget.isFloating():
                if hasattr(widget, 'wasVisible'):
                    widget.setVisible(widget.wasVisible)
        if self.toolBar:
            for action in self.actionList:
                self.toolBar.addAction(action)
        
    def deactivate(self):
        for widget in self.dockWidgetList:
            if widget.isFloating():
                widget.wasVisible = widget.isVisible()
                widget.setVisible(False)
        if self.toolBar:
            self.toolBar.clear()
        
    def onClose(self):
        pass

    def viewActions(self):
        return [ widget.toggleViewAction() for widget in self.dockWidgetList ]
    
    def printTargets(self):
        return [] 
