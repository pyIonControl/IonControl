# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import os
import pickle
from collections import OrderedDict
import operator
from pathlib import Path

from lxml import etree

from pygsti.objects import GateString
from pygsti.io import load_gateset, load_gatestring_list
from pygsti.construction import make_lsgst_structs

from modules.filetype import isXmlFile


def split(text):
    ''''Split a list if , are present it will use , as separator else whitespace'''
    if text.find(',')>=0:
        return map(operator.methodcaller('strip'), text.split(','))
    return text.split()


class GateSequenceException(Exception):
    pass


class GateSequenceContainer:
    def __init__(self, gateDefinition=None):
        self.gateDefinition = gateDefinition
        self._gate_string_list = None
        self._gate_string_struct = None
        self.GateSequenceAttributes = OrderedDict()
        self._usePyGSTi = False
        self.gateSet = None
        self.prep = None
        self.meas = None
        self.filename = None
        self.germs = None
        self.maxLengths = None

    @property
    def sequenceList(self):
        if self._usePyGSTi:
            return self._gate_string_struct.allstrs if self._gate_string_struct is not None else None
        else:
            return self._gate_string_list

    @property
    def usePyGSTi(self):
        return self._usePyGSTi

    @usePyGSTi.setter
    def usePyGSTi(self, use):
        self._usePyGSTi = use
        if not self._usePyGSTi and self.filename:
            self.load(self.filename)
        else:
            self.update_pyGSTi()

    def update_pyGSTi(self):
        if self.gateSet and self.prep and self.meas and self.germs and self.maxLengths:
            self._gate_string_struct = make_lsgst_structs(self.gateSet.gates.keys(), self.prep, self.meas,
                                                          self.germs, self.maxLengths)[-1]
        else:
            self._gate_string_struct = None

    def __repr__(self):
        return self.GateSequenceDict.__repr__()

    def load(self, filename):
        p = Path(filename)
        if p.suffix == ".pkl":
            self.loadPickle(filename)
        elif isXmlFile(filename):
            self.loadXml(filename)
        else:
            self.loadText(filename)

    def loadXml(self, filename):
        self._gate_string_struct = None
        self.filename = filename
        if not self._usePyGSTi and filename:
            self._gate_string_list = list()
            tree = etree.parse(filename)
            root = tree.getroot()
            # load pulse definition
            for gateset in root.findall("GateSequence"):
                text = gateset.text.strip()
                if text:
                    self._gate_string_list.append(GateString(None, text.translate({ord(','): None})))
                else:  # we have the length 0 gate string
                    self._gate_string_list.append(GateString(None, "{}"))
            self.validate()

    def loadText(self, filename):
        self._gate_string_struct = None
        self.filename = filename
        if not self._usePyGSTi and filename:
            self._gate_string_list = list()
            with open(filename) as f:
                for text in f:
                    self._gate_string_list.append(GateString(None, text.strip()))
            if self.gateSet:
                self.validate()

    def savePickle(self, filename):
        with open(filename, "wb") as f:
            pickle.dump(self._gate_string_list, f, -1)

    def loadPickle(self, filename):
        self._gate_string_struct = None
        self.filename = filename
        if not self._usePyGSTi and filename:
            with open(filename, 'rb') as f:
                self._gate_string_list = pickle.load(f)
            if self.gateSet:
                self.validate()

    """Validate the gates used in the gate sets against the defined gates"""            
    def validate(self):
        for gatesequence in self._gate_string_list:
            basic_gates = set(self.gateSet.gates.keys())
            for gate in gatesequence:
                if gate not in basic_gates:
                    raise GateSequenceException(
                        "Gate '{0}' used in GateSequence is not defined".format(gate))

    def loadGateSet(self, path):
        try:
            self.gateSet = load_gateset(path)
        except Exception as e:
            logging.getLogger(__name__).warning("Error loading GateSet from '{}': {}".format(path, e))

    def setPreparation(self, path_or_literal):
        if os.path.exists(path_or_literal):
            self.prep = load_gatestring_list(path_or_literal)
            return os.path.split(path_or_literal)[-1]
        self.prep = [GateString(None, i) for i in split(path_or_literal)]
        self.update_pyGSTi()
        return path_or_literal

    def setMeasurement(self, path_or_literal):
        if os.path.exists(path_or_literal):
            self.meas = load_gatestring_list(path_or_literal)
            return os.path.split(path_or_literal)[-1]
        self.meas = [GateString(None, i) for i in split(path_or_literal)]
        self.update_pyGSTi()
        return path_or_literal

    def setGerms(self, path_or_literal):
        if os.path.exists(path_or_literal):
            self.germs = load_gatestring_list(path_or_literal)
            return os.path.split(path_or_literal)[-1]
        self.germs = [GateString(None, i) for i in split(path_or_literal)]
        self.update_pyGSTi()
        return path_or_literal

    def setLengths(self, literal):
        self.maxLengths = list(map(int, split(literal)))
        self.update_pyGSTi()
        return literal


if __name__=="__main__":
    from gateSequence.GateDefinition import GateDefinition
    gatedef = GateDefinition()
    gatedef.loadGateDefinition(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\StandardGateDefinitions.xml")    

    container = GateSequenceContainer(gatedef)
    container.loadXml(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\GateSequenceLongGSTwithInversion.xml")
    
    print(container)
    
    