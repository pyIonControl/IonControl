#
#       Example of how to interface with voltage controls for the DAC. Because the voltage control needs
#       to compile data for shuttling or other operations, it might be necessary to send parametric data
#       to the local and global adjust settings in order to have a functional dependence that varies with
#       the line in the voltage file. This requires that a function be passed to a voltage parameter, and
#       for best performance, the default call on the function should yield a reasonable return value. In
#       other words, if you set the "Line" parameter in the voltage control GUI with a global variable
#       named "LineGlobal", a user function named "f" that is passed into a control field needs to have a
#       return value with no arguments passed that evaluates to line = LineGlobal. So f() should be equal
#       to f(LineGlobal) for best performance.
#

import math

@userfunc
def VoltageOscillation(amp, frequency, phase, offset, Line):
    """
    A parametrized voltage control parameter. This function returns a sin wave
    to a voltage adjust field that will apply an oscillating voltage in either
    a steady state or a shuttling solution.

    Args:
        amp (num): sine wave amplitude
        frequency (num): sine wave "frequency" with no units for use with Line
        phase (num): sine wave phase
        offset (num): offset to be added to final solution
        Line (num): Line corresponds to voltage line setting, must be passed as
                    a default to inner function for proper shuttling behavior

    Returns:
        function(line=Line)

    """
    def osc(line=Line):
        return amp*math.sin(line*frequency + phase) + offset
    return osc

@userfunc
def userVoltageArray(parentname, childname, Line):
    """Example of the voltageArray function for use in localAdjustVoltage fields.
       A function is passed to the gui which looks up the appropriate line when
       calculating shuttling data. The default display value is determined from
       the Line variable. This particular function looks up the value in a named
       trace and interpolates between the closest indices of the array corresponding
       to the voltage line."""
    def va(line=Line):
        left = int(math.floor(line))
        right = int(math.ceil(line))
        convexc = line - left
        return NamedTrace(parentname, childname, left)*(1-convexc) + \
               NamedTrace(parentname, childname, right)*convexc
    return va


