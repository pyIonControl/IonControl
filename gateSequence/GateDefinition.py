# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from collections import OrderedDict
import logging

from lxml import etree


class Pulse(object):
    def __init__(self, name, pulsetype, encoding):
        self.name = name
        self.pulsetype = pulsetype
        self.encoding = encoding
        
    def __repr__(self):
        return "name: '{0}' pulsetype: '{1}' encoding: '{2}'".format(self.name, self.pulsetype, self.encoding)
        
class Gate(object):
    def __init__(self, name, pulsedict ):
        self.name = name
        self.pulsedict = pulsedict
        
    def __repr__(self):
        return "name: '{0}' pulsedict:{1}".format(self.name, self.pulsedict)


class GateDefinition(object):
    def __init__(self):
        self.PulseDefinition = OrderedDict()
        self.Gates = dict()
    
    @classmethod
    def from_file(cls, filename):
        g = cls()
        g.loadGateDefinition(filename)
        return g
        
    def loadGateDefinition(self, filename):
        self.PulseDefinition = OrderedDict()
        self.Gates = dict()
        if filename is not None:
            logger = logging.getLogger(__name__)
            tree = etree.parse(filename)
            root = tree.getroot()
            
            # load pulse definition
            PulseDefinitionElement = root.find("PulseDefinition")
            for pulse in PulseDefinitionElement:
                self.PulseDefinition.update( {pulse.attrib['name']: Pulse(pulse.attrib['name'], pulse.attrib['type'], pulse.text)} )
                
            logger.info( self.PulseDefinition ) 
            
            #load gate definitions
            GateDefinitionElement = root.find("GateDictionary")
            for gate in GateDefinitionElement:
                self.addGate( gate )
                        
    def addGate(self, element):
        pulsedict = list()
        for child in element:
            pulsedict.append( (child.attrib['name'], child.text) )
        self.Gates.update( { element.attrib['name']: Gate(element.attrib['name'], pulsedict)} )

    def printGates(self):
        logger = logging.getLogger(__name__)
        logger.info( "Gates defined:" )
        for gate in list(self.Gates.values()):
            logger.info( gate )
        
if __name__=="__main__":
    gatedef = GateDefinition()
    gatedef.loadGateDefinition(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\StandardGateDefinitions.xml")    
    gatedef.printGates()
    
