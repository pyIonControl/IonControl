# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui
import PyQt5.uic

from modules.RunningStat import RunningStat
from modules.round import roundToStdDev, roundToNDigits

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/AverageViewUi.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


class AverageView(Form, Base ):
    def __init__(self,config,parentname,parent=None,zero=0):
        Form.__init__(self)
        Base.__init__(self, parent)
        self.config = config
        self.configname = 'AverageView.'+parentname
        self.stat = RunningStat(zero)

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        # History and Dictionary
        self.clearButton.clicked.connect( self.onClear )
        self.update()
    
    def update(self):
        """"update the output
        """
        self.countLabel.setText( str(self.stat.count) )
        mean, stderr = self.stat.mean, self.stat.stderr
        self.averageLabel.setText( str(roundToStdDev(mean, stderr)) )
        self.stddevLabel.setText( str(roundToNDigits(stderr, 2)) )
    
    def onClear(self):
        self.stat.clear()
        self.update()
        
    def add(self, value):
        """add value to the mean and stddev or stderr
        """
        self.stat.add(value)
        self.update()
        
        

if __name__=="__main__":
    
    import sys
    import random
    from PyQt5 import QtWidgets

    def add():
        ui.add( random.gauss(50, 5) )
    
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = AverageView(config, "parent")
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    timer = QtCore.QTimer()
    timer.timeout.connect( add )
    timer.start(100)
    sys.exit(app.exec_())
