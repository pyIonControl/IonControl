# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from PyQt5 import QtGui, QtCore
import PyQt5.uic

from externalParameter.ExternalParameterTableModel import ExternalParameterTableModel
from modules.SequenceDict import SequenceDict
from modules.Utility import unique
from uiModules.KeyboardFilter import KeyListFilter
from modules.PyqtUtility import updateComboBoxItems
import itertools
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from .InstrumentSettings import InstrumentSettings

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ExternalParameterSelection.ui')
SelectionForm, SelectionBase = PyQt5.uic.loadUiType(uipath)

class Parameter:
    def __init__(self):
        self.className = None
        self.name = None
        self.instrument = None
        self.settings = InstrumentSettings()
        self.enabled = False
        
    def __setstate__(self, state):
        self.__dict__ = state


class SelectionUi(SelectionForm, SelectionBase):
    outputChannelsChanged = QtCore.pyqtSignal(object)
    inputChannelsChanged = QtCore.pyqtSignal(object)
    
    def __init__(self, config, globalDict, classdict, instancename="ExternalParameterSelection.ParametersSequence", parent=None):
        SelectionBase.__init__(self, parent)
        SelectionForm.__init__(self)
        self.config = config
        self.instancename = instancename
        self.parameters = self.config.get(self.instancename, SequenceDict())
        self.enabledParametersObjects = SequenceDict()
        self.classdict = classdict
        self.globalDict = globalDict
    
    def setupUi(self, MainWindow):
        logger = logging.getLogger(__name__)
        SelectionForm.setupUi(self, MainWindow)
        self.parameterTableModel = ExternalParameterTableModel( self.parameters, self.classdict )
        self.parameterTableModel.enableChanged.connect( self.onEnableChanged )
        self.tableView.setModel( self.parameterTableModel )
        self.tableView.resizeColumnsToContents()
        self.comboBoxDelegate = ComboBoxDelegate()
        self.tableView.setItemDelegateForColumn(3, self.comboBoxDelegate)
        self.tableView.setItemDelegateForColumn(2, self.comboBoxDelegate)
        self.tableView.horizontalHeader().setStretchLastSection(True)   
        self.filter = KeyListFilter( [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown] )
        self.filter.keyPressed.connect( self.onReorder )
        self.tableView.installEventFilter(self.filter)
        self.classComboBox.addItems(sorted(self.classdict.keys()))
        self.classComboBox.currentIndexChanged[str].connect(self.getInstrumentSuggestions)
        self.addParameterButton.clicked.connect( self.onAddParameter )
        self.removeParameterButton.clicked.connect( self.onRemoveParameter )
        self.refreshInstrumentComboBox.clicked.connect(self.getInstrumentSuggestions)
        for parameter in list(self.parameters.values()):
            if parameter.enabled:
                try:
                    self.enableInstrument(parameter)
                except Exception as e:
                    logger.warning("{0} while enabling instrument {1}".format(e, parameter.name))
                    parameter.enabled = False     
        self.enabledParametersObjects.sortToMatch( list(self.parameters.keys()) ) 
        self.emitSelectionChanged()
        self.tableView.selectionModel().currentChanged.connect( self.onActiveInstrumentChanged )

    def outputChannels(self):
        self._outputChannels =  dict(itertools.chain(*[p.outputChannelList() for p in self.enabledParametersObjects.values()]))        
        return self._outputChannels
        
    def inputChannels(self):
        self._inputChannels =  dict(itertools.chain(*[p.inputChannelList() for p in self.enabledParametersObjects.values()]))        
        return self._inputChannels
        
    def emitSelectionChanged(self):
        self.outputChannelsChanged.emit( self.outputChannels() )
        self.inputChannelsChanged.emit( self.inputChannels() )

    def getInstrumentSuggestions(self, className=None):
        className = str(className) if className else self.classComboBox.currentText()
        myclass = self.classdict[className]
        if hasattr(myclass, 'connectedInstruments'):
            updateComboBoxItems(self.instrumentComboBox, sorted(myclass.connectedInstruments()))
            self.refreshInstrumentComboBox.setEnabled(True)
        else:
            self.instrumentComboBox.clear()
            self.refreshInstrumentComboBox.setEnabled(False)

    def onReorder(self, key):
        if key in [QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown]:
            indexes = self.tableView.selectedIndexes()
            up = key==QtCore.Qt.Key_PageUp
            delta = -1 if up else 1
            rows = sorted(unique([ i.row() for i in indexes ]), reverse=not up)
            if self.parameterTableModel.moveRow( rows, up=up ):
                selectionModel = self.tableView.selectionModel()
                selectionModel.clearSelection()
                for index in indexes:
                    selectionModel.select( self.parameterTableModel.createIndex(index.row()+delta, index.column()), QtCore.QItemSelectionModel.Select )
            self.enabledParametersObjects.sortToMatch( list(self.parameters.keys()) )               
            self.emitSelectionChanged()

    def onEnableChanged(self, name):
        logger = logging.getLogger(__name__)
        parameter = self.parameters[name]
        if parameter.enabled:
            try:
                self.enableInstrument(parameter)
            except Exception as e:
                logger.exception( "{0} while enabling instrument {1}".format(e, name))
                parameter.enabled = False                    
                self.parameterTableModel.setParameterDict( self.parameters )
        else:
            self.disableInstrument(name)
                      
    def onAddParameter(self):
        parameter = Parameter()
        parameter.instrument = str(self.instrumentComboBox.currentText())
        parameter.className = str(self.classComboBox.currentText())
        parameter.name = str(self.nameEdit.currentText())
        if parameter.name not in self.parameters:
            self.parameters[parameter.name] = parameter
            self.parameterTableModel.setParameterDict( self.parameters )
            self.tableView.resizeColumnsToContents()
            self.tableView.horizontalHeader().setStretchLastSection(True)        
        
    def onRemoveParameter(self):
        for index in sorted(unique([ i.row() for i in self.tableView.selectedIndexes() ]), reverse=True):
            parameter = self.parameters.at(index)
            parameter.enabled=False
            self.disableInstrument(parameter.name)
            self.parameters.pop( parameter.name )
        self.parameterTableModel.setParameterDict( self.parameters )
            
    def enableInstrument(self, parameter):
        if parameter.name not in self.enabledParametersObjects:
            logger = logging.getLogger(__name__)
            instance = self.classdict[parameter.className](parameter.name, parameter.settings, self.globalDict, parameter.instrument)
            self.enabledParametersObjects[parameter.name] = instance
            self.enabledParametersObjects.sortToMatch( list(self.parameters.keys()) )               
            self.emitSelectionChanged()
            self.parameterTableModel.setParameterDict( self.parameters )
            logger.info("Enabled Instrument {0} as {1}".format(parameter.className, parameter.name))
            
    def disableInstrument(self, name):
        if name in self.enabledParametersObjects:
            logger = logging.getLogger(__name__)
            instance = self.enabledParametersObjects.pop( name )
            instance.close()
            self.enabledParametersObjects.sortToMatch( list(self.parameters.keys()) )               
            self.emitSelectionChanged()
            parameter = self.parameters[name]
            logger.info("Disabled Instrument {0} as {1}".format(parameter.className, parameter.name))
        
    def onActiveInstrumentChanged(self, modelIndex, modelIndex2 ):
        logger = logging.getLogger(__name__)
        logger.debug( "activeInstrumentChanged {0}".format( modelIndex.row() ) )
        if self.parameters.at(modelIndex.row()).enabled:
            self.treeWidget.setParameters( self.enabledParametersObjects[self.parameters.at(modelIndex.row()).name].parameter )
        
    def saveConfig(self):
        self.config[self.instancename] = self.parameters
        
    def onClose(self):
        for inst in list(self.enabledParametersObjects.values()):
            inst.close()


if __name__ == "__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = SelectionUi(dict())
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())

