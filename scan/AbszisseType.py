# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from enum import Enum


columnLookup = { 'time': 'timeTickFirst', 'x': 'x', 'index': 'indexColumn', 'first': 'timeTickFirst', 'last': 'timeTickLast' }

class AbszisseType(str, Enum):
    x = 'x'
    time = 'time'
    index = 'index'
    first = 'first'
    last = 'last'
        
    @property
    def columnName(self):
        return columnLookup.get( self.value )
    
    
if __name__=="__main__":
    print(AbszisseType.time.columnName)
    a = AbszisseType.time
    print(a.name)
    print(a.columnName)
