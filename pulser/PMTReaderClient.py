# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from .PulserHardwareClient import PulserHardware
from .PMTReaderServer import PMTReaderServer

class PMTReader(PulserHardware):
    serverClass = PMTReaderServer
    def __init__(self):
        super(PMTReader, self).__init__()
        
