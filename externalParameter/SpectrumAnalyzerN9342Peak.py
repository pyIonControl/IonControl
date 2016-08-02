# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import visa   #@UnresolvedImport
from modules.AttributeRedirector import AttributeRedirector
import logging
from modules.quantity import Q


class Settings:
    pass

class SpectrumAnalyzerN9342Peak(object):
    @staticmethod
    def connectedInstruments():
        rm = visa.ResourceManager()
        return [name for name in rm.list_resources() if name.find('COM')!=0 ]

    def __init__(self, instrument=0, timeout=1, settings=None):
        self.settings = settings if settings is not None else Settings()
        self.instrument = instrument
        self.timeout = timeout
        self.conn = None
        self.setDefaults()
        
    def setDefaults(self):
        self.settings.__dict__.setdefault('timeout', Q(500, 'ms'))
        self.settings.__dict__.setdefault('measureSeparation', Q(500, 'ms'))

    def open(self):
        self.rm = visa.ResourceManager()
        self.conn = self.rm.open_resource( self.instrument, timeout=self.timeout)
        self.conn.write(':CALCulate:MARKer1:CPEak ON')
       
    measureSeparation = AttributeRedirector( "settings", "measureSeparation" )
    timeout = AttributeRedirector( "settings", "timeout" )        
    
    def close(self):
        self.conn.close()
        
    def value(self):
        try:
            reply = self.conn.query(":CALCulate:MARKer1:Y?")
            result = float(reply)
        except Exception as e:
            logging.getLogger(__name__).error("Error reading from Spectrum Analyzer: reply: '{0}', exception: {1}".format(reply, str(e)))
            print("Error reading from Spectrum Analyzer: reply: '{0}', exception: {1}".format(reply, str(e)))
            raise
        return result
    
    @property
    def waitTime(self):
        return self.settings.measureSeparation.m_as('s')

    def paramDef(self):
        return [{'name': 'timeout', 'type': 'magnitude', 'value': self.timeout, 'tip': "wait time for communication", 'field': 'timeout'},
                {'name': 'measure separation', 'type': 'magnitude', 'value': self.measureSeparation, 'tip': "time between two reading", 'field': 'measureSeparation'}]

    

