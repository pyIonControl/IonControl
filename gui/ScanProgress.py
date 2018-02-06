# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from datetime import timedelta
import time

from PyQt5 import QtCore, QtGui
import PyQt5.uic

from modules.enum import enum
from modules.firstNotNone import firstNotNone

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ScanProgress.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class ScanProgress(Form, Base):
    OpStates = enum('idle', 'running', 'paused', 'starting', 'stopping', 'interrupted', 'stashing', 'resuming')
    stateChanged = QtCore.pyqtSignal( str )#object )
    def __init__(self):
        Form.__init__(self)
        Base.__init__(self)
        self.state = self.OpStates.idle
        self.range = 1
        self.startTime = time.time()     # time of last start
        self.previouslyElapsedTime = 0      # time spent on run before last start 
        self.expected = 0
        self.timer = None
        self.lastPercentage = 0
        self.lastTime = 0
        self.repeats = 1

    def getData(self):
        return (self.startTime, self.previouslyElapsedTime)

    def setData(self, data):
        self.startTime, self.previouslyElapsedTime = data
    
    def setupUi(self):
        super(ScanProgress, self).setupUi(self)
        self.statusLabel.setText("Idle")
        self.progressBar.setFormat("%p%")
        self.scanLabel.setText("")
        self.evaluationLabel.setText("")
        self.analysisLabel.setText("")

    def __getattr__(self, name):
        """generates the is_idle, is_running, ... attributes"""
        if name[0:3] == 'is_':
            desiredState = self.OpStates.mapping.get(name[3:])
            if desiredState is None:
                raise AttributeError("{0} is not a valid state of ScanProgress")
            return self.state == desiredState
        raise AttributeError()

    def setScanLabel(self, scanName):        
        self.scanLabel.setText( firstNotNone(scanName, "") )
        
    def setEvaluationLabel(self, scanName):        
        self.evaluationLabel.setText(firstNotNone(scanName, ""))
        
    def setAnalysisLabel(self, scanName):        
        self.analysisLabel.setText(firstNotNone(scanName, ""))
        
    def startTimer(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect( self.setTimeLabel )
        self.timer.start(1000)
        
    def stopTimer(self):
        if self.timer:
            self.timer = None
            
    def setIdle(self):
        self.statusLabel.setText("Idle")    
        self.progressBar.setValue(0)
        self.state = self.OpStates.idle
        self.stateChanged.emit('idle')
        self.previouslyElapsedTime = time.time()-self.startTime
        self.widget.setStyleSheet( "QWidget { background: #ffffff; }")
    
    def setRunning(self, total, repeats=1):
        self.statusLabel.setText("Running")    
        self.range = total
        self.progressBar.setRange(0, total)
        self.progressBar.setValue(0)
        #self.progressBar.setStyleSheet("")
        self.setTimeLabel()
        self.state = self.OpStates.running
        self.stateChanged.emit('running')
        self.startTime = time.time()
        self.previouslyElapsedTime = 0
        self.widget.setStyleSheet( "QWidget { background: #a0ffa0; }")
        self.startTimer()
        self.previouslyElapsedTime = 0
        self.repeats = repeats
        
    def resumeRunning(self, index):
        self.statusLabel.setText("Running")    
        self.progressBar.setValue(index)
        self.startTime = time.time()
        self.state = self.OpStates.running
        self.stateChanged.emit('running')
        self.widget.setStyleSheet( "QWidget { background: #a0ffa0; }")
        self.startTimer()
    
    def setPaused(self):
        #self.progressBar.setStyleSheet(StyleSheets.RedProgressBar)
        self.statusLabel.setText("Paused")            
        self.setTimeLabel()
        self.state = self.OpStates.paused
        self.stateChanged.emit('paused')
        self.previouslyElapsedTime += time.time()-self.startTime
        self.widget.setStyleSheet( "QWidget { background: #c0c0ff; }")
        self.stopTimer()
    
    def setStarting(self):
        self.statusLabel.setText("Starting") 
        self.state = self.OpStates.starting
        self.stateChanged.emit('starting')

    def setStopping(self):
        self.statusLabel.setText("Stopping")    
        self.state = self.OpStates.stopping
        self.stateChanged.emit('stopping')

    def setStashing(self):
        self.statusLabel.setText("Stashing")
        self.state = self.OpStates.stashing
        self.stateChanged.emit('stashing')

    def setInterrupted(self, reason):
        #self.progressBar.setStyleSheet(StyleSheets.RedProgressBar)
        self.previouslyElapsedTime = time.time()-self.startTime
        self.statusLabel.setText("Interrupted ({0})".format(reason))            
        self.state = self.OpStates.interrupted
        self.stateChanged.emit('interrupted')
        self.setTimeLabel()
        self.previouslyElapsedTime += time.time()-self.startTime
        self.widget.setStyleSheet( "QWidget { background: #ffa0a0; }")
        self.stopTimer()

    def onData(self, index):
        percentage = round(100 * (index / self.range))
        self.expected = self.elapsedTime() / (index / float(self.range)) if index > 0 else 0
        if self.repeats > 1 and self.state == self.OpStates.running:
            current_repeat = int(index * self.repeats / self.range) + 1
            self.statusLabel.setText("Running ({})".format(current_repeat))
        if (percentage != self.lastPercentage and time.time() - self.lastTime > 4) or index + 1 >= self.range:
            self.lastPercentage = percentage
            self.progressBar.setValue(index)
            self.lastTime = time.time()
            self.setTimeLabel()

    def elapsedTime(self):
        return self.previouslyElapsedTime + (
        (time.time() - self.startTime) if self.state == self.OpStates.running else 0)

    def setTimeLabel(self):
        self.timeLabel.setText("{0} / {1}".format(timedelta(seconds=round(self.elapsedTime())),
                                                  timedelta(seconds=round(self.expected))))



if __name__=="__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = ScanProgress()
    ui.setupUi()
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
