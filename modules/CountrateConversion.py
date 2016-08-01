# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
converting count rates between different units

This way of switching between conversion functions is certainly premature optimization.
Thus I will see it as an excercise in function pointers

"""
from modules.AttributeComparisonEquality import AttributeComparisonEquality


def kHz(count, time_ms):
    return count/time_ms
    
def Hz(count, time_ms):
    return count*1000./time_ms
    
def MHz(count, time_ms):
    return count/1000./time_ms
    
def rawcount(count, time_ms):
    return count
    
def convertFunction(unit):
    return {
        0: (Hz, "Hz"),
        1: (kHz, "kHz"),
        2: (MHz, "MHz"),
        3: (rawcount, "") }[unit]
        
      
class DisplayUnit(AttributeComparisonEquality):
    def __init__(self,unit=0):
        self._unit = unit
        self.convert, self.name = convertFunction(unit)
        
    @property
    def unit(self):
        return self._unit
        
    @unit.setter
    def unit(self, unit):
        self._unit = unit
        self.convert, self.name = convertFunction(unit)
        
        

if __name__ == "__main__":
    import timeit

    def convert(unit, count, time_ms):
        return { 0: count/time_ms,
                 1: count*1000/time_ms,
                 2: count/1000./time_ms,
                 3: count}.get(unit)

    def test():
        u = DisplayUnit(0)
        for i in range(2, 10000):
            u.convert(i, i)
    
    def test2():
        for i in range(2, 10000):
            convert(i%4, i, i)
        
        
    t = timeit.Timer("test()", "from __main__ import test")
    time1 = t.timeit( number=1000)
    print("test()", time1)
    t2 = timeit.Timer("test2()", "from __main__ import test2")
    time2 = t2.timeit( number=1000)
    print("test2()", time2)
    print("ratio", time2/time1)
    