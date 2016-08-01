# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

## This class defines the mode variable which is used as
#  an enumerated typedef.
class Mode(object):
    ## The Finite mode is a mode where a finite number of
    #  samples are generated.
    #  Default value:  0.
    Finite = 0

    ## The Continuous mode is a mode where a set of samples
    #  are continuously repeated.  They samples are repeared
    #  until the stop() method is called.
    #  Default value: 1.
    Continuous = 1

    ## The Static mode is a mode where only one sample is
    #  generated.
    #  Default Value: 2.
    Static = 2
    
## This class defines the trigger type variable which is
#  used as an enumerated typedef.
class TriggerType(object):
    ## The Software trigger type is used when a single
    #  software command starts the signal generation.
    #  Default value: 0.
    Software = 0

    ##  The Hardware trigger types is used when a start trigger
    #  is utilized to start the signal generation.
    #  A software command may still be used to start the generation.
    #  However, that command will set the generator to wait for a 
    #  trigger such that all signal are synchronized.
    #  Defualt value: 1 
    Hardware = 1

