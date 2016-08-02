# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import wrapt
from copy import copy

@wrapt.decorator
def return_copy(wrapped, instance, args, kwargs):
    return copy(wrapped(*args, **kwargs))

