# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import PyQt5.uic
from PyQt5 import QtCore

import logging

from modules.PyqtUtility import BlockSignals
from modules.quantity import Q
from modules.enum import enum
from pulser.Encodings import encode

# server.py
from multiprocessing.connection import Listener

from .controller.ControllerClient import freqToBin, voltageToBin

Form, Base = PyQt5.uic.loadUiType(r'digitalLock\ui\LockControl.ui')


def setBit( var, index, val ):
    """Set the index:th bit of v to x, and return the new value."""
    mask = 1 << index
    var &= ~mask
    if val:
        var |= mask
    return var    


class ClientHandler( QtCore.QThread ):
    setOutputFrequencySignal = QtCore.pyqtSignal( object )
    setHarmonicSignal = QtCore.pyqtSignal(object)
    def __init__(self, client_c, lockSettingsInstance, clientaddress):
        QtCore.QThread.__init__(self)
        self.client_c = client_c
        self.lockSettingsInstance = lockSettingsInstance
        self.clientAddress = clientaddress
        
    def run(self):
        try:
            logging.getLogger(__name__).info("New connection to client '{0}'".format(self.clientAddress))  
            while True:
                command, arguments = self.client_c.recv()
                function = getattr( self, command )
                try:
                    retval = function( *arguments )
                    self.client_c.send( retval )
                except Exception as e:
                    self.client_c.send(e) 
        except EOFError:
            logging.getLogger(__name__).info("Client '{0}' disconnect".format(self.clientAddress))  
        except Exception as e:
            logging.getLogger(__name__).exception(e)  
            
                
    def setOutputFrequency(self, frequency ):
        self.setOutputFrequencySignal.emit( frequency )
        return self.getOutputFrequency()
    
    def getOutputFrequency(self):
        with QtCore.QMutexLocker(self.lockSettingsInstance.mutex):
            currentFreq = self.lockSettingsInstance.lockSettings.outputFrequency
        return currentFreq

    def setHarmonic(self, harmonic):
        self.setHarmonicSignal.emit(harmonic)
        return self.getHarmonic()

    def getHarmonic(self):
        with QtCore.QMutexLocker(self.lockSettingsInstance.mutex):
            harmonic = self.lockSettingsInstance.lockSettings.harmonic
        return harmonic


class LockServer( QtCore.QThread ):
    def __init__(self, address, authkey, locksettingsInstance):
        QtCore.QThread.__init__(self)
        self.address = address
        self.authkey = authkey
        self.lockSettingsInstance = locksettingsInstance
        
    def run(self):
        try:
            server_c = Listener(self.address, authkey=self.authkey)
            while True:
                client_c = server_c.accept()
                clientaddress = server_c.last_accepted
                handler = ClientHandler(client_c, self.lockSettingsInstance, clientaddress)
                handler.setOutputFrequencySignal.connect( self.lockSettingsInstance.setOutputFrequencyGui )
                handler.setHarmonicSignal.connect(self.lockSettingsInstance.setHarmonicGui)
                handler.start()
        except Exception as e:
            logging.getLogger(__name__).exception(e)  

class LockSettings(object):
    def __init__(self):
        self.referenceFrequency = Q(0, 'MHz')
        self.referenceAmplitude = Q(0)
        self.outputFrequency = Q(0, 'MHz')
        self.outputAmplitude = Q(0)
        self.harmonic = Q(107)
        self.errorsigHarmonic = Q(1)
        self.offset = Q(0, 'V')
        self.pCoefficient = Q(0)
        self.iCoefficient = Q(0)
        self.harmonicReferenceFrequency = Q(0, 'Hz')
        self.resonanceFrequency = Q(12642.817, 'MHz')
        self.filter = LockControl.FilterOptions.NoFilter
        self.harmonicOutput = LockControl.HarmonicOutputOptions.Off
        self.mode = 0
        self.dcThreshold = Q(0, 'V')
        self.enableDCThreshold = False
        self.refGTcombLine = False #True if the reference frequency is greater than the comb line it is mixed with
        self.coreMode = 0
        
    def __setstate__(self, d):
        self.__dict__ = d
        self.__dict__.setdefault( 'enableLowPass', False )
        self.__dict__.setdefault( 'mode', 0 )
        self.__dict__.setdefault( 'filter', LockControl.FilterOptions.NoFilter )
        self.__dict__.setdefault( 'harmonicOutput', LockControl.HarmonicOutputOptions.Off )
        self.__dict__.setdefault( 'resonanceFrequency', Q(12642.817, 'MHz') )
        self.__dict__.setdefault( 'harmonicReferenceFrequency', Q(0, 'MHz') )
        self.__dict__.setdefault( 'dcThreshold', Q(0, 'V') )
        self.__dict__.setdefault( 'enableDCThreshold', False )
        self.__dict__.setdefault( 'refGTcombLine', False )
        self.__dict__.setdefault( 'coreMode', 0 )
        self.__dict__.setdefault( 'errorsigHarmonic', Q(1) )
        self.mode &= ~1  # clear the lock enable bit


class LockControl(Form, Base):
    dataChanged = QtCore.pyqtSignal( object )
    AutoStates = enum('idle', 'autoOffset', 'autoLock')
    FilterOptions = enum('NoFilter', 'Lowp_50_29', 'Lowp_40_29', 'Low_30_20', 'Lowp_100_29', 'Lowp_200_29', 'Lowp_300_29', 'Lowp_300_13', 'Lowp_200_9', 'Lowp100_17')
    HarmonicOutputOptions = enum('Off', 'On', 'External')
    def __init__(self, controller, config, settings, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.controller = controller
        self.config = config
        self.settings = settings
        self.lockSettings = self.config.get("LockSettings", LockSettings())
        self.autoState = self.AutoStates.idle
        self.mutex = QtCore.QMutex()
    
    def closeEvent(self, e):
        self.lockServer.quit()
        
    def setupSpinBox(self, localname, settingsname, updatefunc, unit ):
        box = getattr(self, localname)
        value = getattr(self.lockSettings, settingsname)
        box.setValue( value )
        box.dimension = unit
        box.valueChanged.connect( updatefunc )
        updatefunc( value )
    
    def setupUi(self):
        Form.setupUi(self, self)
        self.setupSpinBox('magReferenceFreq', 'referenceFrequency', self.setReferenceFrequency, 'MHz')
        self.setupSpinBox('magReferenceAmpl', 'referenceAmplitude', self.setReferenceAmplitude, '')
        self.setupSpinBox('magOutputFreq', 'outputFrequency', self.setOutputFrequency, 'MHz')
        self.setupSpinBox('magOutputAmpl', 'outputAmplitude', self.setOutputAmplitude, '')
        self.setupSpinBox('magHarmonic', 'harmonic', self.setHarmonic, '')
        self.setupSpinBox('magErrorsigHarmonic', 'errorsigHarmonic', self.setErrorsigHarmonic, '')
        self.setupSpinBox('magHarmonicReference', 'harmonicReferenceFrequency', self.setharmonicReferenceFrequency, 'MHz')
        self.setupSpinBox('magOffset', 'offset', self.setOffset, 'V')
        self.setupSpinBox('magPCoeff', 'pCoefficient', self.setpCoefficient, '')
        self.setupSpinBox('magICoeff', 'iCoefficient', self.setiCoefficient, '')
        self.setupSpinBox('magResonanceFreq', 'resonanceFrequency', self.setResonanceFreq, 'MHz')
        self.setupSpinBox('magDCThreshold', 'dcThreshold', self.onDCThreshold, 'V')
        
        self.filterCombo.addItems( list(self.FilterOptions.mapping.keys()) )
        self.filterCombo.setCurrentIndex( self.lockSettings.filter )
        self.filterCombo.currentIndexChanged[int].connect( self.onFilterChange )
        self.harmonicOutputCombo.addItems( list(self.HarmonicOutputOptions.mapping.keys()) )
        self.harmonicOutputCombo.setCurrentIndex( self.lockSettings.harmonicOutput )
        self.harmonicOutputCombo.currentIndexChanged[int].connect( self.onHarmonicOutputChange )
        self.autoLockButton.clicked.connect( self.onAutoLock )
        self.lockButton.clicked.connect( self.onLock )
        self.unlockButton.clicked.connect( self.onUnlock )
        self.dataChanged.emit( self.lockSettings )
        self.dcThresholdBox.setChecked( self.lockSettings.enableDCThreshold )
        self.dcThresholdBox.stateChanged.connect( self.onDCThresholdEnable )
        self.refGTcombLineBox.setChecked( self.lockSettings.refGTcombLine  )
        self.refGTcombLineBox.stateChanged.connect( self.onSetRefGTcombLine )
        self._setHarmonics()
        self.lockServer = LockServer(("", 16888), b"yb171", self)
        self.lockServer.start()
                
    def setharmonicReferenceFrequency(self, value):
        self.lockSettings.harmonicReferenceFrequency = value
        self.calculateOffset()

    def onSetRefGTcombLine(self, state):
        self.lockSettings.refGTcombLine = state == QtCore.Qt.Checked
        self.dataChanged.emit( self.lockSettings )
        self.calculateOffset()

    def onDCThresholdEnable(self, state):
        self.lockSettings.enableDCThreshold = state == QtCore.Qt.Checked
        self.onDCThreshold(self.lockSettings.dcThreshold)
        
    def onDCThreshold(self, value):
        binvalue = encode(value, self.settings.onBoardADCEncoding) if self.lockSettings.enableDCThreshold else 0
        self.controller.setDCThreshold( binvalue )
        self.lockSettings.dcThreshold = value
        self.dataChanged.emit( self.lockSettings )
        
    def onFilterChange(self, filterMode):
        self.lockSettings.filter = filterMode
        self.lockSettings.mode = setBit( self.lockSettings.mode, 1, self.lockSettings.filter>0 )
        self.controller.setFilter( self.lockSettings.filter )
        self.controller.setMode(self.lockSettings.mode)
        self.dataChanged.emit(self.lockSettings )
        
    def onHarmonicOutputChange(self, outputMode ):
        self.lockSettings.harmonicOutput = outputMode
        self.lockSettings.mode = setBit( self.lockSettings.mode, 14, outputMode==1 )
        self.lockSettings.mode = setBit( self.lockSettings.mode, 15, outputMode==2 )
        self.controller.setMode(self.lockSettings.mode)
        self.dataChanged.emit(self.lockSettings )
        
    def onLock(self):
        self.lockSettings.mode = setBit( self.lockSettings.mode, 0, True)
        self.controller.setMode(self.lockSettings.mode)
    
    def onUnlock(self):
        self.lockSettings.mode = setBit( self.lockSettings.mode, 0, False)
        self.controller.setMode(self.lockSettings.mode)
    
    def onAutoLock(self):
        self.autoOffset()
        
    def setReferenceFrequency(self, value):
        binvalue = freqToBin(value)
        self.controller.setReferenceFrequency(binvalue)
        self.lockSettings.referenceFrequency = value
        self.dataChanged.emit( self.lockSettings )
        self.calculateOffset()

    def setResonanceFreq(self, value):
        self.lockSettings.resonanceFrequency = value
        self.calculateOffset()
        
    def calculateOffset(self):
        fhf = self.lockSettings.resonanceFrequency
        n = self.lockSettings.harmonic #e.g. 105
        error_n = self.lockSettings.errorsigHarmonic #e.g. 32
        fref_uwave = self.lockSettings.harmonicReferenceFrequency
        fref_rf = self.lockSettings.referenceFrequency
        f_out = self.lockSettings.outputFrequency
        f_rep = (fref_uwave - fref_rf)/error_n if self.lockSettings.refGTcombLine else (fref_uwave + fref_rf)/error_n

        offsetFrequency = abs( fhf - abs(n)*f_rep + (-1 if n<0 else 1) * f_out )
        self.magOffsetFreq.setValue(offsetFrequency)

    def setReferenceAmplitude(self, value):
        binvalue = int(value)
        self.controller.setReferenceAmplitude(binvalue)
        self.lockSettings.referenceAmplitude = value
        self.dataChanged.emit( self.lockSettings )
        
    def setOutputFrequencyGui(self, value):
        self.magOutputFreq.setValue(value)
        self.setOutputFrequency(value)
        
    def setOutputFrequency(self, value):
        binvalue = freqToBin(value)
        self.controller.setOutputFrequency(binvalue)
        self.lockSettings.outputFrequency = value
        self.dataChanged.emit( self.lockSettings )
        self.calculateOffset()

    def setOutputAmplitude(self, value):
        binvalue = int(value)
        self.controller.setOutputAmplitude(binvalue)
        self.lockSettings.outputAmplitude = value
        self.dataChanged.emit( self.lockSettings )

    def setHarmonicGui(self, harmonic):
        with BlockSignals(self.magHarmonic):
            self.magHarmonic.setValue(harmonic)
        self.setHarmonic(harmonic)

    def setHarmonic(self, value):
        self.lockSettings.harmonic = value
        self._setHarmonics()
        
    def setErrorsigHarmonic(self, value):
        self.lockSettings.errorsigHarmonic = value
        self._setHarmonics()
        
    def _setHarmonics(self):
        errorsigHarmonic = int(self.lockSettings.errorsigHarmonic)
        self.controller.setHarmonic( int(self.lockSettings.harmonic) )
        self.controller.setFixedPointHarmonic( int( self.lockSettings.harmonic*( (1<<56)/float(errorsigHarmonic)))  )
        self.lockSettings.coreMode = 0 if errorsigHarmonic==1 else 1
        self.controller.setCoreMode( self.lockSettings.coreMode )
        self.dataChanged.emit( self.lockSettings )
        self.calculateOffset()
        
    def setOffset(self, value):
        binvalue = voltageToBin(value)
        self.controller.setInputOffset(binvalue)
        logging.getLogger(__name__).debug("offset {0} binary {1:x}".format(value, binvalue))
        self.lockSettings.offset = value
        self.dataChanged.emit( self.lockSettings )
        
    def setpCoefficient(self, pCoeff):       
        binvalue = int(pCoeff)
        self.controller.setpCoeff(binvalue)
        self.lockSettings.pCoefficient = pCoeff
        self.dataChanged.emit( self.lockSettings )

    def setiCoefficient(self, iCoeff):       
        binvalue = int(iCoeff)
        self.controller.setiCoeff(binvalue)
        self.lockSettings.iCoefficient = iCoeff
        self.dataChanged.emit( self.lockSettings )

    def saveConfig(self):
        self.config["LockSettings"] = self.lockSettings
        
    def onTraceData(self, data):
        pass
    
    def onStreamData(self, data):
        if self.autoState == self.AutoStates.autoOffset:
            newOffset = (data.errorSigMax + data.errorSigMin)/2 + self.lockSettings.offset
            self.magOffset.setValue( newOffset )
            self.setOffset(newOffset)
            self.autoState = self.AutoStates.idle
    
    def autoOffset(self):
        if self.autoState == self.AutoStates.idle:
            self.autoState = self.AutoStates.autoOffset
        
