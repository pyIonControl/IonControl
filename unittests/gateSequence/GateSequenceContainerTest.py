import pytest

from modules.timing import timing
from gateSequence.GateDefinition import GateDefinition
from gateSequence.GateSequenceContainer import GateSequenceContainer


def test_loadXml():
    gatedef = GateDefinition()
    gatedef.loadGateDefinition("GateDefinitionIndex.xml")
    c = GateSequenceContainer(gatedef)
    c.loadGateSet("IonTargetGateset.txt")
    c.loadXml("GateSequenceDefinition.xml")
    assert len(c.sequenceList) == 64

def test_loadText():
    gatedef = GateDefinition()
    gatedef.loadGateDefinition("GateDefinitionIndex.xml")
    c = GateSequenceContainer(gatedef)
    c.loadGateSet("IonTargetGateset.txt")
    c.loadText("grbsequences.txt")
    assert len(c.sequenceList) == 629

def test_save_pickle():
    gatedef = GateDefinition()
    gatedef.loadGateDefinition("GateDefinitionIndex.xml")
    c = GateSequenceContainer(gatedef)
    c.loadGateSet("IonTargetGateset.txt")
    with timing("load text"):
        c.loadText("grbsequences.txt")
    with timing("save pickle"):
        c.savePickle("grbsequences.pkl")
    c2 = GateSequenceContainer(gatedef)
    c2.loadGateSet("IonTargetGateset.txt")
    with timing("load pickle"):
        c2.loadPickle("grbsequences.pkl")

