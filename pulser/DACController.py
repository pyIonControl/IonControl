# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import multiprocessing
import struct
from ctypes import c_longlong
from itertools import chain
from multiprocessing.sharedctypes import Array

from PyQt5 import QtCore

import logging
from pulser.DACControllerServer import DACControllerServer, DACControllerException
from pulser.LoggingReader import LoggingReader
from pulser.ServerProcess import FinishException



class QueueReader(QtCore.QThread):
    def __init__(self, pulserHardware, dataQueue, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.exiting = False
        self.pulserHardware = pulserHardware
        self.running = False
        self.dataMutex = QtCore.QMutex()  # protects the thread data
        self.dataQueue = dataQueue
        self.dataHandler = {'CRCData': lambda data: self.pulserHardware.dataAvailable.emit(data),
                            'FinishException': lambda data: self.raise_(FinishException())}

    def onLogicAnalyzerData(self, data):
        self.pulserHardware.logicAnalyzerDataAvailable.emit(data)

    def raise_(self, ex):
        raise ex

    def run(self):
        logger = logging.getLogger(__name__)
        logger.info("QueueReader thread started.")
        while True:
            try:
                data = self.dataQueue.get()
                self.dataHandler[data.__class__.__name__](data)
            except (KeyboardInterrupt, SystemExit, FinishException):
                break
            except Exception:
                logger.exception("Exception in QueueReader")
        logger.info("QueueReader thread finished.")


class DACController(QtCore.QObject):
    serverClass = DACControllerServer
    dataAvailable = QtCore.pyqtSignal(object)
    sharedMemorySize = 256 * 1024
    channelCount = 112

    def __init__(self):
        super().__init__()
        self.Mutex = QtCore.QMutex
        self.dataQueue = multiprocessing.Queue()
        self.clientPipe, self.serverPipe = multiprocessing.Pipe()
        self.loggingQueue = multiprocessing.Queue()
        self.sharedMemoryArray = Array(c_longlong, self.sharedMemorySize, lock=True)

        self.serverProcess = self.serverClass(self.dataQueue, self.serverPipe, self.loggingQueue,
                                              self.sharedMemoryArray)
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
            return super().__getattr__(name)

        def wrapper(*args, **kwargs):
            self.clientPipe.send((name, args, kwargs))
            return processReturn(self.clientPipe.recv())

        setattr(self, name, wrapper)
        return wrapper

    @classmethod
    def shuttleLookupCode(cls, edge, channelCount):
        return struct.pack('=IIII', edge.interpolStopLine * 2 * channelCount,
                           edge.interpolStartLine * 2 * cls.channelCount,
                           int(edge.idleCount), 0x0)

    def toInteger(self, iterable):
        result = list()
        for value in chain(iterable[0::4], iterable[1::4], iterable[2::4], iterable[3::4]):
            if not -10 <= value < 10:
                raise DACControllerException("voltage {0} out of range -10V <= V < 10V".format(value))
            result.append(int(value / 10.0 * 0x7fff))
        return result  # list(chain(range(96)[0::4], range(96)[1::4], range(96)[2::4], range(96)[3::4])) # list( [0x000 for _ in range(96)]) #result #

    @staticmethod
    def boolToCode(b, bit=0):
        return 1 << bit if b else 0


def processReturn(returnvalue):
    if isinstance(returnvalue, Exception):
        raise returnvalue
    else:
        return returnvalue
