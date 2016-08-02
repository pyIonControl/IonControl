# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

def firstNotNone( *values ):
    """ Return the first argument in a list of arguments that is not None """
    for value in values:
        if value is not None:
            return value
    return None

