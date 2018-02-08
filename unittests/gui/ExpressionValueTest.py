# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import copy

from gui.ExpressionValue import ExpressionValue
from modules.quantity import Q
import unittest
import pickle

globalDict = {'test': Q(123,'Hz')}

class ExpressionValueTest(unittest.TestCase):
    def testPickle(self):
        expr = ExpressionValue(name='Count 3', value=Q(12, 'kHz'))
        pickled = pickle.dumps(expr)
        unpickled = pickle.loads(pickled)
        self.assertEqual(expr, unpickled)

    def testdeepcopy(self):
        expr = ExpressionValue(name='Count 3', value=Q(12, 'kHz'), globalDict=globalDict)
        c = copy.deepcopy(expr)
        self.assertEqual(expr, c)

if __name__ == "__main__":
    unittest.main()