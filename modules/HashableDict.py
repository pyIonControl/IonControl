# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

class HashableDict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))