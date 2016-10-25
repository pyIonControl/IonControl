import logging
from multiprocessing import Process
from mylogging.ServerLogging import configureServerLogging

class FinishException(Exception):
    pass


class ServerProcess(Process):
    def __init__(self, dataQueue=None, commandPipe=None, loggingQueue=None, sharedMemoryArray=None):
        Process.__init__(self)
        self.dataQueue = dataQueue
        self.commandPipe = commandPipe
        self.running = True
        self.loggingQueue = loggingQueue
        self.sharedMemoryArray = sharedMemoryArray

    def readDataFifo(self):
        pass

    def run(self):
        try:
            configureServerLogging(self.loggingQueue)
            logger = logging.getLogger(__name__)
            while self.running:
                if self.commandPipe.poll(0.01):
                    try:
                        commandstring, argument = self.commandPipe.recv()
                        command = getattr(self, commandstring)
                        logger.debug("ProcessServer {0}".format(commandstring))
                        self.commandPipe.send(command(*argument))
                    except Exception as e:
                        self.commandPipe.send(e)
                self.readDataFifo()
            self.dataQueue.put(FinishException())
            logger.info("Server Process {0} finished.".format(self.__class__.__name__))
        except Exception as e:
            logger.error("Server Process {0} exception {1}".format(self.__class__.__name__, e))
        self.dataQueue.close()
        self.loggingQueue.put(None)
        self.loggingQueue.close()

