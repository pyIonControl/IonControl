# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from modules.LRUCache import LRUCache

class TestLRUCache(unittest.TestCase):
    def test_simple(self):
        cache = LRUCache(12)
        origin = list()
        for i in range(12):
            cache[i] = i*i
            origin.append(i*i)
        result = [cache[i] for i in range(12)]
        self.assertEqual(origin, result)

    def test_over(self):
        cache = LRUCache(12)
        origin = list()
        for i in range(20):
            cache[i] = i * i
            origin.append(i * i)
        result = [cache[i] for i in range(8, 20)]
        self.assertEqual(origin[8:], result)

    def test_three(self):
        cache = LRUCache(12)
        origin = list()
        for i in range(20):
            cache[i] = i * i
            origin.append(i * i)
        result = [cache.get(i) for i in range(20)]
        self.assertEqual(origin[8:], result[8:])


