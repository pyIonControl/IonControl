# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from modules import WeakMethod
from functools import partial
import weakref

class C(object):
    def f(self, test=None):
        return test if test else 42


class TestWeakMethod(unittest.TestCase):
    def test_calling(self):
        c = C()
        r = WeakMethod.ref(c.f)
        self.assertEqual(r(), 42)

    def test_with_partial(self):
        c = C()
        r = partial(WeakMethod.ref(c.f), test=4242)
        self.assertEqual(r(), 4242)

    def test_release(self):
        c = C()
        r = WeakMethod.ref(c.f)
        del c
        self.assertFalse(r.bound)

    def test_release_2(self):
        c = C()
        r = WeakMethod.ref(c.f)
        self.assertEqual(r(), 42)
        s = weakref.WeakSet()
        s.add(c)
        del c
        self.assertEqual(len(s), 0)