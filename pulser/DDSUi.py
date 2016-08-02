# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui
import PyQt5.uic

from pulser import Ad9912
from externalParameter.persistence import DBPersist
from externalParameter.decimation import StaticDecimation
from modules.quantity import is_Q, Q
from functools import partial
import time
from collections import defaultdict
from modules.Expression import Expression
from .DDSTableModel import DDSTableModel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.GuiAppearance import restoreGuiState, saveGuiState 
import logging
from modules.Utility import unique

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/DDS.ui')
DDSForm, DDSBase = PyQt5.uic.loadUiType(uipath)

def extendTo(array, length, defaulttype):
    for _ in range( len(array), length ):
        array.append(defaulttype())
        
        
class DDSChannelSettings(object):
    expression = Expression()
    def __init__(self):
        self.frequency = Q(0, 'MHz')
        self.phase = Q(0)
        self.amplitude = Q(0)
        self.frequencyText = None
        self.phaseText = None
        self.amplitudeText = None
        self.enabled = False
        self.name = ""
        self.squareEnabled = False
        self.shutter = None
        self.channel = None
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('name', '')
        self.__dict__.setdefault('squareEnabled', False)
        self.__dict__.setdefault('shutter', None)
        self.__dict__.setdefault('channel', None)

    def evaluateFrequency(self, globalDict ):
        if self.frequencyText:
            oldfreq = self.frequency
            self.frequency = self.expression.evaluateAsMagnitude(self.frequencyText, globalDict)
            return self.frequency!=oldfreq
        return False
            
    def evaluateAmplitude(self, globalDict ):
        if self.amplitudeText:
            oldamp = self.amplitude
            self.amplitude = self.expression.evaluateAsMagnitude(self.amplitudeText, globalDict)
            return oldamp!=self.amplitude
        return False
    
    def evaluatePhase(self, globalDict ):
        if self.phaseText:
            oldphase= self.phase
            self.phase = self.expression.evaluateAsMagnitude(self.phaseText, globalDict)
            return oldphase!=self.phase
        return False

class DDSUi(DDSForm, DDSBase):
    def __init__(self, pulser, config, configName='DDSUi', globalDict=dict(), parent=None):
        DDSBase.__init__(self, parent)
        DDSForm.__init__(self)
        if pulser.pulserConfiguration():
            self.channelInfo = sorted(list(pulser.pulserConfiguration().ddsChannels.values()), key=lambda x: x.channel)
        else:
            self.channelInfo = []
        self.numChannels = len(self.channelInfo)
        self.config = config
        self.channelConfigName = '{0}.ddsChannels'.format(configName)
        self.autoApplyConfigName = '{0}.autoApply'.format(configName)
        self.guiStateConfigName = '{0}.guiState'.format(configName)
        self.ad9912 = Ad9912.Ad9912(pulser)
        oldDDSChannels = self.config.get(self.channelConfigName, [])
        self.ddsChannels = [oldDDSChannels[i] if i < len(oldDDSChannels) else DDSChannelSettings() for i in range(self.numChannels)]
        self.autoApply = self.config.get(self.autoApplyConfigName, True)
        self.decimation = defaultdict(lambda: StaticDecimation(Q(30, 's')))
        self.persistence = DBPersist()
        self.globalDict = globalDict
        self.pulser = pulser
        self.persistSpace = 'DDS'
        for index, channelinfo in enumerate(self.channelInfo):
            self.ddsChannels[index].channel = channelinfo.channel
            self.ddsChannels[index].shutter = channelinfo.shutter

    def setupUi(self, parent):
        DDSForm.setupUi(self, parent)
        self.ddsTableModel = DDSTableModel(self.ddsChannels, self.globalDict)
        self.tableView.setModel( self.ddsTableModel )
        self.delegate = MagnitudeSpinBoxDelegate(self.globalDict)
        self.tableView.setItemDelegateForColumn(2, self.delegate)
        self.tableView.setItemDelegateForColumn(3, self.delegate)
        self.tableView.setItemDelegateForColumn(4, self.delegate)
        self.applyButton.clicked.connect( self.onApply )
        self.resetButton.clicked.connect( self.onReset )
        self.writeAllButton.clicked.connect( self.onWriteAll )
        self.autoApplyBox.setChecked( self.autoApply )
        self.autoApplyBox.stateChanged.connect( self.onStateChanged )
        try:
            self.onWriteAll()
        except Exception as e:
            logging.getLogger(__name__).warning( "Ignored error while setting DDS: {0}".format(e) )
        self.onApply()
        self.ddsTableModel.frequencyChanged.connect( self.onFrequency )
        self.ddsTableModel.phaseChanged.connect( self.onPhase )
        self.ddsTableModel.amplitudeChanged.connect( self.onAmplitude )
        self.ddsTableModel.enableChanged.connect( self.onEnableChanged )
        self.ddsTableModel.squareChanged.connect( self.onSquareChanged )
        self.pulser.shutterChanged.connect( self.onShutterChanged )
        restoreGuiState(self, self.config.get(self.guiStateConfigName))

    def onShutterChanged(self, shutterBitmask):
        for channel in self.ddsChannels:
            channel.enabled = bool(shutterBitmask & (1<<(channel.shutter)))
        self.ddsTableModel.onShutterChanged()

    def onEnableChanged(self, index, value):
        channelObj = self.ddsChannels[index]
        self.pulser.setShutterBit(channelObj.shutter, value)
            
    def setDisabled(self, disabled):
        pass
            
    def onStateChanged(self, state ):
        self.autoApply = self.autoApplyBox.isChecked()

    def onFrequency(self, channel, value):
        channelObj = self.ddsChannels[channel]
        channel = channelObj.channel
        self.ad9912.setFrequency(channel, value)
        if self.autoApply: self.onApply()
        self.decimation[(0, channel)].decimate(time.time(), value, partial(self.persistCallback, "Frequency:{0}".format(channelObj.name if channelObj.name else channel)))
        
    def onPhase(self, channel, value):
        channelObj = self.ddsChannels[channel]
        channel = channelObj.channel
        self.ad9912.setPhase(channel, value)
        if self.autoApply: self.onApply()
        self.decimation[(1, channel)].decimate(time.time(), value, partial(self.persistCallback, "Phase:{0}".format(channelObj.name if channelObj.name else channel)))

    def onAmplitude(self, channel, value):
        channelObj = self.ddsChannels[channel]
        channel = channelObj.channel
        self.ad9912.setAmplitude(channel, value)
        if self.autoApply: self.onApply()
        self.decimation[(2, channel)].decimate(time.time(), value, partial(self.persistCallback, "Amplitude:{0}".format(channelObj.name if channelObj.name else channel)))
 
    def onSquareChanged(self, channel, enable):
        channelObj = self.ddsChannels[channel]
        channel = channelObj.channel
        self.ad9912.setSquareEnabled(channel, enable)
 
    def persistCallback(self, source, data):
        time, value, minval, maxval = data
        unit = None
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
        self.persistence.persist(self.persistSpace, source, time, value, minval, maxval, unit)
   
    def onWriteAll(self):
        with Ad9912.CombineWrites(self.ad9912) as stream:
            for settings in self.ddsChannels:
                stream.setFrequency(settings.channel, settings.frequency)
                stream.setPhase(settings.channel, settings.phase)
                stream.setAmplitude(settings.channel, settings.amplitude)
                stream.setSquareEnabled(settings.channel, settings.squareEnabled)
        if self.autoApply: 
            self.onApply()
        
    def saveConfig(self):
        self.config[self.channelConfigName] = self.ddsChannels
        self.config[self.autoApplyConfigName] = self.autoApply
        self.config[self.guiStateConfigName] = saveGuiState(self)
        
    def onApply(self):
        self.ad9912.update((1 << self.numChannels) - 1)
        
    def onReset(self):
        indexes = self.tableView.selectedIndexes()
        channels = sorted(unique([ i.row() for i in indexes ]))
        mask = 0
        if channels:
            for ch in channels:
                mask |= 1 << ch
        else:
            mask = 0xff
        self.ad9912.reset(mask)
        
    def evaluate(self, name):
        for setting in self.ddsChannels:
            if setting.evaluateFrequency( self.globalDict ):
                self.ad9912.setFrequency(setting.channel, setting.frequency)
            if setting.evaluatePhase( self.globalDict ):
                self.ad9912.setPhase(setting.channel, setting.phase)
            if setting.evaluateAmplitude( self.globalDict ):
                self.ad9912.setAmplitude(setting.channel, setting.amplitude)
        if self.autoApply: 
            self.onApply()
        self.tableView.viewport().repaint() 
             
if __name__ == "__main__":
    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    with configshelve.configshelve("test") as config:
        ui = DDSUi(config, None)
        ui.setupUi(ui)
        ui.show()
        sys.exit(app.exec_())
