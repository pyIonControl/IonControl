# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from unittest import TestCase
from modules.dictutil import setdefault, subdict, getOrInsert


class TestDictutil(TestCase):
    def test_subdict(self):
        d = {1: 2, 3: 4, 5: 6, 7: 8, 9: 10}
        k = [1, 5]
        self.assertDictEqual(subdict(d, k), {1: 2, 5: 6})

    def test_setdefault(self):
        self.assertDictEqual(setdefault({1: 4, 2: 7, 5: 6},
                                        {1: 27, 7: 12, 9: 81}),
                             {1: 4, 2: 7, 5: 6, 7: 12, 9: 81})

    def test_getOrInsert(self):
        d = dict()
        self.assertEqual(getOrInsert(d, 123, 42),
                         42)
        self.assertDictEqual(d, {123: 42})
