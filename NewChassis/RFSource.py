# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
## This is an interface class for any instrument that acts like an
## RF Source.  All classes that act like an RF Source should inherit
## from this class and over-write every method.
class RFSource(object):
    def __init__(self, **kwargs):
        pass

    def getFreq(self, **kwargs):
        pass

    def setFreq(self, freq, **kwargs):
        pass

    def getAmp(self, **kwargs):
        pass

    def setAmp(self, amp, **kwargs):
        pass

    def getPhase(self, **kwargs):
        pass

    def setPhase(self, phase, **kwargs):
        pass

    def init(self, **kwargs):
        pass

    def turnOn(self, **kwargs):
        pass

    def turnOff(self, **kwargs):
        pass

