import logging

from PyQt5 import QtCore


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
                if record is None:  # We send this as a sentinel to tell the listener to quit.
                    logger.debug("LoggingReader Thread shutdown requested")
                    break
                clientlogger = logging.getLogger(record.name)
                if record.levelno >= clientlogger.getEffectiveLevel():
                    clientlogger.handle(record)  # No level or filter logic applied - just do it!
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                logger.exception("Exception in Logging Reader Thread")
        logger.info("LoggingReader Thread finished")


