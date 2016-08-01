# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import wrapt


class SetterProperty(wrapt.ObjectProxy):
    def __init__(self, wrapped):
        super().__init__(wrapped)

    def __set__(self, obj, value):
        return self.__wrapped__(obj, value)

    def __get__(self, obj, type=None):
        raise AttributeError("attribute is write only")

