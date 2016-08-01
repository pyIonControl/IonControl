# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from modules.quantity import Q
import operator

class TestMagnitude(unittest.TestCase):
    def test_plus_minus(self):
        self.assertEqual(operator.sub(Q(3), 2), 1)
        self.assertEqual(Q(3) - 2, 1)
        self.assertEqual(Q(3) / 2, 1.5)
        self.assertEqual(3 / Q(2), 1.5)
        self.assertEqual(2 - Q(3), -1)
        self.assertEqual(operator.sub(2, Q(3)), -1)

