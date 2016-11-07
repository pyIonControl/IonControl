# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from queue import Queue
import logging
import multiprocessing
from modules.quantity import Q
from pulser.Encodings import encode

from PyQt5 import QtCore

from digitalLock.controller.ControllerServer import FinishException, ErrorMessages, FPGAException, DigitalLockControllerServer
from modules.quantity import Q


def check(number, command):
    if number is not None and number<0:
        raise FPGAException("OpalKelly exception '{0}' in command {1}".format(ErrorMessages.get(number, number), command))

frequencyQuantum = Q(1, 'GHz') / 0xffffffffffff
frequencyQuantumHz = frequencyQuantum.m_as('Hz')
voltageQuantum = Q(10, 'V') / 0xffff
binOffsetADC7606 = 0x8fff
voltageQuantumExternal = Q(2.5, 'V') / 0xfff
voltageQuantumExternal16 = Q(2.5, 'V') / 0xffff
voltageQuantumV = voltageQuantum.m_as('V')
clockTick = Q(5, 'ns')
sampleTime = Q(1, 'us')

def binToFreq( binvalue ):
    return binvalue * frequencyQuantum

def binToFreqHz( binvalue ):
    return binvalue * frequencyQuantumHz

def binToVoltage( binvalue ):
    return binvalue * voltageQuantum

def binToVoltageV( binvalue ):
    return binvalue * voltageQuantumV

def freqToBin( mag_value ):
    return int(mag_value / frequencyQuantum) & 0xffffffffffff

def voltageToBin( mag_value ):
    return int(mag_value / voltageQuantum) & 0xffff


class QueueReader(QtCore.QThread):      
    def __init__(self, controller, dataQueue, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.exiting = False
        self.controller = controller
        self.running = False
        self.dataMutex = QtCore.QMutex()           # protects the thread data
        self.dataQueue = dataQueue
        self.dataHandler = { 'StreamData': lambda data : self.controller.streamDataAvailable.emit(data),
                             'ScopeData': lambda data: self.controller.scopeDataAvailable.emit(data),
                             'FinishException': lambda data: self.raise_(FinishException()) }
           
    def raise_(self, ex):
        raise ex
   
    def run(self):
        logger = logging.getLogger(__name__)
        logger.info( "QueueReader thread started." )
        while True:
            try:
                data = self.dataQueue.get()
                #logger.info("{0}".format( data.__class__.__name__ ) )
                self.dataHandler[ data.__class__.__name__ ]( data )
            except (KeyboardInterrupt, SystemExit, FinishException):
                break
            except Exception:
                logger.exception("Exception in QueueReader")
        logger.info( "QueueReader thread finished." )

class LoggingReader(QtCore.QThread):
    def __init__(self, loggingQueue, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.loggingQueue = loggingQueue
        
    def run(self):
        logger = logging.getLogger(__name__)
        logger.debug("LoggingReader Thread running")
        while True:
            try:
                record = self.loggingQueue.get()
                if record is None: # We send this as a sentinel to tell the listener to quit.
                    logger.debug("LoggingReader Thread shutdown requested")
                    break
                clientlogger = logging.getLogger(record.name)
                if record.levelno>=clientlogger.getEffectiveLevel():
                    clientlogger.handle(record) # No level or filter logic applied - just do it!
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                logger.exception("Exception in Logging Reader Thread")
        logger.info("LoggingReader Thread finished")

                

class Controller(QtCore.QObject):
    sleepQueue = Queue()   # used to be able to interrupt the sleeping procedure

    streamDataAvailable = QtCore.pyqtSignal( 'PyQt_PyObject' )
    scopeDataAvailable = QtCore.pyqtSignal( 'PyQt_PyObject' )
    lockStatusChanged = QtCore.pyqtSignal( object )
    
    timestep = Q(5, 'ns')

    def __init__(self):
        super(Controller, self).__init__()
        self.xem = None
        self.Mutex = QtCore.QMutex
        
        self.dataQueue = multiprocessing.Queue()
        self.clientPipe, self.serverPipe = multiprocessing.Pipe()
        self.loggingQueue = multiprocessing.Queue()
                
        self.serverProcess = DigitalLockControllerServer(self.dataQueue, self.serverPipe, self.loggingQueue )
        self.serverProcess.start()

        self.queueReader = QueueReader(self, self.dataQueue)
        self.queueReader.start()
        
        self.loggingReader = LoggingReader(self.loggingQueue)
        self.loggingReader.start()


    def shutdown(self):
        self.clientPipe.send(('finish', (), {}))
        self.serverProcess.join()
        self.queueReader.wait()
        self.loggingReader.wait()
        logging.getLogger(__name__).debug("PulseHardwareClient Shutdown completed")
        
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            return super(Controller, self).__getattr__(name)
        def wrapper(*args, **kwargs):
            self.clientPipe.send((name, args, kwargs))
            return processReturn( self.clientPipe.recv() )
        setattr(self, name, wrapper)
        return wrapper      
                    

def processReturn( returnvalue ):
    if isinstance( returnvalue, Exception ):
        raise returnvalue
    else:
        return returnvalue

