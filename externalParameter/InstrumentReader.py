# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from .InstrumentLoggingReader import processReturn
from .InstrumentReaderBase import InstrumentReaderBase
from modules.Observable import Observable


def wrapInstrument(classname, serialclass):
    return type(classname, (InstrumentReader,),
                dict({"serialclass": serialclass,
                      "_outputChannels": serialclass._outputChannels if hasattr(serialclass, "_outputChannels") else {},
                      "_inputChannels": serialclass._inputChannels if hasattr(serialclass, "_inputChannels") else {},
                      "_channelParams": serialclass._channelParams if hasattr(serialclass, "_channelParams") else {}
                      }))

class InstrumentReader( InstrumentReaderBase ):
    def __init__(self, name, settings, globalDict, instrument ):
        child = self.serialclass(instrument=instrument, settings=settings)
        child.open()
        super( InstrumentReader, self ).__init__(name, settings, globalDict, child)
        self._inputChannels = {None: None}
         
    def close(self):
        self.commandQueue.put(("stop", ()) )
        processReturn( self.responseQueue.get() )
        self.reader.wait()

    @classmethod
    def connectedInstruments(cls):
        if hasattr( cls.serialclass, 'connectedInstruments' ):
            return cls.serialclass.connectedInstruments()
        return []
         
