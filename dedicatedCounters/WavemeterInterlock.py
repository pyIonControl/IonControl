import json
import logging

import functools
from collections import namedtuple

import time
from PyQt5 import QtNetwork, QtCore

from modules.Observable import Observable

LaserInfoBase = namedtuple("LaserInfoBase", "freq time")

class LaserInfo(LaserInfoBase):
    def __new__(cls, freq, mytime):
        if not isinstance(mytime, time.struct_time):
            mytime = time.gmtime(mytime)
        return LaserInfoBase.__new__(cls, freq, mytime)


class WavemeterPoll(Observable):
    """Polls one given wavemeter for all enabled channel values"""
    page = "/wavemeter/wavemeter/wavemeter-status"
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.qurl = QtCore.QUrl(self.url + self.page)
        self.data = dict()

    def onWavemeterError(self, reply, error):
        """Print out received error"""
        logging.getLogger(__name__).warning(
            "Error {} accessing wavemeter {} at '{}'".format(error, self.name, self.uri))
        reply.finished.disconnect()  # necessary to make reply garbage collectable
        reply.error.disconnect()
        reply.deleteLater()
        del reply
        QtCore.QTimer.singleShot(10000, self.getWavemeterData)

    def getWavemeterData(self):
        """Get the data from the wavemeter at the specified channel."""
        reply = self.am.get(QtNetwork.QNetworkRequest(self.qurl))
        reply.error.connect(functools.partial(self.onWavemeterError, reply))
        reply.finished.connect(functools.partial(self.onWavemeterData, reply))

    def onWavemeterData(self, reply):
        """Execute when reply is received from the wavemeter. Display it on the
           GUI, and check whether it is in range."""
        answer = reply.readAll()  # expect {"0": [456.123, 123456789], ...}
        try:
            data = {(self.name, int(k)): LaserInfo(*v) for k, v in json.loads(answer).items()}
            self.data.update(data)
        except:
            logging.getLogger(__name__).error(
                "Error {} accessing wavemeter {} at '{}'".format(answer, self.name, self.uri))
        QtCore.QTimer.singleShot(1000, self.getWavemeterData)
        self.checkFreqsInRange()
        reply.finished.disconnect()  # necessary to make reply garbage collectable
        reply.error.disconnect()
        reply.deleteLater()
        del reply
        self.firebare(data=self.data)


class WavemeterMonitor(Observable):
    def __init__(self, wavemeters):  # wavemeters is dict with name: url
        self.wavemeters = wavemeters
        self.pollers = [WavemeterPoll(name, url) for name, url in wavemeters.items()]
        for p in self.pollers:
            p.subscribe(self.onData)
            self._data = dict()

    def onData(self, data):
        self._data.update(data)
        self.firebare(data=self._data)

