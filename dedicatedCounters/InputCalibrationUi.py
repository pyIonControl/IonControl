# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui, QtCore
import PyQt5.uic
from pyqtgraph.parametertree import Parameter, ParameterTree

from dedicatedCounters import AnalogInputCalibration

import os

from modules.AttributeComparisonEquality import AttributeComparisonEquality

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/InputCalibrationUi.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/InputCalibrationChannel.ui')
SheetForm, SheetBase = PyQt5.uic.loadUiType(uipath)


class Settings(AttributeComparisonEquality):
    def __init__(self):
        pass
    
class ChannelSettings(AttributeComparisonEquality):
    def __init__(self):
        self.calibration = "Voltage"
        self.parameters = dict()  #  map from calibration to settings
        
class InputCalibrationChannel(SheetForm, SheetBase):
    def __init__(self, config, channel, parent=None):
        SheetBase.__init__(self, parent)
        SheetForm.__init__(self)
        self.config = config
        self.channel = channel
        self.settings = self.config.get("InputCalibration.{0}".format(channel), ChannelSettings())
        self.myCalibration = None
        self.treeWidget = None
    
    def setupUi(self, callback, MainWindow):
        SheetForm.setupUi(self, MainWindow) 
        self.calibrationsCombo.addItems( list(AnalogInputCalibration.AnalogInputCalibrationMap.keys()) )   
        self.calibrationsCombo.currentIndexChanged["QString"].connect( self.onCalibrationChanged )
        self.callback = callback
        if self.settings.calibration:
            self.onCalibrationChanged(self.settings.calibration)
            self.calibrationsCombo.setCurrentIndex(self.calibrationsCombo.findText(self.settings.calibration))
      
    def onCalibrationChanged(self, calibration):  
        calibration = str(calibration)
        if self.myCalibration:
            self.settings.parameters[self.settings.calibration] = self.myCalibration.parameters
        self.myCalibration = AnalogInputCalibration.AnalogInputCalibrationMap[calibration]() 
        if calibration in self.settings.parameters:
            self.myCalibration.parameters = self.settings.parameters[calibration]
        if not self.treeWidget:
            try:
                self.param = Parameter.create(name='params', type='group', children=self.myCalibration.paramDef())
                self.treeWidget = ParameterTree()
                self.treeWidget.setParameters(self.param, showTop=False)
                self.verticalLayout.insertWidget(2, self.treeWidget)
                self.param.sigTreeStateChanged.connect(self.myCalibration.update, QtCore.Qt.UniqueConnection)
            except (TypeError, AttributeError):
                pass
        else:
            self.param = Parameter.create(name='params', type='group', children=self.myCalibration.paramDef())
            self.treeWidget.setParameters(self.param, showTop=False)
            try:
                self.param.sigTreeStateChanged.connect(self.myCalibration.update, QtCore.Qt.UniqueConnection )
            except TypeError:
                pass  # we want the connection to be unique
        self.settings.calibration = calibration
        self.callback( self.channel, self.myCalibration )
            
    def saveConfig(self):
        if self.myCalibration:
            self.settings.parameters[self.settings.calibration] = self.myCalibration.parameters
        self.config["InputCalibration.{0}".format(self.channel)] = self.settings
        

class InputCalibrationUi(Form, Base):
    def __init__(self, config, numChannels, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.config = config
        self.numChannels = numChannels
        self.settings = self.config.get("InputCalibration.Settings", Settings())
        self.calibrations = [None]*numChannels
        self.widgetList = list()
    
    def setupUi(self, MainWindow):
        Form.setupUi(self, MainWindow)
        self.channelSpinBox.setMaximum( self.numChannels-1 )
        for i in range(self.numChannels):
            ui = InputCalibrationChannel(self.config, i)
            ui.setupUi(self.updateCalibration, ui)
            self.stackedWidget.insertWidget(i, ui)
            self.calibrations[i] = ui.myCalibration
            self.widgetList.append(ui)
        self.stackedWidget.setCurrentIndex(0)

    def updateCalibration(self, channel, calibration):
        self.calibrations[channel] = calibration

    def saveConfig(self):
        self.config["InputCalibration.Settings"] = self.settings
        for widget in self.widgetList:
            widget.saveConfig()

if __name__=="__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = InputCalibrationUi(config, 4)
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
