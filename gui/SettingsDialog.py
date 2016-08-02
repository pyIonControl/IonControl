# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from functools import partial
import logging
import os

from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic


class Settings:
    def __init__(self):
        self.deviceSerial = None
        self.deviceDescription = None
        self.pulser = None
        self.bitfile = None

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/SettingsDialog.ui')
SettingsDialogForm, SettingsDialogBase = PyQt5.uic.loadUiType(uipath)

class SettingsDialogConfig:
    def __init__(self):
        self.autoUpload = False
        self.lastInstrument = None
        self.lastBitfile = None
        self.showOnStartup = True
        
    def __setstate__(self, state):
        """this function ensures that the given fields are present in the class object"""
        self.__dict__ = state

class SettingsDialog(SettingsDialogForm, SettingsDialogBase):
    def __init__(self,pulser,config,parent=0):
        SettingsDialogBase.__init__(self, parent)    
        SettingsDialogForm.__init__(self)
        self.config = config
        self.deviceMap = dict()
        self.settings = Settings()
        self.pulser = pulser
        
    def setupUi(self):
        super(SettingsDialog, self).setupUi(self)
        self.pushButtonScan.clicked.connect( self.scanInstruments )
        self.renameButton.clicked.connect( self.onBoardRename )
        self.uploadButton.clicked.connect( self.onUploadBitfile )
        self.toolButtonOpenBitfile.clicked.connect( self.onLoadBitfile )
        self.comboBoxInstruments.currentIndexChanged[str].connect( self.onIndexChanged )
        self.scanInstruments()
        self.configSettings = self.config.get('SettingsDialog.Config', SettingsDialogConfig() )
        self.bitfileCache = self.config.get('SettingsDialog.bitfileCache', dict() )
        self.checkBoxAutoUpload.setChecked( self.configSettings.autoUpload )
        self.checkBoxAutoUpload.stateChanged.connect( partial(self.onStateChanged, 'autoUpload') )
        self.showOnStartupCheckBox.setChecked( self.configSettings.showOnStartup )
        self.showOnStartupCheckBox.stateChanged.connect( partial(self.onStateChanged, 'showOnStartup') )
        for item in self.bitfileCache:
            self.comboBoxBitfiles.addItem(item)
        if self.configSettings.lastBitfile:
            self.comboBoxBitfiles.setCurrentIndex( self.comboBoxBitfiles.findText(self.configSettings.lastBitfile))
        if self.configSettings.lastInstrument in self.deviceMap:
            self.comboBoxInstruments.setCurrentIndex( self.comboBoxInstruments.findText(self.configSettings.lastInstrument) )
            if not self.configSettings.showOnStartup:
                try:
                    if self.configSettings.autoUpload and self.configSettings.lastBitfile is not None:
                        self.onUploadBitfile()
                    else:
                        self.pulser.openBySerial(self.deviceMap[ self.configSettings.lastInstrument].serial )
                except IOError as e:
                    logging.getLogger(__name__).warning( e.strerror )
                    self.exec_()
            else:
                self.exec_()
        else:
            self.exec_()
                
    def onStateChanged(self, attribute, state):
        setattr( self.configSettings, attribute, state==QtCore.Qt.Checked )
        
    def onBoardRename(self):
        newIdentifier = str(self.identifierEdit.text())
        self.pulser.renameBoard(self.settings.deviceSerial, newIdentifier )
        self.scanInstruments()
        self.comboBoxInstruments.setCurrentIndex( self.comboBoxInstruments.findText(newIdentifier) )
        
    def scanInstruments(self):
        logger = logging.getLogger(__name__)
        self.comboBoxInstruments.clear()
        self.deviceMap = self.pulser.listBoards()
        self.comboBoxInstruments.addItems( list(self.deviceMap.keys()) )
        logger.info( "Opal Kelly Devices found {0}".format(self.deviceMap ) )
        
    def onIndexChanged(self, description):
        logger = logging.getLogger(__name__)
        if description!='':
            logger.info( "instrument '{0}' {1} {2}".format(description, self.deviceMap[str(description)].modelName, self.deviceMap[str(description)].serial) )
            self.settings.deviceSerial = self.deviceMap[str(description)].serial
            self.settings.deviceDescription = str(description)
            self.settings.deviceInfo = self.deviceMap[str(description)]
            self.identifierEdit.setText( description )
        
    def accept(self):
        self.lastPos = self.pos()
        if self.settings.deviceSerial not in [None, '', 0]:
            if self.configSettings.autoUpload:
                self.onUploadBitfile()
            else:
                self.pulser.openBySerial(self.settings.deviceSerial)
            self.settings.pulser = self.pulser
            self.settings.bitfile = str(self.comboBoxBitfiles.currentText())
        self.hide()
        
    def reject(self):
        self.lastPos = self.pos()
        self.hide()
        
    def show(self):
        if hasattr(self, 'lastPos'):
            self.move(self.lastPos)
        QtWidgets.QDialog.show(self)
        
    def apply(self, button):
        if str(button.text())=="Apply":
            self.pulser.openBySerial( self.settings.deviceSerial )   
            
    def saveConfig(self):
        self.config['SettingsDialog.Config'] = self.configSettings
        self.config['SettingsDialog.bitfileCache'] = self.bitfileCache
        
    def onLoadBitfile(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open bitfile')
        if path!="":
            if path not in self.bitfileCache:
                self.bitfileCache[path]=path
                self.comboBoxBitfiles.addItem(path)
            self.comboBoxBitfiles.setCurrentIndex(self.comboBoxBitfiles.findText(path))
            self.configSettings.lastBitfile = path
            
    def onUploadBitfile(self):
        logger = logging.getLogger(__name__)
        bitfile = str(self.comboBoxBitfiles.currentText())
        logger.info( "Uploading file '{0}'".format(bitfile) )
        if bitfile!="":
            if not os.path.exists(self.bitfileCache[bitfile]):
                raise IOError( "bitfile '{0}' not found".format(self.bitfileCache[bitfile]))
            self.pulser.openBySerial( self.settings.deviceSerial )
            self.pulser.uploadBitfile(self.bitfileCache[bitfile])
            self.configSettings.lastInstrument = self.settings.deviceDescription
            if hasattr(self.pulser, "getConfiguration") and False:
                logging.getLogger(__name__).info( "{0}".format( self.pulser.getConfiguration() ) )

            
if __name__ == "__main__":
    import sys
    class Recipient:
        def onSettingsApply(self):
            pass
        
    config = dict()
    recipient = Recipient()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = SettingsDialog(config)
    ui.setupUi(recipient)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
