import pytest
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