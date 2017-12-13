# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from modules.Expression import Expression
import logging
import lxml.etree as ElementTree
from modules.XmlUtilit import xmlEncodeAttributes, xmlParseAttributes


class PushVariable(object):
    expression = Expression()
    XMLTagName = "PushVariable"
    def __init__(self):
        self.push = False
        self.destinationName = None
        self.variableName = None
        self.definition = ""
        self.value = None
        self.minimum = ""
        self.maximum = ""
        self.strMinimum = None
        self.strMaximum = None
        self.valueValid = True
        self.minValid = True
        self.maxValid = True
        
    def __setstate__(self, s):
        self.__dict__ = s
        self.__dict__.setdefault( 'destinationName', None )
        self.__dict__.setdefault( 'variableName', None )
        self.__dict__.setdefault( 'strMinimum', None )
        self.__dict__.setdefault( 'strMaximum', None )
        self.__dict__.setdefault( 'valueValid', True )
        self.__dict__.setdefault( 'minValid', True )
        self.__dict__.setdefault( 'maxValid', True )
        
    stateFields = [ 'push', 'definition', 'destinationName', 'variableName', 'value', 'minimum', 'maximum', 'strMinimum', 'strMaximum', 'valueValid', 'minValid', 'maxValid'] 
        
    def exportXml(self, element):
        myElement = ElementTree.SubElement(element, self.XMLTagName )
        xmlEncodeAttributes( self.__dict__, myElement)
        return myElement
    
    @staticmethod
    def fromXmlElement( element, flat=False ):
        myElement = element if flat else element.find(PushVariable.XMLTagName)
        v = PushVariable()
        v.__dict__.update( xmlParseAttributes( myElement ) )
        return v
        
    def __eq__(self, other):
        return isinstance(other, self.__class__) and tuple(getattr(self, field) for field in self.stateFields)==tuple(getattr(other, field) for field in self.stateFields)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(getattr(self, field) for field in self.stateFields))

    def evaluate(self, variables=dict(), useFloat=False):
        if self.definition:
            try:
                self.value = self.expression.evaluate( self.definition, variables, useFloat=useFloat )
                self.valueValid = True
            except Exception as e:
                logging.getLogger(__name__).warning(str(e))
                self.valueValid = False
        if self.strMinimum:
            try:
                self.minimum = self.expression.evaluate( self.strMinimum, variables, useFloat=useFloat )
                self.minValid = True
            except Exception as e:
                logging.getLogger(__name__).warning(str(e))
                self.minValid = False               
        if self.strMaximum:
            try:
                self.maximum = self.expression.evaluate( self.strMaximum, variables, useFloat=useFloat )
                self.maxValid = True
            except Exception as e:
                logging.getLogger(__name__).warning(str(e))
                self.maxValid = False               
        
    def pushRecord(self, variables=None):
        if variables is not None:
            self.evaluate(variables)
        if (self.push and self.destinationName is not None and self.destinationName != 'None' and 
            self.variableName is not None and self.variableName != 'None' and self.value is not None):
            if ((not self.minimum or self.value >= self.minimum) and 
                (not self.maximum or self.value <= self.maximum)):
                return [(self.destinationName, self.variableName, self.value)], []
            else:
                logging.getLogger(__name__).warning("Result out of range, Not pushing {0} to {1}: {2} <= {3} <= {4}".format(self.variableName, self.destinationName, self.minimum, self.value, self.maximum))
                return [], [(self.destinationName, self.variableName)]
        else:
            if (self.push):
                logging.getLogger(__name__).warning("Not pushing {0} to {1}: {2} <= {3} <= {4}, push not fully specified".format(self.variableName, self.destinationName, self.minimum, self.value, self.maximum))
        return [], []
    
    @property
    def key(self):
        return (self.destinationName, self.variableName)

    @property
    def hasStrMinimum(self):
        return (1 if self.minValid else -1) if self.strMinimum is not None else 0

    @property
    def hasStrMaximum(self):
        return (1 if self.maxValid else -1) if self.strMaximum is not None else 0
    
    @property
    def valueStatus(self):
        return 1 if self.valueValid else -1
