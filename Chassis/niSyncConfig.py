# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os
import platform
import sys


# This file sets the path for the location of the niSync dll, which differs depending on the os.
# Windows XP: C:\Program Files\National Instruments\IVI Foundation\VISA\WinNT\Bin
# Widnows 7: C:\Program Files (x86)\IVI Foundation\VISA\WinNT\Bin
#
# The API reference documentation is in the following directory:
# C:\Program Files (x86)\IVI Foundation\VISA\WinNT\niSync
#
# Also distinguish between 32 bit python and 64 bit python
#

def is_python_64():
    return sys.maxsize > 2**32

if sys.platform.startswith('win'):
    lib_directory = r'C:\Program Files\IVI Foundation\VISA\WinNT\Bin'
    lib_directory += "//"

    if platform.release() == '7':
        if is_python_64():
                lib_directory = r'C:\Program Files\IVI Foundation\VISA\Win64\Bin'
                lib_directory += "\\"
        else:
            if sys.platform.endswith('32'):
                lib_directory = r'C:\Program Files\IVI Foundation\VISA\WinNT\Bin'
                lib_directory += "\\"
            else:
                lib_directory = r'C:\Program Files (x86)\IVI Foundation\VISA\WinNT\Bin'
                lib_directory += "\\"
            if os.path.exists(r'C:\Program Files (x86)'):
                lib_directory = r'C:\Program Files (x86)\IVI Foundation\VISA\WinNT\Bin'
                lib_directory += "\\"

    lib_name = "niSync"

    # if the DLL is not found, try the Windows\System32 directory (works on Windows 10 x64)
    if not os.path.isfile(os.path.join(lib_directory,lib_name+'.dll')):
        lib_directory = r'C:\Windows\System32'
        if not os.path.isfile(os.path.join(lib_directory, lib_name + '.dll')):
            raise FileNotFoundError

else:
    raise NotImplementedError("Location of niSync library unknown on %s." % (sys.platform))
