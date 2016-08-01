# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from modules import MagnitudeParser
import unittest

class MagnitudeParserTest(unittest.TestCase):
    def testValueExpression(self):
        print(MagnitudeParser.isValueExpression("0x123f"))
        print(MagnitudeParser.isValueExpression("123"))
        print(MagnitudeParser.isValueExpression("123 kHz2"))


if __name__ == "__main__":
    unittest.main()