# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from modules.descriptor import SetterProperty
import unittest


class A:
    def __init__(self, a=1):
        self._a = a

    @SetterProperty
    def a(self, newa):
        self._a = newa

    @property
    def a2(self):
        return self._a * self._a


class Descriptor_test(unittest.TestCase):
    def test_SetterProperty(self):
        a = A()
        a.a = 12
        self.assertEqual(a.a2, 144)
        with self.assertRaises(AttributeError):
            c = a.a


if __name__ == "__main__":
    unittest.main()
