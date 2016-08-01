# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

def formatDelta(delta):
    """Return a string version of a datetime time difference object (timedelta),
       formatted as: HH:MM:SS.S. If hours = 0, returns MM:SS.S"""
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    hours += delta.days * 24
    seconds += delta.microseconds * 1e-6
    components = list()
    if (hours > 0): components.append("{0}".format(hours))
    components.append("{0:02d}:{1:04.1f}".format(int(minutes), seconds))
    return ":".join(components)