import json
import logging

import functools
from collections import namedtuple, defaultdict

import time
from datetime import datetime, timedelta
from enum import Enum

from PyQt5 import QtNetwork, QtCore

from modules.Observable import Observable
from modules.quantity import Q

LaserInfoBase = namedtuple("LaserInfoBase", "freq time active interlock_enabled interlock_inrange")

class LaserInfo(LaserInfoBase):
    def __new__(cls, **kwargs):
        mytime = kwargs["time"]
        if not isinstance(mytime, datetime):
            mytime = datetime.utcfromtimestamp(mytime)
        return LaserInfoBase.__new__(cls, kwargs.get("freq"), mytime, kwargs.get("active"),
                                     kwargs.get("interlock_enabled"), kwargs.get("interlock_inrange"))


class WavemeterPoll(Observable):
    """Polls one given wavemeter for all enabled channel values"""
    page = "/wavemeter/wavemeter/wavemeter-status"
    def __init__(self, name, url):
        super(WavemeterPoll, self).__init__()
        self.name = name
        self.url = url
        self.qurl = QtCore.QUrl(self.url + self.page)
        self.data = dict()
        self.am = QtNetwork.QNetworkAccessManager()
        QtCore.QTimer.singleShot(0, self.getWavemeterData)

    def onWavemeterError(self, reply, error):
        """Print out received error"""
        logging.getLogger(__name__).warning(
            "Error {} accessing wavemeter {} at '{}'".format(error, self.name, self.url))
        reply.finished.disconnect()  # necessary to make reply garbage collectable
        reply.error.disconnect()
        reply.deleteLater()
        del reply
        QtCore.QTimer.singleShot(20000, self.getWavemeterData)

    def getWavemeterData(self):
        """Get the data from the wavemeter at the specified channel."""
        reply = self.am.get(QtNetwork.QNetworkRequest(self.qurl))
        reply.error.connect(functools.partial(self.onWavemeterError, reply))
        reply.finished.connect(functools.partial(self.onWavemeterData, reply))

    def onWavemeterData(self, reply):
        """Execute when reply is received from the wavemeter. Display it on the
           GUI, and check whether it is in range."""
        answer = reply.readAll().data().decode()  # expect {"0": [456.123, 123456789], ...}
        try:
            data = {(self.name, int(k)): LaserInfo(**v) for k, v in json.loads(answer).items()}
            self.data.update(data)
        except:
            logging.getLogger(__name__).error(
                "Error {} accessing wavemeter {} at '{}'".format(answer, self.name, self.url))
        QtCore.QTimer.singleShot(0, self.getWavemeterData)
        reply.finished.disconnect()  # necessary to make reply garbage collectable
        reply.error.disconnect()
        reply.deleteLater()
        del reply
        self.firebare(data=self.data)


class LockStatus(Enum):
    Unlocked = 0
    NoData = 1
    Transient = 2
    Locked = 3


class InterlockChannel(Observable):
    def __init__(self, name=None, wavemeter=None, channel=None, minimum=None, maximum=None, useServerInterlock=False,
                 contextSet=set(), enabled=False):
        super(InterlockChannel, self).__init__()
        self.wavemeter = wavemeter
        self.channel = channel
        self.minimum = minimum
        self.maximum = maximum
        self.useServerInterlock = useServerInterlock
        self.contextSet = contextSet
        self.currentFreq = None
        self.timestamp = datetime.utcfromtimestamp(0)
        self.currentState = LockStatus.NoData
        self.serverInRange = False
        self.serverRangeActive = False
        self.serverActive = False
        self.enabled = enabled
        self.name = name
        self.unlockedCount = 0  # counts how often the reading was out

    def __setstate__(self, state):  # is called when an older version InterlockChannel is unpickled
        super(InterlockChannel, self).__init__()
        self.wavemeter = None
        self.channel = state.get('channel')
        self.minimum = state.get('min')
        self.maximum = state.get('max')
        self.useServerInterlock = False
        self.contextSet = set()
        self.currentFreq = None
        self.timestamp = datetime.utcfromtimestamp(0)
        self.currentState = LockStatus.NoData
        self.serverInRange = False
        self.serverRangeActive = False
        self.serverActive = False
        self.enabled = state.get('enable')
        self.name = None
        self.unlockedCount = 0  # counts how often the reading was out

    def __repr__(self):
        return "<InterlockChannel {} {}:{}, {}-{}>".format(self.name, self.wavemeter, self.channel, self.minimum,
                                                          self.maximum)

    def __reduce__(self):
        # print(self)
        return InterlockChannel, (self.name, self.wavemeter, self.channel, self.minimum, self.maximum,
                                  self.useServerInterlock, self.contextSet, self.enabled)

    def update(self, cd):
        now = datetime.utcnow()
        if cd:
            self.serverActive = cd.active
            if cd.active:
                self.currentFreq = Q(cd.freq, 'GHz')
                self.timestamp = cd.time
                self.serverInRange = cd.interlock_inrange
                self.serverRangeActive = cd.interlock_enabled
        oldstate = self.currentState
        if now - self.timestamp > timedelta(seconds=20) or not self.serverActive:
            self.currentState = LockStatus.NoData
        else:
            if self.useServerInterlock and self.serverRangeActive:
                self.currentState = LockStatus.Locked if self.serverInRange else LockStatus.Unlocked
            else:
                if (self.minimum is not None and self.currentFreq < self.minimum or
                                self.maximum is not None and self.currentFreq > self.maximum):
                    self.unlockedCount += 1
                else:
                    self.unlockedCount = 0
                if self.unlockedCount == 0:
                    self.currentState = LockStatus.Locked
                elif self.unlockedCount < 2:
                    self.currentState = LockStatus.Transient
                else:
                    self.currentState = LockStatus.Unlocked
        self.firebare(wavemeter=self.wavemeter, channel=self.channel)
        return oldstate != self.currentState


class Interlock:
    def __init__(self, wavemeters, config):
        self.wavemeters = wavemeters
        self.pollers = [WavemeterPoll(name, url) for name, url in wavemeters.items()]
        self.contexts = defaultdict(set)  # context: set(InterlockChannel, ...)
        self.observables = defaultdict(Observable)  # keys are contexts
        self.config = config
        self.channels = config.get("InterlockChannels", list())  # contains all channels
        for p in self.pollers:
            p.subscribe(self.onData)
            self._data = dict()
        self._updateChannels()

    def saveConfig(self):
        self.config["InterlockChannels"] = self.channels

    def _updateChannels(self):
        """Keep the self.contexts populated"""
        for ch in self.channels:
            for c in ch.contextSet:
                self.contexts[c].add(ch)

    def subscribe(self, callback, context=None, unique=False):
        self.observables[context].subscribe(callback, unique)
        self.contexts[context]

    def createContext(self, context):
        self.observables[context]  # touch the defaultdict
        self.contexts[context]

    def contextStatus(self, context):
        channels = self.contexts.get(context)
        if channels is None:
            return LockStatus.NoData
        l = [c.currentState.value for c in channels if c.enabled]
        return LockStatus(min(l)) if l else LockStatus.Locked

    def onData(self, data):
        # print(data)
        changedContexts = set()
        for channel in self.channels:
            d = data.get((channel.wavemeter, channel.channel))
            if not d: continue
            changed = channel.update(d)
            if changed:
                changedContexts.update(channel.contextSet)
        for c in changedContexts:
            status = self.contextStatus(c)
            self.observables[c].firebare(c, status)
            self.observables[None].firebare(c, status)



