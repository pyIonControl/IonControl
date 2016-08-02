# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from modules import decorators
from functools import lru_cache
import unittest

class A:
    pass

@lru_cache(maxsize=100)
def getA():
    return A()

@decorators.return_copy
@lru_cache(maxsize=100)
def getB():
    return A()


class Decorators_test(unittest.TestCase):
    def test_return_copy(self):
        self.assertEqual(id(getA()), id(getA()), "lru_cache expected to return same object")
        s = set(getB() for _ in range(10))
        ids = set(id(e) for e in s)
        self.assertEqual(len(ids), 10, "return_copy decorator should return a copy")

if __name__ == "__main__":
    unittest.main()