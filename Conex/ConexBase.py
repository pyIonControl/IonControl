# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os.path
import sys

conex_dirs = [r'C:\Program Files\Newport\MotionControl\CONEX-CC\Bin',
              r'C:\Program Files (x86)\Newport\MotionControl\CONEX-CC\Bin']

class ConexError(Exception):
    pass

for d in conex_dirs:
    if os.path.isdir(d):
        sys.path.append(d)
        break
else:
    raise ConexError("Newport Conex libraries not found in '{0}'".format("', '".join(conex_dirs)))

# import python for .NET
import clr   #@UnresolvedImport
# Add reference to assembly and import names from namespace
assembly = "Newport.CONEXCC.CommandInterface"
if clr.FindAssembly(assembly):
    clr.AddReference(assembly)  # add reference if found
else:
    raise ImportError("Newport Conex libraries: Unable to load '{0}' DLL".format(assembly))

from CommandInterfaceConexCC import *
import System

