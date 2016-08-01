# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from modules.SequenceDict import SequenceDict
from copy import deepcopy

class CounterDictionary(SequenceDict):
    def __init__(self, *args, **kwargs):
        super(CounterDictionary, self).__init__(*args, **kwargs)
 
    def merge(self, variabledict, overwrite=False):
        # pop all variables that are not in the variabledict
        for var in list(self.values()):
            if var.name not in variabledict or variabledict[var.name].type != 'counter':
                self.pop(var.name)
        # add missing ones
        for var in list(variabledict.values()):
            if var.type == 'counter':
                if var.name not in self or overwrite:
                    self[var.name] = deepcopy(var)
        self.sortToMatch( list(variabledict.keys()) )
                        
        