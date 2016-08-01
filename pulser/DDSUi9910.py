# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import functools

from PyQt5 import QtGui
import PyQt5.uic

from pulser import Ad9910
from modules.quantity import mg

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/DDS9910.ui')
DDSForm, DDSBase = PyQt5.uic.loadUiType(uipath)

def extendTo(array, length, defaulttype):
    for _ in range( len(array), length ):
        array.append(defaulttype())

class DDSUi(DDSForm, DDSBase):
    def __init__(self,config,pulser,parent=None):
        DDSBase.__init__(self, parent)
        DDSForm.__init__(self)
        self.numChannels = 4
        self.config = config
        self.frequency = self.config.get('DDSUi.Frequency', [Q(0, 'MHz')]*4)
        extendTo(self.frequency, self.numChannels, lambda: Q(0, 'MHz') )
        self.phase = self.config.get('DDSUi.Phase', [Q(0, 'rad')]*4)
        extendTo(self.phase, self.numChannels, lambda: Q(0, 'rad') )
        self.amplitude = self.config.get('DDSUi.Amplitude', [0]*4)
        extendTo(self.amplitude, self.numChannels, lambda: 0 )
        self.names = self.config.get('DDSUi.Names', ['']*8)
        extendTo(self.names, self.numChannels, lambda: '' )
        self.ad9910 = Ad9910.Ad9910(pulser)
        self.autoApply = self.config.get('DDSUi.autoApply', False)
        
    def setupUi(self, parent):
        DDSForm.setupUi(self, parent)
        for channel, box  in enumerate([self.frequencyBox0, self.frequencyBox1, self.frequencyBox2, self.frequencyBox3]):
            box.setValue( self.frequency[channel] )
            box.valueChanged.connect( functools.partial(self.onFrequency, box, channel))
        for channel, box  in enumerate([self.phaseBox0, self.phaseBox1, self.phaseBox2, self.phaseBox3]):
            box.setValue( self.phase[channel] )
            box.valueChanged.connect( functools.partial(self.onPhase, box, channel))
        for channel, box  in enumerate([self.amplitudeBox0, self.amplitudeBox1, self.amplitudeBox2, self.amplitudeBox3]):
            box.setValue( self.amplitude[channel] )
            box.editingFinished.connect( functools.partial(self.onAmplitude, box, channel))
        for channel, box in enumerate([self.channelEdit0, self.channelEdit1, self.channelEdit2, self.channelEdit3]):
            box.setText(self.names[channel])
            box.textChanged.connect( functools.partial(self.onName, box, channel) )
        
        for channel, box  in enumerate([self.rampMin0, self.rampMin1, self.rampMin2, self.rampMin3, 
                                        self.rampMax0, self.rampMax1, self.rampMax2, self.rampMax3]):
            box.editingFinished.connect( functools.partial(self.onRampLimits, box, channel))   
            
        for channel, box  in enumerate([self.rampStepUp0, self.rampStepUp1, self.rampStepUp2, self.rampStepUp3, 
                                        self.rampStepDown0, self.rampStepDown1, self.rampStepDown2, self.rampStepDown3]):
            box.editingFinished.connect( functools.partial(self.onRampStep, box, channel))  
            
        for channel, box  in enumerate([self.rampRatePos0, self.rampRatePos1, self.rampRatePos2, self.rampRatePos3, 
                                        self.rampRateNeg0, self.rampRateNeg1, self.rampRateNeg2, self.rampRateNeg3]):
            box.editingFinished.connect( functools.partial(self.onRampRate, box, channel))        
        
        
        for channel, box  in enumerate([self.rampEnable0, self.rampEnable1, self.rampEnable2, self.rampEnable3, 
                                        self.rampDwellHigh0, self.rampDwellHigh1, self.rampDwellHigh2, self.rampDwellHigh3,
                                        self.rampDwellLow0, self.rampDwellLow1, self.rampDwellLow2, self.rampDwellLow3]):
            box.stateChanged.connect( functools.partial(self.onRampSettings, box, channel)) 
            
        for channel, box  in enumerate([self.rampType0, self.rampType1, self.rampType2, self.rampType3]):
            box.currentIndexChanged.connect( functools.partial(self.onRampSettings, box, channel))             
            
        self.applyButton.clicked.connect( self.onApply )
        self.resetButton.clicked.connect( self.onReset )
        self.writeAllButton.clicked.connect( self.onWriteAll )
        self.autoApplyBox.setChecked( self.autoApply )
        self.autoApplyBox.stateChanged.connect( self.onStateChanged )
        self.onWriteAll()
        self.onApply()
            
    def setDisabled(self, disabled):
        for widget  in [self.frequencyBox0, self.frequencyBox1, self.frequencyBox2, self.frequencyBox3,
                        self.phaseBox0, self.phaseBox1, self.phaseBox2, self.phaseBox3,
                        self.amplitudeBox0, self.amplitudeBox1, self.amplitudeBox2, self.amplitudeBox3]:
            widget.setEnabled( not disabled )        
            
    def onStateChanged(self, state ):
        self.autoApply = self.autoApplyBox.isChecked()

    def onFrequency(self, box, channel, value):
        self.ad9910.setFrequency(channel, box.value() )
        self.frequency[channel] = box.value()
        if self.autoApply: self.onApply()
        
    def onPhase(self, box, channel, value):
        self.ad9910.setPhase(channel, box.value())
        self.phase[channel] = box.value()
        if self.autoApply: self.onApply()
    
    def onAmplitude(self, box, channel):
        self.ad9910.setAmplitude(channel, box.value())
        self.amplitude[channel] = box.value()
        if self.autoApply: self.onApply()
    
    def onName(self, box, channel, text):
        self.names[channel] = str(text)
        
    def onRampLimits(self, box, channel):
        # Don't care which was changed, max or min, take both 
        rampMin = self.__getattr__('rampMin'+str(channel)).value()
        rampMax = self.__getattr__('rampMax'+str(channel)).value()
        rampType = self.__getattr__('rampType'+str(channel)).currentIndex()
        self.ad9910.setRampLimits(channel, rampType, rampMin, rampMax)
        if self.autoApply: self.onApply()

    def onRampStep(self, box, channel): # input in MHz
        rampStepUp = self.__getattr__('rampStepUp'+str(channel)).value()
        rampStepDown = self.__getattr__('rampStepDown'+str(channel)).value()
        rampType = self.__getattr__('rampType'+str(channel)).currentIndex()
        self.ad9910.setRampStep(channel, rampType, rampStepUp, rampStepDown)
        if self.autoApply: self.onApply()
    
    def onRampRate(self, box, channel): #input in time
        rampNegRate = self.__getattr__('rampRateNeg'+str(channel)).value()
        rampPosRate = self.__getattr__('rampRatePos'+str(channel)).value()
        self.ad9910.setRampTimeStep(channel, rampNegRate, rampPosRate)
        if self.autoApply: self.onApply()

    def onRampSettings(self, box, channel):
        rampDwellHigh = self.__getattr__('rampDwellHigh'+str(channel)).QAbstractButton.isChecked()
        rampDwellLow = self.__getattr__('rampDwellLow'+str(channel)).QAbstractButton.isChecked()
        rampEnable = self.__getattr__('rampEnable'+str(channel)).QAbstractButton.isChecked()
        rampType = self.__getattr__('rampType'+str(channel)).currentIndex()
        self.ad9910.setCFR2register(channel, rampEnable, rampType, not rampDwellHigh, not rampDwellLow)
        if self.autoApply: self.onApply() 
        
    def onRampType(self, box, channel):
        rampDwellHigh = self.__getattr__('rampDwellHigh'+str(channel)).QAbstractButton.isChecked()
        rampDwellLow = self.__getattr__('rampDwellLow'+str(channel)).QAbstractButton.isChecked()
        rampEnable = self.__getattr__('rampEnable'+str(channel)).QAbstractButton.isChecked()
        rampType = self.__getattr__('rampType'+str(channel)).currentIndex()
        self.ad9910.setCFR2register(channel, rampEnable, rampType, not rampDwellHigh, not rampDwellLow)
        # resend ramp type dependents when ramp type is changed, just to be sure:        
        self.onRampLimits(box, channel)
        self.onRampStep(box, channel)
        if self.autoApply: self.onApply()  
        
    def onWriteAll(self):
        for channel, box  in enumerate([self.frequencyBox0, self.frequencyBox1, self.frequencyBox2, self.frequencyBox3]):
            self.onFrequency( box, channel, box.value() )
        for channel, box  in enumerate([self.phaseBox0, self.phaseBox1, self.phaseBox2, self.phaseBox3]):
            self.onPhase( box, channel, box.value() )
        for channel, box  in enumerate([self.amplitudeBox0, self.amplitudeBox1, self.amplitudeBox2, self.amplitudeBox3]):
            self.onAmplitude( box, channel )
        for channel, box  in enumerate([self.rampMin0, self.rampMin1, self.rampMin2, self.rampMin3, 
                                        self.rampMax0, self.rampMax1, self.rampMax2, self.rampMax3]):
            self.onRampLimits(box, channel)   
        for channel, box  in enumerate([self.rampStepUp0, self.rampStepUp1, self.rampStepUp2, self.rampStepUp3, 
                                        self.rampStepDown0, self.rampStepDown1, self.rampStepDown2, self.rampStepDown3]):
            self.onRampStep(box, channel)  
        for channel, box  in enumerate([self.rampRatePos0, self.rampRatePos1, self.rampRatePos2, self.rampRatePos3, 
                                        self.rampRateNeg0, self.rampRateNeg1, self.rampRateNeg2, self.rampRateNeg3]):
            self.onRampRate(box, channel)  
        for channel, box  in enumerate([self.rampEnable0, self.rampEnable1, self.rampEnable2, self.rampEnable3, 
                                        self.rampDwellHigh0, self.rampDwellHigh1, self.rampDwellHigh2, self.rampDwellHigh3,
                                        self.rampDwellLow0, self.rampDwellLow1, self.rampDwellLow2, self.rampDwellLow3]):
            self.onRampSettings(box, channel)  
        if self.autoApply: self.onApply
        
    def saveConfig(self):
        self.config['DDSUi.Frequency'] = self.frequency
        self.config['DDSUi.Phase'] = self.phase
        self.config['DDSUi.Amplitude'] = self.amplitude
        self.config['DDSUi.Names'] = self.names
        self.config['DDSUi.autoApply'] = self.autoApply
        
    def onApply(self):
        self.ad9910.update(0xff) # Currently does not work for 9910
        
    def onReset(self):
        self.ad9910.reset(0xff)
             
if __name__ == "__main__":
    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    with configshelve.configshelve("test") as config:
        ui = DDSUi(config, None)
        ui.setupUi(ui)
        ui.show()
        sys.exit(app.exec_())
