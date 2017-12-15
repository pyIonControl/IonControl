# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import functools
import logging

from PyQt5 import QtCore
import PyQt5.uic

from voltageControl.ShuttleEdgeTableModel import ShuttleEdgeTableModel
from voltageControl.ShuttlingDefinition import ShuttlingGraph, ShuttleEdge
from modules.PyqtUtility import updateComboBoxItems, BlockSignals
from modules.firstNotNone import firstNotNone
from modules.Utility import unique
from modules.GuiAppearance import restoreGuiState, saveGuiState
import lxml.etree as ElementTree
import os.path
from modules.Expression import Expression
from gui.ExpressionValue import ExpressionValue
from modules.quantity import Q
import re
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from modules.DataChanged import DataChangedS

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/VoltageAdjust.ui')
VoltageAdjustForm, VoltageAdjustBase = PyQt5.uic.loadUiType(uipath)
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ShuttlingEdge.ui')
ShuttlingEdgeForm, ShuttlingEdgeBase = PyQt5.uic.loadUiType(uipath)

    
class Adjust(object):
    expression = Expression()
    dataChangedObject = DataChangedS()
    dataChanged = dataChangedObject.dataChanged

    def __init__(self, globalDict=dict()):
        self._globalDict = globalDict
        self._line = ExpressionValue(name="line", globalDict=globalDict, value=Q(0.0))
        self._lineValue = self._line.value
        self._lineGain = ExpressionValue( name="lineGain", globalDict=globalDict, value=Q(1.0) )
        self._globalGain = ExpressionValue( name="globalGain", globalDict=globalDict, value=Q(1.0) )
        self._line.valueChanged.connect(self.onLineExpressionChanged)
        self._lineGain.valueChanged.connect(self.onLineExpressionChanged)
        self._globalGain.valueChanged.connect(self.onLineExpressionChanged)

    @property
    def globalDict(self):
        return self._globalDict
    
    @globalDict.setter
    def globalDict(self, globalDict):
        self._globalDict = globalDict
        self._lineGain.globalDict = globalDict
        self._globalGain.globalDict = globalDict
        self._line.globalDict = globalDict
        
    @property
    def line(self):
        return self._lineValue
    
    @line.setter
    def line(self, value):
        self._lineValue = value
    
    @property
    def lineGain(self):
        return self._lineGain.value
    
    @lineGain.setter
    def lineGain(self, value):
        self._lineGain.value = value
    
    @property
    def globalGain(self):
        return self._globalGain.value
    
    @globalGain.setter
    def globalGain(self, value):
        self._globalGain.value = value
        
    @property
    def lineString(self):
        return self._line.string
    
    @lineString.setter
    def lineString(self, s):
        self._line.string = s
    
    @property
    def lineGainString(self):
        return self._lineGain.string
    
    @lineGainString.setter
    def lineGainString(self, s):
        self._lineGain.string = s
    
    @property
    def globalGainString(self):
        return self._globalGain.value
    
    @globalGainString.setter
    def globalGainString(self, s):
        self._globalGain.string = s

    def __getstate__(self):
        dictcopy = dict(self.__dict__)
        dictcopy.pop('_globalDict', None)
        return dictcopy

    def __setstate__(self, state):
        state.setdefault('_globalDict', dict())
        state.pop('line', None)
        self.__dict__ = state
        if not isinstance(self._line, ExpressionValue):
            self._line = ExpressionValue(name="line", globalDict=self._globalDict, value=Q(self._line))
        if not isinstance(self._lineGain, ExpressionValue):
            self._lineGain = ExpressionValue(name='lineGain', globalDict=self._globalDict, value=Q(self._lineGain))
        if not isinstance(self._globalGain, ExpressionValue):
            self._globalGain = ExpressionValue(name='globalGain', globalDict=self._globalDict, value=Q(self._globalGain))
        self._lineValue = self._line.value
        self._line.valueChanged.connect(self.onLineExpressionChanged)
        self._lineGain.valueChanged.connect(self.onLineExpressionChanged)
        self._globalGain.valueChanged.connect(self.onLineExpressionChanged)

    def onLineExpressionChanged(self, name, value, string, origin):
        if name == 'line':
            self._lineValue = value
        self.dataChanged.emit(self)


class Settings:
    def __init__(self):
        self.adjust = Adjust()
        self.shuttlingRoute = ""
        self.shuttlingRepetitions = 1
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('shuttlingRoute', "")
        self.__dict__.setdefault('shuttlingRepetitions', 1)
        
class ShuttlingException(Exception):
    pass


def triplet_iterator(iterable):
    i = 0
    while i+2<len(iterable):
        yield iterable[i:i+3]
        i += 2


class VoltageAdjust(VoltageAdjustForm, VoltageAdjustBase ):
    updateOutput = QtCore.pyqtSignal(object, object)
    shuttleOutput = QtCore.pyqtSignal(object, object)
    
    def __init__(self, config, voltageBlender, globalDict, parent=None):
        VoltageAdjustForm.__init__(self)
        VoltageAdjustBase.__init__(self, parent)
        self.config = config
        self.configname = 'VoltageAdjust.Settings'
        self.settings = self.config.get(self.configname, Settings())
        self.settings.adjust.globalDict = globalDict
        self.adjust = self.settings.adjust
        self.shuttlingGraph = ShuttlingGraph()
        self.voltageBlender = voltageBlender
        self.shuttlingDefinitionFile = None

    def setupUi(self, parent):
        VoltageAdjustForm.setupUi(self, parent)
        self.lineBox.globalDict = self.settings.adjust.globalDict
        self.lineGainBox.globalDict = self.settings.adjust.globalDict
        self.globalGainBox.globalDict = self.settings.adjust.globalDict
        self.lineBox.setExpression( self.adjust._line )
        self.currentLineDisplay.setText(str(self.adjust._line))
        self.lineGainBox.setExpression( self.adjust._lineGain )
        self.globalGainBox.setExpression( self.adjust._globalGain )
        self.adjust.dataChanged.connect(self.onExpressionChanged)
        self.triggerButton.clicked.connect( self.onTrigger )
        # Shuttling
        self.addEdgeButton.clicked.connect( self.addShuttlingEdge )
        self.removeEdgeButton.clicked.connect( self.removeShuttlingEdge )
        self.shuttleEdgeTableModel = ShuttleEdgeTableModel(self.config, self.shuttlingGraph)
        self.delegate = ComboBoxDelegate()
        self.edgeTableView.setModel(self.shuttleEdgeTableModel)
        self.edgeTableView.setItemDelegateForColumn( 8, self.delegate )
        self.edgeTableView.setItemDelegateForColumn(10, self.delegate )
        self.currentPositionLabel.setText( firstNotNone( self.shuttlingGraph.currentPositionName, "" ) )
        self.shuttlingGraph.currentPositionObservable.subscribe( self.onCurrentPositionEvent )
        self.shuttlingGraph.graphChangedObservable.subscribe( self.setupGraphDependent )
        self.setupGraphDependent()
        self.uploadDataButton.clicked.connect( self.onUploadData )
        self.uploadEdgesButton.clicked.connect( self.onUploadEdgesButton )
        restoreGuiState(self, self.config.get('VoltageAdjust.GuiState'))
        self.destinationComboBox.currentIndexChanged[str].connect( self.onShuttleSequence )
        self.shuttlingRouteEdit.setText( " ".join(self.settings.shuttlingRoute) )
        self.shuttlingRouteEdit.editingFinished.connect( self.onSetShuttlingRoute )
        self.shuttlingRouteButton.clicked.connect( self.onShuttlingRoute )
        self.repetitionBox.setValue(self.settings.shuttlingRepetitions)
        self.repetitionBox.valueChanged.connect( self.onShuttlingRepetitions )
        
    def onTrigger(self):
        self.voltageBlender.trigger()
        
    def onShuttlingRepetitions(self, value):
        self.settings.shuttlingRepetitions = int(value)
        
    def onSetShuttlingRoute(self):
        self.settings.shuttlingRoute = re.split(r'\s*(-|,)\s*', str(self.shuttlingRouteEdit.text()).strip() )
        
    def onShuttlingRoute(self):
        self.synchronize()
        if self.settings.shuttlingRoute:
            path = list()
            for start, transition, stop in triplet_iterator(self.settings.shuttlingRoute):
                if transition=="-":
                    path.extend( self.shuttlingGraph.shuttlePath(start, stop) )
            if path:
                self.shuttleOutput.emit( path*self.settings.shuttlingRepetitions, False )                               
        
    def onUploadData(self):
        self.voltageBlender.writeData(self.shuttlingGraph)
    
    def onUploadEdgesButton(self):
        self.writeShuttleLookup()
        
    def writeShuttleLookup(self):
        self.voltageBlender.writeShuttleLookup(self.shuttlingGraph)
    
    def setupGraphDependent(self):
        updateComboBoxItems( self.destinationComboBox, sorted(self.shuttlingGraph.nodes()) )
        
    def shuttlingNodes(self):
        return sorted(self.shuttlingGraph.nodes()) 
    
    def currentShuttlingPosition(self):
        return self.shuttlingGraph.currentPositionName or self.shuttlingGraph.currentPosition

    def onCurrentPositionEvent(self, event):
        self.adjust.line = event.line
        self.currentLineDisplay.setText(str(self.adjust.line))
        self.currentPositionLabel.setText( firstNotNone(event.text, "") )           
        self.updateOutput.emit(self.adjust, False)

    def onShuttleSequence(self, destination, cont=False, instant=False):
        self.synchronize()
        destination = str(destination)
        logger = logging.getLogger(__name__)
        logger.info( "ShuttleSequence" )
        path, preShuttle, postShuttle = self.shuttlingGraph.shuttlePath(None, destination, allow_position=True)
        if path:
            #  TODO: do the pre and post shuttle
            if instant:
                edge = path[-1][2]
                _, toLine = (edge.startLine, edge.stopLine) if path[-1][0]==edge.startName else (edge.stopLine, edge.startLine)
                self.adjust.line = toLine
                self.currentLineDisplay.setText(str(toLine))
                self.updateOutput.emit(self.adjust, True)
            else:
                self.shuttleOutput.emit( path, cont )
        return bool(path)

    def onShuttlingDone(self, currentline):
        self.currentLineDisplay.setText(str(currentline))
        self.adjust.line = currentline
        self.updateOutput.emit(self.adjust, False)

    def addShuttlingEdge(self):
        edge = self.shuttlingGraph.getValidEdge()
        self.shuttleEdgeTableModel.add(edge)

    def removeShuttlingEdge(self):
        for index in sorted(unique([ i.row() for i in self.edgeTableView.selectedIndexes() ]), reverse=True):
            self.shuttleEdgeTableModel.remove(index)
        
    def onExpressionChanged(self, value):
        self.updateOutput.emit(self.adjust, True)

    def onValueChanged(self, attribute, value):
        setattr(self.adjust, attribute, float(value))
        self.updateOutput.emit(self.adjust, True)
    
    def setLine(self, line):
        self.shuttlingGraph.setPosition( line )
        
    def setCurrentPositionLabel(self, event ):
        self.currentPositionLabel.setText( event.text )
    
    def saveConfig(self):
        self.config[self.configname] = self.settings
        self.config['VoltageAdjust.GuiState'] = saveGuiState(self)
        root = ElementTree.Element('VoltageAdjust')
        self.shuttlingGraph.toXmlElement(root)
        if self.shuttlingDefinitionFile:
            with open(self.shuttlingDefinitionFile, 'wb') as f:
                f.write(self.prettify(root))
            
    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        return ElementTree.tostring(elem, encoding='utf-8', pretty_print=True, xml_declaration=True)

    def loadShuttleDef(self, filename):
        if filename is not None:
            self.shuttlingDefinitionFile = filename
            if os.path.exists(filename):
                tree = ElementTree.parse(filename)
                root = tree.getroot()
                
                # load pulse definition
                ShuttlingGraphElement = root.find("ShuttlingGraph")
                newGraph = ShuttlingGraph.fromXmlElement(ShuttlingGraphElement)
                matchingPos = newGraph.getMatchingPosition(self.shuttlingGraph) # Try to match previous graph node/position
                self.shuttlingGraph = newGraph
                self.shuttleEdgeTableModel.setShuttlingGraph(self.shuttlingGraph)
                self.currentPositionLabel.setText( firstNotNone( self.shuttlingGraph.currentPositionName, "" ) )
                self.shuttlingGraph.currentPositionObservable.subscribe( self.onCurrentPositionEvent )
                self.shuttlingGraph.graphChangedObservable.subscribe( self.setupGraphDependent )
                self.setupGraphDependent()
                self.setPosition(matchingPos)
                self.updateOutput.emit(self.adjust, True) # Update the output voltages by setting updateHardware to True

    def setPosition(self, line):
        """ Sets the current position in the shuttling graph. Provides a link for pyqtSignal connections
            to access the shuttlingGraph even after loadShuttleDef replaces it."""
        self.shuttlingGraph.setPosition(line)

    #@doprofile
    def synchronize(self):
        if (self.shuttlingGraph.hasChanged or not self.voltageBlender.shuttlingDataValid()) and self.voltageBlender.dacController.isOpen:
            logging.getLogger(__name__).info("Uploading Shuttling data")
            self.voltageBlender.writeData(self.shuttlingGraph)
            self.writeShuttleLookup()
            self.shuttlingGraph.hasChanged = False
            
