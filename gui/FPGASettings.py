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


class FPGASettings:
    def __init__(self):
        self.deviceSerial = None
        self.deviceDescription = None
        self.deviceInfo = None

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/FPGASettings.ui')
SettingsDialogForm, SettingsDialogBase = PyQt5.uic.loadUiType(uipath)
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/FPGASettingsList.ui')
ListForm, ListBase = PyQt5.uic.loadUiType(uipath)

class FPGASettingsDialogConfig:
    def __init__(self):
        self.autoUpload = False
        self.lastInstrument = None
        self.lastBitfile = None
        self.enabled = False

    def __setstate__(self, state):
        """this function ensures that the given fields are present in the class object"""
        self.__dict__ = state
        self.__dict__.setdefault( 'enabled', False )

class FPGASettingsWidget(SettingsDialogForm, SettingsDialogBase):
    def __init__(self, pulser, config, target, parent=0):
        SettingsDialogBase.__init__(self, parent)    
        SettingsDialogForm.__init__(self)
        self.config = config
        self.deviceMap = dict()
        self.deviceSerialMap = dict()
        self.settings = FPGASettings()
        self.pulser = pulser
        self.configName = 'SettingsDialog.{0}'.format(target)
        
    def setupUi(self):
        super(FPGASettingsWidget, self).setupUi(self)
        self.pushButtonScan.clicked.connect( self.scanInstruments )
        self.renameButton.clicked.connect( self.onBoardRename )
        self.uploadButton.clicked.connect( self.onUploadBitfile )
        self.toolButtonOpenBitfile.clicked.connect( self.onLoadBitfile )
        self.scanInstruments()
        self.configSettings = self.config.get(self.configName+'.Config', FPGASettingsDialogConfig() )
        self.bitfileCache = self.config.get(self.configName+'.bitfileCache', dict() )
        self.checkBoxAutoUpload.setChecked( self.configSettings.autoUpload )
        self.checkBoxAutoUpload.stateChanged.connect( partial(self.onStateChanged, 'autoUpload') )
        for item in self.bitfileCache:
            self.comboBoxBitfiles.addItem(item)
        if self.configSettings.lastBitfile:
            self.comboBoxBitfiles.setCurrentIndex( self.comboBoxBitfiles.findText(self.configSettings.lastBitfile))
        if self.configSettings.lastInstrument in self.deviceMap:
            index  = self.comboBoxInstruments.findText(self.configSettings.lastInstrument)
            self.comboBoxInstruments.setCurrentIndex( index )
            self.onIndexChanged(self.configSettings.lastInstrument)
        elif len(self.deviceMap)>0:
            self.comboBoxInstruments.setCurrentIndex(0)
            self.onIndexChanged(str(self.comboBoxInstruments.itemText(0)))
        self.comboBoxInstruments.currentIndexChanged[str].connect( self.onIndexChanged )
        self.enableCheckBox.setChecked( self.configSettings.enabled )
        self.enableCheckBox.stateChanged.connect( self.onEnableChanged )
        self.onEnableChanged( QtCore.Qt.Checked if self.configSettings.enabled else QtCore.Qt.Unchecked )
            
    def onEnableChanged(self, enable):
        enable = enable == QtCore.Qt.Checked
        self.comboBoxInstruments.setEnabled(enable)
        self.comboBoxBitfiles.setEnabled(enable)
        self.checkBoxAutoUpload.setEnabled(enable)
        self.toolButtonOpenBitfile.setEnabled(enable)
        self.pushButtonScan.setEnabled(enable)
        self.uploadButton.setEnabled(enable)
        self.configSettings.enabled = enable
            
    def showStatus(self, isopen):
        pass
            
    def resourcesAvailable(self):
        return (self.settings.deviceSerial in self.deviceSerialMap and 
                self.configSettings.lastBitfile is not None and os.path.exists(self.configSettings.lastBitfile) and 
                (self.configSettings.lastInstrument in self.deviceMap) and self.deviceMap[self.configSettings.lastInstrument].serial == self.settings.deviceSerial )            
            
    def initialize(self):
        if self.configSettings.enabled and self.resourcesAvailable():
            try:
                if self.configSettings.autoUpload:
                    self.onUploadBitfile()
                self.pulser.openBySerial(self.settings.deviceSerial)
                self.showStatus(True)
                return True
            except Exception as e:
                return False
        return not self.configSettings.enabled
    
    def accept(self):
        if self.configSettings.enabled:
            self.configSettings.lastInstrument = self.settings.deviceDescription
            return self.initialize()
        return True
    
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
        self.deviceSerialMap = dict( ( (dev.serial, dev) for dev in list(self.deviceMap.values())) )
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
        
    def saveConfig(self):
        self.config[self.configName+'.Config'] = self.configSettings
        self.config[self.configName+'.bitfileCache'] = self.bitfileCache
        
    def onLoadBitfile(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open bitfile', "", "bitfiles (*.bit)")
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
        self.configSettings.lastBitfile = bitfile
        if bitfile!="":
            if not os.path.exists(self.bitfileCache[bitfile]):
                raise IOError( "bitfile '{0}' not found".format(self.bitfileCache[bitfile]))
            self.pulser.openBySerial( self.settings.deviceSerial )
            self.pulser.uploadBitfile(self.bitfileCache[bitfile])
            self.configSettings.lastInstrument = self.settings.deviceDescription
            if hasattr( self.pulser, 'getConfiguration'):
                logger.info( "{0}".format( self.pulser.getConfiguration() ) )


class FPGASettingsDialog(ListForm, ListBase):
    def __init__(self, config, parent=0):
        ListBase.__init__(self, parent)    
        ListForm.__init__(self)
        self.config = config
        self.widgetDict = dict()
        self.showOnStartup = self.config.get('FPGASettingsDialog.showOnStartup', True)
        self.lastPos = self.config.get('FPGASettingsDialog.lastPos', None)
        
    def setupUi(self):
        super(FPGASettingsDialog, self).setupUi(self)
        
    def initialize(self):
        if not( all( ( widget.initialize() for widget in list(self.widgetDict.values()) ) ) ) or self.showOnStartup:
            self.exec_()

    def apply(self):
        for widget in list(self.widgetDict.values()):
            widget.initialize()
    
    def addEntry(self, target, pulser):
        newWidget = FPGASettingsWidget(pulser, self.config, target, self)
        newWidget.setupUi()
        self.widgetDict[target] = newWidget
        self.toolBox.addItem( newWidget, target )

    def accept(self):
        self.lastPos = self.pos()
        if all( ( widget.accept() for widget in list(self.widgetDict.values()) ) ):
            self.hide()
        
    def reject(self):
        self.lastPos = self.pos()
        self.hide()
        
    def show(self):
        if self.lastPos is not None:
            self.move(self.lastPos)
        QtWidgets.QDialog.show(self)
        
    def saveConfig(self):
        self.config['FPGASettingsDialog.showOnStartup'] = self.showOnStartup
        self.config['FPGASettingsDialog.lastPos'] = self.lastPos 
        for widget in list(self.widgetDict.values()):
            widget.saveConfig()
     
    def settings(self, target):
        return self.widgetDict[target].settings
            
if __name__ == "__main__":
    import sys
    class Recipient:
        def onSettingsApply(self):
            pass
        
    config = dict()
    recipient = Recipient()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = FPGASettingsDialog(config)
    ui.setupUi(recipient)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
