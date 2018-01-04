import inspect


class Hasher(object):
    """Hashes Python data into md5."""
    def __init__(self, digest):
        self.digest = digest()

    def update(self, v):
        """Add `v` to the hash, recursively if needed."""
        self.digest.update(str(type(v)).encode())
        if isinstance(v, str):
            self.digest.update(v.encode())
        elif isinstance(v, (bytes, bytearray)):
            self.digest.update(v)
        elif v is None or isinstance(v, (int, float, bool, complex)):
            self.digest.update(repr(v).encode())
        elif isinstance(v, (tuple, list)):
            for e in v:
                self.update(e)
        elif isinstance(v, set):
            for e in sorted(v):
                self.update(e)
        elif isinstance(v, dict):
            for key, val in sorted(v.items()):
                self.update(key)
                self.update(val)
        elif isinstance(v, type):
            self.digest.update(str(v).encode())
        elif hasattr(v, '__getstate__'):
            self.update(v.__getstate__())
        elif hasattr(v, '__getnewargs_ex__'):
            self.update(v.__getnewargs_ex__())
        elif hasattr(v, '__getnewargs__'):
             self.update(v.__getnewargs__())
        elif hasattr(v, '__reduce_ex__'):
             tocall, *args = v.__reduce_ex__(0)
             self.digest.update(tocall.__name__.encode())
             self.update(args)
        elif hasattr(v, '__reduce__'):
             tocall, *args = v.__reduce_ex__(0)
             self.digest.update(tocall.__name__.encode())
             self.update(args)
        else:
            for k in sorted(dir(v)):
                if k.startswith('__'):
                    continue
                a = getattr(v, k)
                if inspect.isroutine(a):
                    continue
                self.update(k)
                self.update(a)

    def digest(self):
        """Retrieve the digest of the hash."""
        return self.digest.digest()

    def hexdigest(self):
        return self.digest.hexdigest()

def hexdigest(obj, algo):
    h = Hasher(algo)
    h.update(obj)
    return h.hexdigest()

def digest(obj, algo):
    h = Hasher(algo)
    h.update(obj)
    return h.digest()
