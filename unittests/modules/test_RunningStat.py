# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from modules import RunningStat
import random
import numpy

class TestRunningStat(unittest.TestCase):
    def test_mean(self):
        testdata = numpy.array([random.random() for _ in range(2000)])
        stat = RunningStat.RunningStat()
        for d in testdata:
            stat.add(d)
        self.assertAlmostEqual(stat.mean, numpy.mean(testdata), 14)
        self.assertEqual(stat.min, numpy.min(testdata))
        self.assertEqual(stat.max, numpy.max(testdata))
        self.assertAlmostEqual(stat.std, numpy.std(testdata), 14)

    def test_min(self):
        pass


