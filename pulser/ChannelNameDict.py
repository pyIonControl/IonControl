# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import ChainMap


class ChannelNameDict( ChainMap ):
    def __init__(self, CustomDict=None, DefaultDict=None ):
        super(ChannelNameDict, self).__init__( CustomDict if CustomDict is not None else dict(), DefaultDict if DefaultDict is not None else dict())
        self._inverse = dict((value, key) for key, value in self.items())

    def __setstate__(self, state):
        self.__dict__ = state
        self._inverse = dict((value, key) for key, value in self.items())

    @property
    def defaultDict(self):
        return self.maps[1]
    
    @defaultDict.setter
    def defaultDict(self, defaultDict ):
        self.maps[1] = defaultDict
    
    @property
    def customDict(self):
        return self.maps[0]

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._inverse[value] = key

    def channel(self, name):
        return self._inverse[name]