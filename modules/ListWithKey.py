# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

identity = lambda x: x
from collections import MutableMapping, MutableSequence

class ListWithKeyError(Exception):
    pass

class ListWithKey(MutableSequence):
    """
    List container with key and constant time lookup.
    The key of an element has to stay contant and may ONLY be changed via the updateKey fucntion.
    """
    def __init__(self, iterable=[], key=identity, setkey=None):
        """
        Construct ListWithKey
        :param iterable: iterable with initial list elements
        :param key:  a function where key(element) returns the desired key. Idenityty by default.
        :param setkey: a function that updates the key in an element and returns the updated element.
        :return:
        """
        self.list = list(iterable)
        self.lookup = dict((key(elem), index) for index, elem in enumerate(self.list))
        if len(self.lookup) != len(self.list):
            raise ListWithKeyError("keys are not unique")
        self.key = key
        self.setkey = setkey

    def __getitem__(self, index):
        return self.list.__getitem__(index)

    def __setitem__(self, index, value):
        elem = self.list[index]
        if self.key(value) != self.key(elem) and self.key(elem) in self.lookup:
            raise ListWithKeyError("keys are not unique")
        self.list.__setitem__(index, value)
        self.lookup.pop(self.key(elem))
        self.lookup[self.key(value)] = index

    def __delitem__(self, index):
        elem = self.list.pop(index)
        self.rebuildLookup()

    def __len__(self):
        return self.list.__len__()

    def insert(self, index, value):
        if self.key(value) in self.lookup:
            raise ListWithKeyError("keys are not unique")
        self.list.insert(index, value)
        self.lookup = dict((self.key(elem), index) for index, elem in enumerate(self.list))

    def mapping(self):
        """
        :return: MutableMapping with key(element), element pairs.
        Can be used to change the container elements
        """
        return ListWithKeyLookup(self)

    def sort(self, reverse=False):
        self.list.sort(key=self.key, reverse=reverse)
        self.rebuildLookup()

    def updateKey(self, index, newkey):
        """
        Update the key at the given index. Uses newelement = setkey(oldelement, newkey)
        :param index:
        :param newkey:
        :return: None
        """
        elem = self.list[index]
        oldkey = self.key(elem)
        if newkey != oldkey and newkey in self.lookup:
            raise ListWithKeyError("keys are not unique")
        self.list[index] = self.setkey(elem, newkey)
        self.lookup.pop(oldkey)
        self.lookup[newkey] = index

    def rebuildLookup(self):
        self.lookup.clear()
        self.lookup.update(dict((self.key(elem), index) for index, elem in enumerate(self.list)))

class ListWithKeyLookup(MutableMapping):
    """MutableMapping view of the ListWithKey container"""
    def __init__(self, listWithKey):
        self.listWithKey = listWithKey

    def __getitem__(self, key):
        return self.listWithKey[self.listWithKey.lookup[key]]

    def __iter__(self):
        return self.listWithKey.lookup.__iter__()

    def __len__(self):
        return self.listWithKey.__len__()

    def __setitem__(self, key, value):
        if key != self.listWithKey.key(value):
            raise ListWithKeyError("key must match key of value")
        position = self.listWithKey.lookup.get(key, None)
        if position is None:
            position = len(self.listWithKey)
            self.listWithKey.append(value)
        self.listWithKey.lookup[key] = position

    def __delitem__(self, key):
        index = self.listWithKey.lookup.pop(key)
        self.listWithKey.list.pop(index)


if __name__=="__main__":
    l = ListWithKey(list(range(50000)), setkey=lambda e, k: k)
    mapping = l.mapping()

    class example(object):
        def __init__(self, key):
            self.key = key

        def setkey(self, k):
            self.key = k
            return self

        def __repr__(self):
            return str(self.key)

    le = ListWithKey([example(i) for i in range(5000)], key=lambda e: e.key, setkey=example.setkey)
    print(le[300])
    le.updateKey(300, -300)
    print(le[300])
    m = le.mapping()
    print(m[-300])