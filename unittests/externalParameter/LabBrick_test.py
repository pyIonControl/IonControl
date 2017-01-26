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
        self.assertNotEqual(len(info), 0, "No labbricks found")
        for key, data in info.items():
            instrument = LabBrick("_".join(map(str, key)))
            print("Model {}, serial {}, frequency {}, power {}, on {}".format(key[0], key[1], instrument.frequency, instrument.power, instrument.rfOn))
            centerFrequency = instrument.minFrequency / 2 + instrument.maxFrequency / 2
            instrument.frequency = instrument.minFrequency
            print("Model {}, serial {}, frequency {}, power {}, on {}".format(key[0], key[1], instrument.frequency, instrument.power, instrument.rfOn))
            instrument.power = 0
            print("Model {}, serial {}, frequency {}, power {}, on {}".format(key[0], key[1], instrument.frequency, instrument.power, instrument.rfOn))
            instrument.rfOn = False
            print("Model {}, serial {}, frequency {}, power {}, on {}".format(key[0], key[1], instrument.frequency, instrument.power, instrument.rfOn))
            instrument.rfOn = True
            print("Model {}, serial {}, frequency {}, power {}, on {}".format(key[0], key[1], instrument.frequency, instrument.power, instrument.rfOn))
            instrument.close()


if __name__ == "__main__":
    unittest.main()
