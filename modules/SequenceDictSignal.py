# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
# A list that also works as a dict
from operator import itemgetter
import copy
from PyQt5 import QtCore
from .SequenceDict import SequenceDict

class SignalObject(QtCore.QObject):
    dataChanged = QtCore.pyqtSignal()

class SequenceDictSignal(SequenceDict):

    def __init__(self, *args, **kwds):
        self.signalObject = SignalObject()
        self.dataChanged = self.signalObject.dataChanged
        SequenceDict.__init__(self, *args, **kwds)
        
    __hash__ = SequenceDict.__hash__

    def clear(self):
        SequenceDict.clear(self)
        self.dataChanged.emit()

    def __setitem__(self, key, value):
        SequenceDict.__setitem__(self, key, value)
        self.dataChanged.emit()
        
    def insert(self, index, key, value):
        SequenceDict.insert(self, index, key, value)
        self.dataChanged.emit()

    def __delitem__(self, key):
        SequenceDict.__delitem__(self, key)
        self.dataChanged.emit()

    __iter__ = SequenceDict.__iter__
    __reversed__ = SequenceDict.__reversed__
    
    def renameAt(self, index, new):
        SequenceDict.renameAt(self, index, new)
        self.dataChanged.emit()
        
    def popitem(self):
        SequenceDict.popitem(self)
        self.dataChanged.emit()

    def popAt(self, index):
        SequenceDict.popAt(self, index)
        self.dataChanged.emit()

    __reduce__ = SequenceDict.__reduce__
    __repr__ = SequenceDict.__repr__
    __eq__ = SequenceDict.__eq__
    
    def setAt(self, index, value):
        SequenceDict.setAt(self, index, value)
        self.dataChanged.emit()
    
    def sort(self, key=itemgetter(0), reverse=False):
        SequenceDict.sort(self, key, reverse)
        self.dataChanged.emit()
        
    def sortByAttribute(self, attribute, reverse=False):
        SequenceDict.sortByAttribute(self, attribute, reverse)
        self.dataChanged.emit()
    
    def swap(self, index1, index2):
        SequenceDict.swap(self, index1, index2)
        self.dataChanged.emit()
        
    def sortToMatch(self, keylist):
        SequenceDict.sortToMatch(self, keylist)
        self.dataChanged.emit()
            
    __deepcopy__ = SequenceDict.__deepcopy__
        
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    d = SequenceDictSignal([(4, 4), (1, 1), (2, 2), (3, 3)])
    print(list(d.items()))
    print(list(d.items()))
    e = copy.deepcopy(d)
    print(list(e.items()))
    
    
    