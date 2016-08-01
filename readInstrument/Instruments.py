# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from . import Read_N9010A
from . import Read_E5100B
from . import Read_N9342CN

instrumentmap = {
    'N9342CN' : Read_N9342CN.N9342CN,
    'E5100B' : Read_E5100B.E5100B,
    'N9010A' : Read_N9010A.N9010A
}
