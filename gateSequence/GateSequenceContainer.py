# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os
from collections import OrderedDict
import operator

import xml.etree.ElementTree as etree

from pygsti.objects import GateString
from pygsti.io import load_gateset, load_gatestring_list


class GateSequenceOrderedDict(OrderedDict):
    pass

class GateSequenceException(Exception):
    pass

class GateSequenceContainer:
    def __init__(self, gateDefinition ):
        self.gateDefinition = gateDefinition
        self.GateSequenceDict = GateSequenceOrderedDict()
        self.GateSequenceAttributes = OrderedDict()
        self._usePyGSTi = False
        self.gateSet = None
        self.prep = None
        self.meas = None
        self.filename = None

    @property
    def usePyGSTi(self):
        return self._usePyGSTi

    @usePyGSTi.setter
    def usePyGSTi(self, use):
        self._usePyGSTi = use
        if not self._usePyGSTi and self.filename:
            self.loadXml(self.filename)
        else:
            pass

        
    def __repr__(self):
        return self.GateSequenceDict.__repr__()
    
    def loadXml(self, filename):
        self.filename = filename
        self.GateSequenceDict = GateSequenceOrderedDict()
        if filename is not None:
            tree = etree.parse(filename)
            root = tree.getroot()
            
            # load pulse definition
            for gateset in root:
                if gateset.text:
                    self.GateSequenceDict.update( { gateset.attrib['name']: list(map(operator.methodcaller('strip'), gateset.text.split(',')))} )
                else:  # we have the length 0 gate string
                    self.GateSequenceDict.update( { gateset.attrib['name']: [] } )
                self.GateSequenceAttributes.update( { gateset.attrib['name']: gateset.attrib })
            self.validate()
    
    """Validate the gates used in the gate sets against the defined gates"""            
    def validate(self):
        for name, gatesequence in self.GateSequenceDict.items():
            self.validateGateSequence( name, gatesequence )

    def validateGateSequence(self, name, gatesequence):
        for gate in gatesequence:
            self.validateGate(name, gate)
        return gatesequence

    def validateGate(self, name, gate):
        if gate not in self.gateDefinition.Gates:
            raise GateSequenceException( "Gate '{0}' used in GateSequence '{1}' is not defined".format(gate, name) )

    def loadGateSet(self, path):
        self.gateSet = load_gateset(path)

    def setPreparation(self, path_or_literal):
        if os.path.exists(path_or_literal):
            self.prep = load_gatestring_list(path_or_literal)
            return os.path.split(path_or_literal)[-1]
        self.prep = GateString(None, path_or_literal)
        return path_or_literal

    def setMeasurement(self, path_or_literal):
        if os.path.exists(path_or_literal):
            self.meas = load_gatestring_list(path_or_literal)
            return os.path.split(path_or_literal)[-1]
        self.meas = GateString(None, path_or_literal)
        return path_or_literal

    def setGerm(self, path_or_literal):
        if os.path.exists(path_or_literal):
            self.germs = load_gatestring_list(path_or_literal)
            return os.path.split(path_or_literal)[-1]
        self.germs = GateString(None, path_or_literal)
        return path_or_literal


if __name__=="__main__":
    from gateSequence.GateDefinition import GateDefinition
    gatedef = GateDefinition()
    gatedef.loadGateDefinition(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\StandardGateDefinitions.xml")    

    container = GateSequenceContainer(gatedef)
    container.loadXml(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\GateSequenceLongGSTwithInversion.xml")
    
    print(container)
    
    