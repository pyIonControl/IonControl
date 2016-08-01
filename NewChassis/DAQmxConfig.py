# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os
import sys
import platform

if sys.platform.startswith('win'):
    # Full path of the NIDAQmx.h file
    # Default location on Windows XP
    dot_h_file = r'C:\Program Files\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h'

    #if platform.release()=='7':
    if os.path.exists( r'C:\Program Files (x86)'):
        dot_h_file = r'C:\Program Files (x86)\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h'

    # Name (and eventually path) of the library
    # Default on Windows is nicaiu
    lib_name = "nicaiu"

elif sys.platform.startswith('linux'):
    # On linux you can use the command find_library('nidaqmx')

    # Full path of the NIDAQmx.h file
    dot_h_file = '/usr/local/natinst/nidaqmx/include/NIDAQmx.h'

    # Name (and eventually path) of the library
    lib_name = 'libnidaqmx.so'

elif sys.platform.startswith('cygwin'):
    dot_h_file = r'C:\Program Files\National Instruments\NI-DAQ\DAQmx ANSI C Dev\include\NIDAQmx.h'
    lib_name = "nicaiu"

else:
    raise NotImplementedError("Location of niDAQmx library and include file unknown on %s - if you find out, please let the PyDAQmx project know" % (sys.platform))
