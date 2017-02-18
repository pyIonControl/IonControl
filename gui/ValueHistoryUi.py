# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import PyQt5.uic
from PyQt5 import QtCore, QtWidgets
from functools import partial

from modules.AttributeComparisonEquality import AttributeComparisonEquality
from persist.ValueHistory import ValueHistoryStore
from modules.PyqtUtility import updateComboBoxItems
from datetime import datetime
from collections import defaultdict
import logging
from uiModules.GenericTableModel import GenericTableModel
from modules.GuiAppearance import restoreGuiState, saveGuiState   #@UnresolvedImport
from modules.quantity import Q
from modules.NamedTimespan import getRelativeDatetime, timespans
from dateutil.tz import tzlocal

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ValueHistory.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


class Parameters(AttributeComparisonEquality):
    def __init__(self):
        self.space = None
        self.parameter = None
        self.fromTime = datetime(2014, 1, 1)
        self.spaceParamCache = dict()

class ValueHistoryUi(Form, Base):
    def __init__(self, config, dbConnection, parent=None, globaldict=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.config = config
        self.globalDict = globaldict
        self.parameters = self.config.get("ValueHistory.parameters", Parameters())
        self.dbConnection = dbConnection
        self.connection = ValueHistoryStore(dbConnection)
        self.connection.open_session()
        self.cache = dict()
        self.currentSpace = None
        self.currentGlobal = None
    
    def setupUi(self, MainWindow):
        Form.setupUi(self, MainWindow)
        self.comboBoxSpace.currentIndexChanged[str].connect( self.onSpaceChanged  )
        self.comboBoxParam.currentIndexChanged[str].connect( partial(self.onValueChangedString, 'parameter') )
        self.loadButton.clicked.connect( self.onLoad )       
        self.namedTimespanComboBox.addItems( ['Select timespan ...']+timespans )
        self.namedTimespanComboBox.currentIndexChanged[str].connect( self.onNamedTimespan )
        self.onRefresh()
        if self.parameters.space is not None:
            self.comboBoxSpace.setCurrentIndex( self.comboBoxSpace.findText(self.parameters.space ))
        if self.parameters.parameter is not None:
            self.comboBoxParam.setCurrentIndex( self.comboBoxParam.findText(self.parameters.parameter ))
        if self.parameters.fromTime is not None:
            self.dateTimeEditFrom.setDateTime( self.parameters.fromTime )
        self.dateTimeEditFrom.dateTimeChanged.connect( partial(self.onValueChangedDateTime, 'fromTime')  )
        self.toolButtonRefresh.clicked.connect( self.onRefresh )
        self.onSpaceChanged(self.parameters.space)
        self.dataModel = GenericTableModel(self.config, list(), "ValueHistory", ["Date", "Value"], [lambda t: t.astimezone(tzlocal()).strftime('%Y-%m-%d %H:%M:%S'), str])
        self.tableView.setModel( self.dataModel )
        self.tableView.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        self.copyAction = QtWidgets.QAction("Copy to clipboard", self)
        self.copyAction.triggered.connect(self.copyToClipboard)
        self.pushAction = QtWidgets.QAction("Push to global", self)
        self.pushAction.triggered.connect(self.pushToGlobal)
        self.tableView.addAction(self.copyAction)
        self.tableView.addAction(self.pushAction)
        restoreGuiState( self, self.config.get('ValueHistory.guiState'))
        
    def onNamedTimespan(self, name):
        dt = getRelativeDatetime(str(name), None)
        if dt is not None:
            self.parameters.fromTime = dt
            self.dateTimeEditFrom.setDateTime( self.parameters.fromTime )
            self.namedTimespanComboBox.setCurrentIndex(0)

    def onValueChangedString(self, param, value):
        setattr( self.parameters, param, str(value) )

    def onValueChangedDateTime(self, param, value):
        setattr( self.parameters, param, value.toPyDateTime() )

    def saveConfig(self):
        self.config["ValueHistory.parameters"] = self.parameters
        self.config['ValueHistory.guiState'] = saveGuiState( self )
        
    def onRefresh(self):
        self.parameterNames = defaultdict( list )
        for (space, source) in list(self.connection.refreshSourceDict().keys()):
            self.parameterNames[space].append(source)
        updateComboBoxItems( self.comboBoxSpace, sorted(self.parameterNames.keys()) )
        updateComboBoxItems( self.comboBoxParam, sorted(self.parameterNames[self.parameters.space]) )
        
    def onSpaceChanged(self, newSpace):
        newSpace = str(newSpace)
        if self.parameters.space is not None and self.parameters.parameter is not None:
            self.parameters.spaceParamCache[self.parameters.space] = self.parameters.parameter
        self.parameters.space = newSpace
        self.parameters.parameter = self.parameters.spaceParamCache.get( self.parameters.space, self.parameterNames[self.parameters.space][0] if len(self.parameterNames[self.parameters.space])>0 else None )
        updateComboBoxItems( self.comboBoxParam, sorted(self.parameterNames[self.parameters.space]) )
        if self.parameters.parameter is not None:
            self.comboBoxParam.setCurrentIndex( self.comboBoxParam.findText(self.parameters.parameter ))
               
    def onLoad(self):
        self.doLoad( self.parameters.space, self.parameters.parameter, self.parameters.fromTime )

    def doLoad(self, space, parameter, fromTime ):
        result = self.connection.getHistory( space, parameter, fromTime, datetime.now() )
        if not result:
            logging.getLogger(__name__).warning("Database query returned empty set")
        elif len(result)>0:
            self.data = [(e.upd_date, Q(e.value, e.unit)) for e in reversed(result)]
            self.dataModel.setDataTable(self.data)
            self.currentSpace = space
            self.currentGlobal = parameter
            self.pushAction.setText("Push to {0}".format(self.currentGlobal))

    def pushToGlobal(self):
        index = self.tableView.selectedIndexes()[0]
        if self.currentSpace == 'globalVar' and self.currentGlobal is not None:
            self.globalDict[self.currentGlobal] = self.dataModel.data[index.row()][1]

    def copyToClipboard(self):
        """ Copy value to clipboard as a string. """
        clip = QtWidgets.QApplication.clipboard()
        index = self.tableView.selectedIndexes()[0]
        if self.currentSpace == 'globalVar' and self.currentGlobal is not None:
            clip.setText(str(self.dataModel.data[index.row()][1]))

