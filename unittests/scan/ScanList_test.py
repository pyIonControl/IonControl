import unittest

from modules.quantity import Q, to_Q
from scan.ScanList import scanspace


class ScanList_test(unittest.TestCase):
    def test_scanspace_units(self):
        start = Q(1, 'kHz')
        stop = Q(1100, ' Hz')
        s = list(scanspace(start, stop, 11))
        self.assertEqual(s[0], start)
        self.assertEqual(s[-1], stop)

    def test_scanspace(self):
        self.assertEqual(9, 9)
        self.assertEqual(None, None)


if __name__ == "__main__":
    unittest.main()
