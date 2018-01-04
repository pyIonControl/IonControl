from collections import OrderedDict
import unittest
import hashlib

from modules.hasher import Hasher


class Alpha:
    def __init__(self):
        self.a = 42

    def __getstate__(self):
        return self.__dict__


class Beta:
    def __init__(self):
        self.a = 43

    def __getnewargs_ex__(self):
        return (self.a, {'value': self.a, 'other': 43})

class Gamma:
    def __init__(self):
        self.a = 43

    def __getnewargs__(self):
        return (self.a)

class Delta:
    def __init__(self):
        self.a = 43

    def __reduce_ex__(self, protocol):
        return getEpsilon, (1, 2, 3), {4: 5, 6:7}, iter([range(5)]), iter([(i, i*i) for i in range(20)])

def getEpsilon(args):
    return Epsilon()

class Epsilon:
    def __init__(self):
        self.a = 43

    def __reduce__(self):
        return getEpsilon, (1, 2, 3), {4: 5, 6:7}, iter([range(5)]), iter([(i, i*i) for i in range(20)])

class Theta:
    def __init__(self):
        self.a = 43



class HasherTest(unittest.TestCase):
    def test_basic(self):
        h = Hasher(hashlib.sha256)
        h.update(1)
        h.update(1.2)
        h.update('Peter')
        h.update(b'Peter')
        h.update(None)
        h.update(True)
        h.update(False)
        h.update(1 + 1j)
        self.assertEqual(h.hexdigest(), "113d6319a605d95c70ca2dc291c03fb87d72f7c98502c706c03e52c9d6035d27")

    def test_list_tuple(self):
        h = Hasher(hashlib.sha256)
        h.update((1, 2, 3))
        h.update((1.2, 2.5, 7))
        h.update(['Peter', 3, 5.7])
        h.update(bytearray(b'Peter'))
        self.assertEqual(h.hexdigest(), "576ad0bee72cc58ba5a717bb2d86742d075076af284f2bf74ad09bd90e6f1163")

    def test_dict_set(self):
        d = [(i, i * i) for i in range(20)]
        h = Hasher(hashlib.sha256)
        h.update(dict(d))
        h.update(OrderedDict(d))
        h.update(set(d))
        self.assertEqual(h.hexdigest(), "789eb6aa8e93f721b0933795ee9bfb4c43eebc32dd29f4c7c1693002bf432259")

    def test_class(self):
        h = Hasher(hashlib.sha256)
        h.update(Alpha())
        h.update(Beta())
        h.update(Gamma())
        h.update(Delta())
        h.update(Epsilon())
        h.update(Theta())
        self.assertEqual(h.hexdigest(), "90b9deac66bcaaf8394056355d4bb003486bdb1d7187c628ae5ea95ad6604bac")


if __name__ == "__main__":
    unittest.main()
