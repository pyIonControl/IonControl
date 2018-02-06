# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

class Event(object):
    pass

class Observable(object):
    def __init__(self):
        self.callbacks = []
        
    def subscribe(self, callback, unique=False):
        if unique:
            if callback not in self.callbacks:
                self.callbacks.append(callback)
        else:
            self.callbacks.append(callback)
        
    def unsubscribe(self, callback):
        self.callbacks.pop( self.callbacks.index(callback) )
        
    def clear(self):
        self.callbacks = []
        
    def fire(self, **attrs):
        e = Event()
        e.source = self
        for k, v in attrs.items():
            setattr(e, k, v)
        for fn in self.callbacks:
            fn(e)

    def firebare(self, *args, **kwargs):
        for fn in self.callbacks:
            fn(*args, **kwargs)


