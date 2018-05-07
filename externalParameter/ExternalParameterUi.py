# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools
import logging

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic

from externalParameter.OutputChannel import OutputChannel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.firstNotNone import firstNotNone
from modules.Expression import Expression
from modules.GuiAppearance import restoreGuiState, saveGuiState
from uiModules.CategoryTree import CategoryTreeModel, CategoryTreeView, nodeTypes

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ExternalParameterUi.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class ExternalParameterControlModel(CategoryTreeModel):
    valueChanged = QtCore.pyqtSignal(str, object)
    expression = Expression()
    def __init__(self, controlUi, parameterList=[], parent=None):
        super(ExternalParameterControlModel, self).__init__(parameterList, parent, nodeNameAttr='displayName')
        self.parameterList=parameterList
        self.controlUi = controlUi
        for parameter in parameterList:
            parameter.categories = parameter.device.name
        self.headerLookup.update({
            (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, 0): 'Name',
            (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, 1): 'Control',
            (QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole, 2): 'External'
            })
        self.dataLookup.update({
            (QtCore.Qt.DisplayRole, 0): lambda node: node.content.displayName,
            (QtCore.Qt.DisplayRole, 1): lambda node: str(node.content.targetValue),
            (QtCore.Qt.EditRole, 1): lambda node: firstNotNone( node.content.string, str(node.content.targetValue) ),
            (QtCore.Qt.UserRole, 1): lambda node: node.content.dimension,
            (QtCore.Qt.DisplayRole, 2): lambda node: str(node.content.externalValue),
            (QtCore.Qt.BackgroundRole, 1): self.dependencyBgFunction,
            (QtCore.Qt.ToolTipRole, 1): self.toolTipFunction
            })
        self.setDataLookup.update({
            (QtCore.Qt.EditRole, 1): lambda index, value: self.setValue(index, value),
            (QtCore.Qt.UserRole, 1): lambda index, value: self.setStrValue(index, value),
            })
        self.flagsLookup = {
            1:QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        }
        self.numColumns = 3
        self.allowReordering = True
        self.signalConnections = list()

    def setParameterList(self, outputChannelDict):
        self.beginResetModel()
        self.parameterList = list(outputChannelDict.values())
        # first disconnect all old signals, they may point to the wrong index
        for inst, valueSlot, targetValueSlot in self.signalConnections:
            inst.valueChanged.disconnect(valueSlot)
            inst.targetChanged.disconnect(targetValueSlot)
        del self.signalConnections[:]   # clear the list
        # now we can add new connections
        for listIndex, inst in enumerate(self.parameterList):
            inst.multipleChannels = len(inst.device._outputChannels)>1
            inst.categories = inst.device.name if inst.multipleChannels else None
            inst.displayName = inst.channelName if inst.multipleChannels else inst.device.name
            inst.toolTip = None
            valueSlot = functools.partial(self.showValue, listIndex)
            targetValueSlot = functools.partial(self.onTargetChanged, listIndex)
            inst.valueChanged.connect(valueSlot)
            inst.targetChanged.connect(targetValueSlot)
            self.signalConnections.append((inst, valueSlot, targetValueSlot))
        self.clear()
        self.endResetModel()
        self.addNodeList(self.parameterList)

    def showValue(self, listIndex, value, tooltip=None):
        inst=self.parameterList[listIndex]
        inst.toolTip = tooltip
        id=inst.name if inst.multipleChannels else inst.device.name
        node = self.nodeDict[id]
        modelIndex=self.indexFromNode(node, 2)
        self.dataChanged.emit(modelIndex, modelIndex)

    def onTargetChanged(self, listIndex, value):
        inst=self.parameterList[listIndex]
        id = inst.name if inst.multipleChannels else inst.device.name
        node = self.nodeDict[id]
        modelIndex = self.indexFromNode(node, 1)
        self.dataChanged.emit(modelIndex, modelIndex)
            
    def setValue(self, index, value):
        node=self.nodeFromIndex(index)
        self._setValue(node.content, value)

    def _setValue(self, inst, value):
        logger = logging.getLogger(__name__)
        logger.debug( "setValue {0}".format(value))
        inst.targetValue = value
        self.setValueFollowup(inst)
        return True
 
    def setStrValue(self, index, strValue):
        node=self.nodeFromIndex(index)
        node.content.string = strValue
        return True
        
    def setValueFollowup(self, inst):
        try:
            logger = logging.getLogger(__name__)
            logger.debug( "setValueFollowup {0}".format( inst.value ) )
            if not inst.setValue(inst.targetValue):
                delay = int( inst.settings.delay.m_as('ms') )
                QtCore.QTimer.singleShot(delay, functools.partial(self.setValueFollowup, inst))
        except Exception as e:
            logger.exception(e)
            logger.warning( "Exception during setValueFollowup, number of adjusting devices likely to be faulty")

    def update(self, iterable):
        for destination, name, value in iterable:
            if destination=='External':
                for inst in self.parameterList:
                    if inst.name==name:
                        break
                inst.savedValue = value    # set saved value to make this new value the default
                node = self.nodeFromContent(inst)
                self.setValue(self.indexFromNode(node, 1), value)
                inst.strValue = None
                logging.info("Pushed to external parameter {0} value {1}".format(name, value)) 
                
    def evaluate(self, name):
        for inst in self.parameterList:
            if (name is None or inst.name == name) and inst.hasDependency:
                value = self.expression.evaluateAsMagnitude(inst.string, self.controlUi.globalDict)
                self._setValue(inst, value)
                inst.savedValue = value   # set saved value to make this new value the default
                node = self.nodeFromContent(inst)
                index = self.indexFromNode(node, 1)
                self.dataChanged.emit(index, index)

class ControlUi(Form, Base):
    def __init__(self, config, globalDict=None, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.globalDict = firstNotNone( globalDict, dict() )
        self.config = config
        self.configName = 'ControlUi'
    
    def setupUi(self, outputChannels):
        Form.setupUi(self, self)
        self.categoryTreeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        model = ExternalParameterControlModel(self)
        self.categoryTreeView.setModel(model)
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.categoryTreeView.setItemDelegateForColumn(1, self.delegate)
        self.setupParameters(outputChannels)
        restoreGuiState(self, self.config.get(self.configName+'.guiState'))
        try:
            self.categoryTreeView.restoreTreeMarkup(self.config.get(self.configName+'.treeMarkup', None))
            self.categoryTreeView.restoreTreeColumnWidth(self.config.get(self.configName + '.treeColumnWidth', None))
        except Exception as e:
            logging.getLogger(__name__).error("unable to restore tree state in {0}: {1}".format(self.configName, e))
        self.categoryTreeView.selectionModel().currentChanged.connect( self.onActiveChannelChanged )

    def setupParameters(self, outputChannels):
        oldState=self.categoryTreeView.treeState()
        oldNodeDictKeys=list(self.categoryTreeView.model().nodeDict.keys())
        self.categoryTreeView.model().setParameterList(outputChannels)
        self.categoryTreeView.header().setStretchLastSection(True)
        self.categoryTreeView.restoreTreeState(oldState)
        for key, node in self.categoryTreeView.model().nodeDict.items():
            if key not in oldNodeDictKeys: #Expand any new nodes
                index = self.categoryTreeView.model().indexFromNode(node)
                self.categoryTreeView.expand(index)
                try:
                    self.evaluate(key)
                except (KeyError, ValueError) as e:
                    logging.getLogger(__name__).warning(str(e))
        
    def keys(self):
        pList = self.categoryTreeView.model().parameterList
        return [p.name for p in pList]
    
    def update(self, iterable):
        self.categoryTreeView.model().update(iterable)
        self.categoryTreeView.viewport().repaint()
        
    def evaluate(self, name):
        self.categoryTreeView.model().evaluate(name)
        
    def callWhenDoneAdjusting(self, callback):
        OutputChannel.useTracker.callWhenDoneAdjusting(callback)

    def saveConfig(self):
        self.config[self.configName+'.guiState'] = saveGuiState(self)
        try:
            self.config[self.configName+'.treeMarkup'] = self.categoryTreeView.treeMarkup()
            self.config[self.configName+'.treeColumnWidth'] = self.categoryTreeView.treeColumnWidth()
        except Exception as e:
            logging.getLogger(__name__).error("unable to save tree state in {0}: {1}".format(self.configName, e))

    def onActiveChannelChanged(self, modelIndex, modelIndex2 ):
        model = self.categoryTreeView.model()
        node = model.nodeFromIndex(modelIndex)
        if node.nodeType==nodeTypes.data:
            index = model.parameterList.index(node.content)
            outchannel = model.parameterList[index]
            self.treeWidget.setParameters( outchannel.parameter )

