# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from modules.SequenceDict import SequenceDict
from copy import deepcopy
import re

class ShutterDictionary(SequenceDict):
    def __init__(self, *args, **kwargs):
        super(ShutterDictionary, self).__init__(*args, **kwargs)
                    
    def merge(self, variabledict, overwrite=False):
        # pop all variables that are not in the variabledict
        for var, _ in list(self.values()):
            if var.name not in variabledict:
                self.pop(var.name)
        # add missing ones
        for name, var in variabledict.items():
            if var.type is not None:
                m = re.match("\s*shutter(?:\s+(\w+)){0,1}", var.type)
                if m and ( name not in self or overwrite):
                    mask = deepcopy(variabledict[m.group(1)]) if m.group(1) is not None and m.group(1) in variabledict else None
                    self[name] = (deepcopy(var), mask)
        self.sortToMatch( list(variabledict.keys()) )

                        
                    

