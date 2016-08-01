# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
# A list that also works as a dict
from collections import MutableMapping
from itertools import zip_longest
from operator import itemgetter
import copy

class SequenceDict(dict, MutableMapping):

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        if not hasattr(self, '_keys'):
            self._keys = []
        self.update(*args, **kwds)
        
    def __hash__(self):
        return hash(tuple(self.items()))

    def clear(self):
        del self._keys[:]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            self._keys.append(key)
        dict.__setitem__(self, key, value)
        
    def insert(self, index, key, value):
        if key not in self:
            self._keys.insert(index, key)
        else:
            self._keys.remove(key)
            self._keys.insert(index, key)            
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __iter__(self):
        return iter(self._keys)

    def __reversed__(self):
        return reversed(self._keys)
    
    def renameAt(self, index, new):
        """Rename the element given by its index
        >>> s = SequenceDict([(1,1),(2,2),(3,3),(4,4)])
        >>> s.renameAt(2, 20)
        >>> print(s)
        SequenceDict([(1, 1), (2, 2), (20, 3), (4, 4)])
        >>> s.renameAt(2, 20)
        >>> print(s)
        SequenceDict([(1, 1), (2, 2), (20, 3), (4, 4)])
        """
        if new in self:
            if self._keys[index]==new:
                return 
            else:
                raise KeyError('renameAt: "{0}" key already exists')
        dict.__setitem__(self, new, dict.pop(self, self._keys[index] ) )
        self._keys[index] = new
        
    def popitem(self):
        if not self:
            raise KeyError('dictionary is empty')
        key = self._keys.pop()
        value = dict.pop(self, key)
        return key, value

    def popAt(self, index):
        if not self:
            raise KeyError('dictionary is empty')
        key = self._keys.pop(index)
        value = dict.pop(self, key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        inst_dict.pop('_keys', None)
        return (self.__class__, (items,), inst_dict)

    setdefault = MutableMapping.setdefault
    update = MutableMapping.update
    pop = MutableMapping.pop
    keys = MutableMapping.keys
    values = MutableMapping.values
    items = MutableMapping.items

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self.items()))

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, SequenceDict):
            return all(p==q for p, q in  zip_longest(list(self.items()), list(other.items())))
        return dict.__eq__(self, other)
    
    def setAt(self, index, value):
        """return the element at position index
        >>> s = SequenceDict([(4,44),(2,22),(3,33),(1,11)])
        >>> print(s.at(2))
        33
        >>> s.setAt(2,333)
        >>> print(s.at(2))
        333
        >>> print(s[3])
        333
        """
        return dict.__setitem__(self, self._keys[index], value)

    def at(self, index):
        """return the element at position index
        >>> s = SequenceDict([(4,44),(2,22),(3,33),(1,11)])
        >>> print(s.at(2))
        33
        >>> print(s.at(0))
        44
        """
        return dict.__getitem__(self, self._keys[index])
    
    def keyAt(self, index):
        """return the key of the element at position index
        >>> s = SequenceDict([(4,44),(2,22),(3,33),(1,11)])
        >>> print(s.keyAt(2))
        3
        >>> print(s.keyAt(0))
        4
        """
        return self._keys[index]
    
    def sort(self, key=itemgetter(0), reverse=False):
        """sort the order by the given key
        >>> s = SequenceDict([(4,4),(2,2),(3,3),(1,1)])
        >>> s.sort()
        >>> print(s)
        SequenceDict([(1, 1), (2, 2), (3, 3), (4, 4)])
        >>> s.sort( reverse=True )
        >>> print(s)
        SequenceDict([(4, 4), (3, 3), (2, 2), (1, 1)])
        """
        temp = sorted( iter(self.items()), key=key, reverse=reverse )
        self._keys = [itemgetter(0)(t) for t in temp]
        
    def sortByAttribute(self, attribute, reverse=False):
        temp = sorted( iter(self.items()), key=lambda a: getattr(a[1], attribute), reverse=reverse )
        self._keys = [itemgetter(0)(t) for t in temp]
    
    def index(self, key):
        return self._keys.index(key)
    
    def swap(self, index1, index2):
        """Swap the two indexes given
        >>> s = SequenceDict([(1,1),(2,2),(3,3),(4,4)])
        >>> s.swap( 0, 3 )
        >>> print(s)
        SequenceDict([(4, 4), (2, 2), (3, 3), (1, 1)])
        """
        self._keys[index1], self._keys[index2] = self._keys[index2], self._keys[index1]
        
    def sortToMatch(self, keylist):
        """Sort the Sequence to match the order of the keys given in keylist
        keylist may contain additional keys that are not in the SequenceDict
        all keys of the SequenceDict must be in keylist
        >>> s = SequenceDict([(1,1),(2,2),(3,3),(4,4)])
        >>> s.sortToMatch( [4,1,7,2,3] )
        >>> print(s)
        SequenceDict([(4, 4), (1, 1), (2, 2), (3, 3)])
        """
        reverse = dict([ (value, index) for index, value in enumerate(keylist) ])
        self._keys = sorted( self._keys, key=lambda x: reverse.get(x, 1000000))
            
    def __deepcopy__(self, mode):
        new = type(self)()
        for key, value in self.items():
            new[key] = copy.deepcopy(value, mode)
        return new
    
    def __setdefault__(self, key, value):
        if key not in self:
            self._keys.append(key)
            dict.__setitem__(self, key, value)
        
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()
    d = SequenceDict([(4, 4), (1, 1), (2, 2), (3, 3)])
    print(list(d.items()))
    print(list(d.items()))
    e = copy.deepcopy(d)
    print(list(e.items()))
    
    import pickle
    s = pickle.dumps(d, 0)
    print('next is pickle.load')
    ud = pickle.loads(s)
    print('unpickled', ud)
    print(ud.at(1))
    
    
