# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

class AttributeRedirector(object):
    """redirect attributes to an attribute object within the object"""
    def __init__(self, targetobject, attrname, defaultval=None ):
        """redirect attribute to an attribute "attrname" of object of this instance with name targetobject
        if defaultval is not None and the attribute is not found, set the attribute to defaultval"""
        self.targetobject = targetobject
        self.attrname = attrname
        self.defaultval = defaultval
        
    def __get__(self, instance, owner):
        try:
            val = instance.__dict__[self.targetobject].__dict__[self.attrname]
            return val
        except AttributeError as e:
            if self.defaultval is not None:
                instance.__dict__[self.targetobject].__dict__[self.attrname] = self.defaultval
                return self.defaultval
            raise e
    
    def __set__(self, instance, value):
        instance.__dict__[self.targetobject].__dict__[self.attrname] = value
