# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
class PowerSupply(object):
    def __init__(self, **kwargs):
        pass

    def init(self, **kwargs):
        pass

    def getVoltage(self, **kwargs):
        pass

    def setVoltage(self, voltage, **kwargs):
        pass

    def getCurrent(self, **kwargs):
        pass

    def setCurrent(self, current, **kwargs):
        pass

    def moveToVoltage(self, voltage, steps = 100, **kwargs):
        pass

    def close(self, **kwargs):
        pass
