# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from time import sleep
import random
import logging

class DummyReader:
    def __init__(self, instrument=None, settings=None):
        self.readTimeout = 1
        logging.getLogger(__name__).info("Created class dummy")
        
    def open(self):
        pass
        
    def close(self):
        pass
                
    def value(self):
        sleep(self.readTimeout)
        value = random.gauss(1, 0.1)
        logging.getLogger(__name__).debug("dummy reading value {0}".format(value))
        return value
    
    
    