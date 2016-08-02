# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore
import logging
import queue
import time
import sys


def processReturn( returnvalue ):
    if isinstance( returnvalue, Exception ):
        raise returnvalue
    else:
        return returnvalue

class InstrumentLoggingReader(QtCore.QThread):  
    newData = QtCore.pyqtSignal( object, object )
    newException = QtCore.pyqtSignal( object )
    def __init__(self, name, reader, commandQueue, responseQueue, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.exiting = False
        self.reader = reader
        self.commandQueue = commandQueue
        self.responseQueue = responseQueue
        self._readWait = 0
        self.name = name
   
    def run(self):
        from mylogging.ExceptionLogButton import GlobalExceptionLogButtonSlot        
        if GlobalExceptionLogButtonSlot is not None:
            logging.getLogger(__name__).info("ExceptionLogButton connected for new thread")
            self.newException.connect( GlobalExceptionLogButtonSlot )
        else:
            logging.getLogger(__name__).warning("ExceptionLogButton not available")            
        while not self.exiting:
            try:
                try:
                    timeout = self.reader.waitTime if hasattr(self.reader, 'waitTime') else 0.1
                    command, arguments  = self.commandQueue.get(timeout=timeout)
                    logging.getLogger(__name__).debug("{0} {1}".format(command, arguments))
                    self.responseQueue.put( getattr( self, command)( *arguments ) )
                except queue.Empty:
                    pass
                data = self.reader.value()
                if data is not None:
                    self.newData.emit( self.name, (time.time(), data) )
            except Exception:
                logging.getLogger(__name__).exception("Exception in QueueReader")
                self.newException.emit( sys.exc_info() )
        self.newData.emit( self.name, None )
        logging.getLogger(__name__).info( "InstrumentLoggingReader thread finished." )
        self.reader.close()
        del self.reader
        
    def paramDef(self):
        return self.reader.paramDef() if hasattr(self.reader, 'paramDef') else []
        
    def directUpdate(self, field, data):
        setattr( self.reader, field, data )
       
    def stop(self):
        self.newData.emit(self.name, None)
        self.exiting = True
        