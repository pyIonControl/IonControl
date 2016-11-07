# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from queue import Queue
import logging
import multiprocessing
from multiprocessing.sharedctypes import Array

from PyQt5 import QtCore

from modules.quantity import Q
from .InstrumentLoggingWindowServer import FinishException, InstrumentLoggingProcess

class QueueReader(QtCore.QThread):      
    def __init__(self, pulserHardware, dataQueue, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.exiting = False
        self.pulserHardware = pulserHardware
        self.running = False
        self.dataMutex = QtCore.QMutex()           # protects the thread data
        self.dataQueue = dataQueue
        self.dataHandler = { 'Data': lambda data, size : self.pulserHardware.dataAvailable.emit(data, size),
                             'DedicatedData': lambda data, size: self.pulserHardware.dedicatedDataAvailable.emit(data),
                             'FinishException': lambda data, size: self.raise_(FinishException()),
                             'LogicAnalyzerData': lambda data, size: self.onLogicAnalyzerData(data) }
   
    def onLogicAnalyzerData(self, data): 
        self.pulserHardware.logicAnalyzerDataAvailable.emit(data)
        
    def raise_(self, ex):
        raise ex
   
    def run(self):
        logger = logging.getLogger(__name__)
        logger.info( "QueueReader thread started." )
        while True:
            try:
                data = self.dataQueue.get()
                self.dataHandler[ data.__class__.__name__ ]( data, self.dataQueue.qsize() )
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

                

class InstrumentLoggingWindow(QtCore.QObject):
    serverClass = InstrumentLoggingProcess
    sleepQueue = Queue()   # used to be able to interrupt the sleeping procedure

    dataAvailable = QtCore.pyqtSignal( 'PyQt_PyObject', object )
    dedicatedDataAvailable = QtCore.pyqtSignal( 'PyQt_PyObject' )
    logicAnalyzerDataAvailable = QtCore.pyqtSignal( 'PyQt_PyObject' )
    shutterChanged = QtCore.pyqtSignal( 'PyQt_PyObject' )
    ppActiveChanged = QtCore.pyqtSignal( object )
    
    timestep = Q(5, 'ns')

    sharedMemorySize = 256*1024
    def __init__(self, project):
        super(InstrumentLoggingWindow, self).__init__()
        
        self.dataQueue = multiprocessing.Queue()
        self.clientPipe, self.serverPipe = multiprocessing.Pipe()
        self.loggingQueue = multiprocessing.Queue()
        self.sharedMemoryArray = Array( 'L', self.sharedMemorySize, lock=True )
                
        self.serverProcess = self.serverClass(project, self.dataQueue, self.serverPipe, self.loggingQueue, self.sharedMemoryArray )
        self.serverProcess.start()

        self.queueReader = QueueReader(self, self.dataQueue)
        self.queueReader.start()
        
        self.loggingReader = LoggingReader(self.loggingQueue)
        self.loggingReader.start()
        
    def is_alive(self):
        self.serverProcess.is_alive()
        
    def shutdown(self):
        self.clientPipe.send(('finish', (), {}))
        self.serverProcess.join()
        self.queueReader.quit()
        self.loggingReader.quit()
        logging.getLogger(__name__).debug("PulseHardwareClient Shutdown completed")


