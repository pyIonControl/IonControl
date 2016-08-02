# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

def dictValueFind( dd, value ):
    try:
        return next((key for key, v in list(dd.items()) if v==value))
    except StopIteration:
        return None