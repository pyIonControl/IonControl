# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
# The dictionary of External Instrument classes is maintained using a metaclass
# To define a new External Instrument you need to
# * define the class with a class attribute __metaclass__ = InstrumentMeta
# * import the module containing the class in this module
# * the dictionary of classes is InstrumentMeta.InstrumentDict

import logging

from . import StandardExternalParameter     #@UnusedImport
from .externalParameter import InterProcessParameters  #@UnusedImport

try:
    from . import MotionParameter  #@UnusedImport
except ImportError as ex:
    logging.getLogger(__name__).info("Newport motion control devices are not available: {0}".format(ex))
except Exception as ex:
    logging.getLogger(__name__).info("Newport motion control devices are not available")

try:
    from . import APTInstruments #@UnusedImport
except Exception as ex:
    logging.getLogger(__name__).info("Thorlabs APT devices are not available")
    
