# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import time

from Conex.ConexBase import ConexCC, ConexError




class ConexInstrument:
    def __init__(self, instrumentKey=None):
        self.instrumentKey = instrumentKey
        self.address = 1
        self.controllerId = None
        self._position = None
        self._cc = None

    def open(self, instrumentKey=None):
        if instrumentKey is not None:
            self.instrumentKey = instrumentKey
        self._cc = ConexCC()
        retval = self._cc.OpenInstrument(self.instrumentKey)
        if retval != 0:
            raise ConexError("Newport Conex cannot open '{0}' returnvalue {1}".format(self.instrumentKey, retval))
        (self.controllerId,) = self.processReturn('ID_Get', self._cc.ID_Get(self.address, None, None))
        if self.isNotHomed:
            logging.getLogger(__name__).info("Newport conex home search {0}".format(self.instrumentKey))
            self.homeSearch()

    def processReturn(self, name, retval):
        if len(retval) < 2:
            return retval
        if retval[0] != 0:
            raise ConexError("Conex instrument {}: {}: {}".format(self.instrumentKey, name, retval[-1]))
        return retval[1:-1]

    def close(self):
        self._cc.CloseInstrument()

    def controllerVersion(self):
        (version,) = self.processReturn('controllerVersion', self._cc.VE(self.address, None, None))
        return version

    @property
    def position(self):
        number = 0.0
        (position,) = self.processReturn('read position', self._cc.TP(self.address, number, None))
        self._position = float(position)
        return self._position

    @position.setter
    def position(self, position=0.0):
        if self.isNotHomed:
            raise ConexError("Conex Instrument {0} is not ready to move. Try a home search.".format(self.instrumentKey))
        self.processReturn('write position', self._cc.PA_Set(self.address, position, None))
        self._position = position
        return self._position

    @property
    def status(self):
        return self.processReturn('status', self._cc.TS(self.address, None, None, None))

    @property
    def isSerchingHome(self):
        _, state = self.status
        return state == '1E'

    @property
    def isMotionRunning(self):
        _, state = self.status
        return state == '28'

    @property
    def isReadyToMove(self):
        _, state = self.status
        return state in ['32', '33', '34']

    @property
    def isNotHomed(self):
        _, state = self.status
        return state == '0A'

    def reset(self):
        self.processReturn('reset', self._cc.RS(self.address, None))

    def homeSearch(self):
        self.processReturn('homeSearch', self._cc.OR(self.address, None))

    def waitEndOfHomeSearch(self):
        while self.isSerchingHome:
            time.sleep(0.1)

    def waitEndOfMotion(self):
        while self.isMotionRunning:
            time.sleep(0.1)

