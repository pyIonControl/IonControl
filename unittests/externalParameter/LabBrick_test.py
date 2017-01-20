# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from externalParameter.LabBrick import LabBrick, LabBrickInstrument, loadDll

loadDll(r"..\..\dll\vnx_fmsynth.dll")

class LabBrickTest(unittest.TestCase):
    def test_info(self):
        info = LabBrick.collectInformation()
        print(info)


if __name__ == "__main__":
    unittest.main()
