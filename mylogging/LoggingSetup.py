# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import sys

from PyQt5 import QtCore


class QtLoggingHandler(logging.Handler, QtCore.QObject):    
    textWritten = QtCore.pyqtSignal(object, object)
    def __init__(self):
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self)

    def emit(self, record):
        self.textWritten.emit(self.format(record).rstrip()+"\n", record.levelno)
        
class QtWarningButtonHandler(logging.Handler, QtCore.QObject):  
    textWritten = QtCore.pyqtSignal(object)
    def __init__(self):
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self)

    def emit(self, record):
        self.textWritten.emit(self.format(record).rstrip()+"\n")

class LevelThresholdFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno >= self.passlevel)
        else:
            return (record.levelno < self.passlevel)
        
class LevelListFilter(logging.Filter):
    def __init__(self, passlevellist):
        self.passlevellist = passlevellist
        
    def filter(self, record):
        return record.levelno in self.passlevellist
        
class LevelFilter(logging.Filter):
    def __init__(self, passlevel):
        self.passlevel = passlevel
        
    def filter(self, record):
        return record.levelno == self.passlevel

traceHandler = None
errorHandler = None
def setTraceFilename(filename):
    global traceHandler
    if traceHandler is not None:
        logger.removeHandler(traceHandler)
    traceHandler = logging.FileHandler(filename)
    traceHandler.setFormatter(fileformatter)
    traceHandler.addFilter( LevelFilter(logging.TRACE))  # @UndefinedVariable
    logger.addHandler( traceHandler )

def setErrorFilename(filename):
    global errorHandler
    if errorHandler is not None:
        logger.removeHandler(errorHandler)
    errorHandler = logging.FileHandler(filename)
    errorHandler.setFormatter(fileformatter)
    errorHandler.addFilter( LevelThresholdFilter(logging.ERROR, True) )  # @UndefinedVariable
    logger.addHandler( errorHandler )


TRACE_LEVEL_NUM = 25 
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
def trace(self, message, *args, **kws):
    # Yes, logger takes its '*args' as 'args'.
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws) 
logging.Logger.trace = trace
logging.TRACE = TRACE_LEVEL_NUM

logger = logging.getLogger("")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(levelname)s %(name)s(%(filename)s:%(lineno)d %(funcName)s) %(message)s')

stdoutHandler = logging.StreamHandler(sys.stdout)
stdoutHandler.setFormatter(formatter)
stdoutHandler.addFilter(LevelThresholdFilter(logging.WARNING, False))

stderrHandler = logging.StreamHandler(sys.stderr)
stderrHandler.setFormatter(formatter)
stderrHandler.addFilter(LevelThresholdFilter(logging.WARNING, True))

fileformatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s(%(filename)s:%(lineno)d %(funcName)s) %(message)s')

# fileHandler = logging.FileHandler("messages")
# fileHandler.setFormatter(fileformatter)
# fileHandler.setLevel(logging.INFO) 

qtHandler = QtLoggingHandler()
qtHandler.setFormatter(formatter)

qtWarningButtonHandler = QtWarningButtonHandler()
qtWarningButtonHandler.setFormatter(formatter)
qtWarningButtonHandler.addFilter(LevelListFilter((logging.WARNING, logging.ERROR)))

logger.addHandler(stdoutHandler)
logger.addHandler(stderrHandler)
logger.addHandler(qtHandler)
logger.addHandler(qtWarningButtonHandler)
# logger.addHandler(fileHandler)

pyqtlogger = logging.getLogger("PyQt5")
pyqtlogger.setLevel(logging.ERROR)
del pyqtlogger
