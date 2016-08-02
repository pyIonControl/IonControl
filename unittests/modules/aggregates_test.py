# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from modules.aggregates import min_iterable, max_iterable


class Descriptor_test(unittest.TestCase):
    def test_min_iterable(self):
        self.assertEqual(min_iterable(range(5, 10)), 5)
        self.assertEqual(min_iterable(tuple()), None)

    def test_max_iterable(self):
        self.assertEqual(max_iterable(range(5, 10)), 9)
        self.assertEqual(max_iterable(tuple()), None)


if __name__ == "__main__":
    unittest.main()
