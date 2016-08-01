# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import PyQt5.uic

from dedicatedCounters.StatusTableModel import StatusTableModel
from modules.GuiAppearance import restoreGuiState, saveGuiState

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/TableViewWidget.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


class Settings:
    def __init__(self):
        self.average = False
        

class StatusDisplay(Form, Base ):
    def __init__(self, config, pulserConfiguration, parent=None):
        Form.__init__(self)
        Base.__init__(self, parent)
        self.config = config
        self.digitalStatus = 0
        self.statusBits = pulserConfiguration.statusBits if pulserConfiguration else None

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.model = StatusTableModel(self.statusBits)
        self.tableView.setModel( self.model )
        restoreGuiState( self, self.config.get("StatusDisplay") )
            
    def setData(self, data):
        if data.externalStatus is not None and self.digitalStatus !=data.externalStatus:
            self.digitalStatus = data.externalStatus
            self.model.setData( data.externalStatus ) 

    def saveConfig(self):
        self.config["StatusDisplay"] = saveGuiState(self)