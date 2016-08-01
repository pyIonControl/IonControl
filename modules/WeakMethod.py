# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
# File weakmethod.py
import weakref 


class ref(object):
    """Wraps any callable, most importantly a bound method, in
    a way that allows a bound method's object to be GC'ed, while
    providing the same interface as a normal weak reference"""
    def __init__(self, fn):
        try:
            o, f, c = fn.__self__, fn.__func__, fn.__self__.__class__
        except AttributeError:
            self._obj = None
            self._func = fn
            self._class = None
        else:
            if o is None:
                self._obj = None
            else:
                self._obj = weakref.ref(o)
            self._func = f
            self._class = c
            
    def __call__(self, *args, **kwargs):
        if self._obj is None:
            return self._func(*args, **kwargs)
        else:
            obj = self._obj()
            return self._func.__get__( obj, self._class )(*args, **kwargs) if obj is not None else None
        
    @property
    def bound(self):
        return self._obj is None or self._obj() is not None
        
