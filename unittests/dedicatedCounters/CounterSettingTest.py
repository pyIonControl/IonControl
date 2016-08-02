# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import copy
import pickle
import unittest

from dedicatedCounters.CounterSetting import CounterSetting
from modules.quantity import Q

class CounterSettingTest(unittest.TestCase):
    def testPickle(self):
        expr = CounterSetting(name='Count 7', minValue=Q(12, 'kHz'), maxValue=Q(123, 'kHz'))
        pickled = pickle.dumps(expr)
        unpickled = pickle.loads(pickled)
        self.assertEqual(expr, unpickled)

    def testdeepCopy(self):
        expr = CounterSetting(name='Count 7', minValue=Q(12, 'kHz'), maxValue=Q(123, 'kHz'))
        c = copy.deepcopy(expr)
        self.assertEqual(expr, c)

if __name__ == "__main__":
    unittest.main()