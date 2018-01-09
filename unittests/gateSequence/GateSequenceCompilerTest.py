import unittest
from gateSequence.GateSequenceCompiler import GateSequenceCompiler

class GateSequenceCompilerTest(unittest.TestCase):
    def test_pack(self):
        data = list(range(12))
        packed = GateSequenceCompiler.packData(data, 4)
        self.assertEqual(packed, [0xba9876543210])
        data = list(range(16))*2 + [4, 2]
        packed = GateSequenceCompiler.packData(data, 4)
        self.assertEqual(packed, [0xfedcba9876543210, 0xfedcba9876543210, 0x24])

if __name__ == "__main__":
    unittest.main()