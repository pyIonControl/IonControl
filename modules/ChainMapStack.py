# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from collections import ChainMap, deque

class ChainMapStack(ChainMap):
    """A small modification for chain maps in which the maps variable behaves like a stack"""
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.maps = deque()

    def push(self, x):
        self.maps.appendleft(x)

    def pop(self):
        return self.maps.popleft()
