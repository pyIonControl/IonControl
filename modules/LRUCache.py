import collections

class LRUCache(collections.MutableMapping):
    def __init__(self, capacity=128):
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
        self._cache = collections.OrderedDict()

    def __getitem__(self, key):
        try:
            item = self._cache.pop(key)
            self.hits += 1
            self._cache[key] = item
            return item
        except KeyError:
            self.misses += 1
            raise

    def __setitem__(self, key, value):
        try:
            self._cache.pop(key)
        except KeyError:
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)
        self._cache[key] = value

    def __delitem__(self, key):
        self._cache.__delitem__(key)

    def __iter__(self):
        return self._cache.__iter__()

    def __len__(self):
        return self._cache.__len__()