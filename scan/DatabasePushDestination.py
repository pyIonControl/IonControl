# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from externalParameter.persistence import DBPersist
import time
from modules.quantity import is_Q

class DatabasePushDestination:
    def __init__(self, space):
        self.persist = DBPersist()
        self.space = space
    
    def update(self, pushlist, upd_time=None ):
        upd_time = time.time() if upd_time is None else upd_time
        for _, variable, value in pushlist:
            if is_Q(value):
                value, unit = value.m, "{:~}".format(value.units)
            else:
                unit = None
            self.persist.persist(self.space, variable, upd_time, value, unit)
    
    def keys(self):
        return (source for (space, source) in list(self.persist.sourceDict().keys()) if space == self.space) 

