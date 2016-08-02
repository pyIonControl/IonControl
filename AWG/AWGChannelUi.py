"""
Created on 08 Dec 2015 at 4:11 PM

author: jmizrahi
"""

import logging
import os

import PyQt5.uic
from PyQt5 import QtCore, QtWidgets
from pyqtgraph import mkBrush
from trace.pens import solidBluePen, blue

from AWG.AWGWaveform import AWGWaveform
from AWG.AWGSegmentModel import AWGSegmentModel, nodeTypes

blueBrush = mkBrush(blue)

AWGChanneluipath = os.path.join(os.path.dirname(__file__), '..', 'ui/AWGChannel.ui')
AWGChannelForm, AWGChannelBase = PyQt5.uic.loadUiType(AWGChanneluipath)

class AWGChannelUi(AWGChannelForm, AWGChannelBase):
    """interface for one channel of the AWG.

    Args:
       settings (Settings): AWG settings
       channel (int): channel number for this AWGChannel
       globalDict (dict): dictionary of global variables
    """
    dependenciesChanged = QtCore.pyqtSignal(int)
    def __init__(self, channel, settings, globalDict, waveformCache, parent=None):
        AWGChannelBase.__init__(self, parent)
        AWGChannelForm.__init__(self)
        self.settings = settings
        self.channel = channel
        self.globalDict = globalDict
        self.waveform = AWGWaveform(channel, settings, waveformCache)
        self.waveform.updateDependencies()

    @property
    def plotEnabled(self):
        return self.settings.channelSettingsList[self.channel]['plotEnabled']

    @plotEnabled.setter
    def plotEnabled(self, val):
        self.settings.channelSettingsList[self.channel]['plotEnabled'] = val
        self.settings.saveIfNecessary()

    def setupUi(self, parent):
        AWGChannelForm.setupUi(self, parent)
        #segment table
        self.segmentModel = AWGSegmentModel(self.channel, self.settings, self.globalDict)
        self.segmentView.setModel(self.segmentModel)
        self.segmentView.restoreTreeState(self.settings.channelSettingsList[self.channel]['segmentTreeState'])
        self.segmentModel.segmentChanged.connect(self.onSegmentChanged)
        self.segmentView.segmentChanged.connect(self.onSegmentChanged)
        self.addSegmentButton.clicked.connect(self.onAddSegment)
        self.removeSegmentButton.clicked.connect(self.onRemoveSegment)

        #Context menu
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        addToSetAction = QtWidgets.QAction("Add to Set", self)
        removeFromSetAction = QtWidgets.QAction("Remove From Set", self)
        self.addAction(addToSetAction)
        addToSetAction.triggered.connect(self.onAddToSet)
        self.addAction(removeFromSetAction)
        removeFromSetAction.triggered.connect(self.onRemoveFromSet)

        #plot
        self.plot.setTimeAxis(False)
        self.plotCheckbox.setChecked(self.plotEnabled)
        self.plot.setVisible(self.plotEnabled)
        self.plotCheckbox.stateChanged.connect(self.onPlotCheckbox)
        self.styleComboBox.setCurrentIndex(self.settings.channelSettingsList[self.channel]['plotStyle'])
        self.styleComboBox.currentIndexChanged[int].connect(self.onStyle)
        self.replot()

    def onStyle(self, style):
        """plot style is changed. Save settings and replot."""
        self.settings.channelSettingsList[self.channel]['plotStyle'] = style
        self.settings.saveIfNecessary()
        self.replot()

    def onPlotCheckbox(self, checked):
        """Plot checkbox is changed. plot, or unplot and hide plot."""
        self.plotEnabled = checked
        if not checked:
            self.plot.getItem(0, 0).clear()
        elif checked:
            self.replot()
        self.plot.setVisible(checked)

    def replot(self):
        """Plot the waveform"""
        logger = logging.getLogger(__name__)
        if self.plotEnabled:
            # try:
            points = self.waveform.evaluate()
            points = points.tolist()
            self.plot.getItem(0,0).clear()
            if self.settings.channelSettingsList[self.channel]['plotStyle'] == self.settings.plotStyles.lines:
                self.plot.getItem(0,0).plot(points, pen=solidBluePen)
            if self.settings.channelSettingsList[self.channel]['plotStyle'] == self.settings.plotStyles.points:
                self.plot.getItem(0,0).plot(points, pen=None, symbol='o', symbolSize=3, symbolPen=solidBluePen, symbolBrush=blueBrush)
            if self.settings.channelSettingsList[self.channel]['plotStyle'] == self.settings.plotStyles.linespoints:
                self.plot.getItem(0,0).plot(points, pen=solidBluePen, symbol='o', symbolSize=3, symbolPen=solidBluePen, symbolBrush=blueBrush)
            # except Exception as e:
            #     logger.warning(e.__class__.__name__ + ": " + str(e))

    def onSegmentChanged(self):
        """Update dependencies if a segment changed"""
        self.waveform.updateDependencies()
        self.dependenciesChanged.emit(self.channel)
        self.settings.saveIfNecessary()

    def onAddSegment(self):
        """Add segment button is clicked."""
        indexList = self.segmentView.selectedRowIndexes()
        if indexList:
            selectedNode = self.segmentModel.nodeFromIndex(indexList[-1])
            parent = selectedNode if selectedNode.nodeType==nodeTypes.segmentSet else selectedNode.parent
        else:
            parent = self.segmentModel.root
        self.segmentModel.addNode(parent, nodeTypes.segment)
        self.onSegmentChanged()

    def onRemoveSegment(self):
        """Remove segment button is clicked."""
        self.segmentView.onDelete()
        self.onSegmentChanged()

    def onAddToSet(self):
        logger = logging.getLogger(__name__)
        indexList = self.segmentView.selectedRowIndexes()
        nodeList = [self.segmentModel.nodeFromIndex(index) for index in indexList]
        if nodeList:
            oldParent = nodeList[-1].parent
            sameParent = all([node.parent==oldParent for node in nodeList])
            if not sameParent:
                logger.warning("Selected nodes do not all have the same parent")
            else:
                newParent=self.segmentModel.addNode(oldParent, nodeTypes.segmentSet, nodeList[-1].row+1)
                self.segmentModel.changeParent(nodeList, oldParent, newParent)
                self.segmentView.expandAll()
                self.onSegmentChanged()

    def onRemoveFromSet(self):
        logger = logging.getLogger(__name__)
        indexList = self.segmentView.selectedRowIndexes()
        nodeList = [self.segmentModel.nodeFromIndex(index) for index in indexList]
        if nodeList:
            oldParent = nodeList[-1].parent
            sameParent = all([node.parent==oldParent for node in nodeList])
            if not sameParent:
                logger.warning("Selected nodes do not all have the same parent")
            elif oldParent is self.segmentModel.root:
                pass
            else:
                newParent=oldParent.parent
                self.segmentModel.changeParent(nodeList, oldParent, newParent, oldParent.row)
                self.segmentView.expandAll()
                self.onSegmentChanged()
