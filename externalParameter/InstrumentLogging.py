# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from externalParameter.InstrumentReader import wrapInstrument
LoggingInstruments = dict()

try:
    from .MKSReader import MKSReader
    LoggingInstruments["MKS Vacuum Gauge"] = wrapInstrument( "MKSInstrumentReader", MKSReader)
except:
    logging.getLogger(__name__).info("MKS Vacuum gauge reader not available")
    
try:
    from .TerranovaReader import TerranovaReader
    LoggingInstruments["Ion Gauge"] = wrapInstrument( "TerranovaInstrumentReader", TerranovaReader)
except:
    logging.getLogger(__name__).info("Ion gauge reader not available")

try:
    from externalParameter.Keithley2010Reader import Keithley2010Reader
    LoggingInstruments['Keithley 2010'] = wrapInstrument("Keithley2010ReaderInstrumentReader", Keithley2010Reader)
except:
    logging.getLogger(__name__).info("Keithley 2010 reader not available")

try:
    from .MultiMeterReader import MultiMeterReader
    from .Keithley2010Reader import Keithley2010Reader
    from .ILX5900Reader import ILX5900Reader
    from .SpectrumAnalyzerN9342Peak import SpectrumAnalyzerN9342Peak
    LoggingInstruments['Multi Meter'] = wrapInstrument( "MultiMeterInstrumentReader", MultiMeterReader )
    LoggingInstruments['Keithley 2010'] = wrapInstrument( "Keithley2010ReaderInstrumentReader", Keithley2010Reader )
    LoggingInstruments['ILX-5900'] = wrapInstrument( "ILX5900InstrumentReader", ILX5900Reader )
    LoggingInstruments['N9342Peak'] = wrapInstrument( "SpectrumAnalyzerN9342PeakReader", SpectrumAnalyzerN9342Peak )
except:
    logging.getLogger(__name__).info("Multi Meter reader not available")



try:
    from .PhotodiodeReader import PhotoDiodeReader
    LoggingInstruments['Photodiode'] = wrapInstrument( "PhotodiodeInstrumentReader", PhotoDiodeReader )
except:
    logging.getLogger(__name__).info("Photodiode reader not available")

try:
    from .OmegaCN7500Reader import OmegaCN7500Reader
    LoggingInstruments["Oven set point"] = wrapInstrument( "OmegaCN7500InstrumentReader", OmegaCN7500Reader)
except:
    logging.getLogger(__name__).info("oven set point not available")
    
from .DummyReader import DummyReader
LoggingInstruments["Dummy"] = wrapInstrument( "DummyInstrumentReader", DummyReader ) 