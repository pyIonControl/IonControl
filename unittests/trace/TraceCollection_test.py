import unittest

from trace.TraceCollection import TraceCollection


class TraceCollection_test(unittest.TestCase):
    def load_file(self):
        tc = TraceCollection()
        tc.loadTrace('MyScan_002.hdf5')
        tc.structuredData['test.json'] = list(range(20))
        tc.saveZip('MyScan_002.zip')
        tc.save('text')




if __name__ == "__main__":
    unittest.main()
