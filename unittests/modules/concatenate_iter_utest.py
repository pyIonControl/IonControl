# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from modules import concatenate_iter
import unittest

class Concatenate_iter(unittest.TestCase):
    def testConcatenation(self):
        a = list(range(8))
        b = [8, 9]
        c = (10, 11, 12)
        d = list(range(20))[13:20]
        concat = [ i for i in concatenate_iter.concatenate_iter(a, b, c, d)]
        self.assertEqual( concat, list(range(20)))
        
    def testInterleaved(self):
        a = [1, 4, 7, 10]
        b = (2, 5, 8)
        c = [3, 6, 9, 'ignoreme']
        interleaved = [ i for i in concatenate_iter.interleave_iter(a, b, c)]
        self.assertEqual(interleaved, list(range(1, 11)))
        
if __name__ == "__main__":
    unittest.main()       