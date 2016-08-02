# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import visa

class VisaInstrument(object):
    def __init__(self, **kwargs):
        self.inst = None
        pass

    def query(self, command):
        pass

    def write(self, command):
        pass

    def close(self):
        pass

    def __del__(self):
        self.close()
