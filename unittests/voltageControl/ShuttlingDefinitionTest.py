# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from voltageControl.ShuttlingDefinition import ShuttleEdge

class ShuttlingDefinitionTest(unittest.TestCase):
    def testShuttleEdge(self):
        e = ShuttleEdge(startLine=0, stopLine=20)
        self.assertEqual(list(e.iLines()), list(range(21)))

    def testShuttleEdgeInverse(self):
        e = ShuttleEdge(startLine=20, stopLine=0)
        self.assertEqual(list(e.iLines()), list(range(20, -1, -1)))

    def testShuttleEdgeLinStartStop(self):
        e = ShuttleEdge(startLine=0, stopLine=20)
        e.startType = "Linear"
        e.stopType = "Linear"
        e.startLength = 3
        e.stopLength = 3
        print(list(e.iLines()))

    def testShuttleEdgeLinStartStopInverse(self):
        e = ShuttleEdge(startLine=20, stopLine=0)
        e.startType = "Linear"
        e.stopType = "Linear"
        e.startLength = 3
        e.stopLength = 3
        print(list(e.iLines()))

    def testShuttleEdgeSinSqStartStop(self):
        e = ShuttleEdge(startLine=0.15, stopLine=20.15)
        e.startType = "Sine square"
        e.stopType = "Sine square"
        e.startLength = 3
        e.stopLength = 3
        print(list(e.iLines()))

        ie = ShuttleEdge(startLine=20.15, stopLine=0.15)
        ie.startType = "Sine square"
        ie.stopType = "Sine square"
        ie.startLength = 3
        ie.stopLength = 3
        print(list(ie.iLines()))

    def testShuttleEdgeSinSqStartStop2(self):
        e = ShuttleEdge(startLine=0.15, stopLine=20.15)
        e.startType = "Sine square"
        e.stopType = "Sine square"
        e.startLength = 3
        e.stopLength = 3
        print(list(e.iLines()))

        ie = ShuttleEdge(startLine=20.15, stopLine=0.15)
        ie.startType = "Sine square"
        ie.stopType = "Sine square"
        ie.startLength = 3
        ie.stopLength = 3
        print(list(ie.iLines()))


if __name__ == "__main__":
    unittest.main()