# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from modules.Expression import Expression
from modules.quantity import Q, is_Q

class GateSequenceCompilerException(Exception):
    pass

class GateSequenceCompiler(object):
    expression = Expression()
    def __init__(self, pulseProgram ):
        self.pulseProgram = pulseProgram
        self.compiledGates = dict()

    """Compile all gate sequences into binary representation
        returns tuple of start address list and bytearray data"""

    def gateSequencesCompile(self, gatesets):
        logger = logging.getLogger(__name__)
        logger.info("compiling {0} gateSequences.".format(len(gatesets.sequenceList)))
        self.gateCompile(gatesets.gateDefinition)
        addresses = list()
        data = list()
        index = 0
        for gatestring in gatesets.sequenceList:
            gatestringdata = self.gateSequenceCompile(gatestring)
            addresses.append(index)
            data.extend(gatestringdata)
            index += len(gatestringdata) * 8
        return addresses, data

    """Compile one gateset into its binary representation"""
    def gateSequenceCompile(self, gateset):
        data = list()
        length = 0
        for gate in gateset:
            thisCompiledGate = self.compiledGates[gate]
            data.extend( thisCompiledGate )
            length += len(thisCompiledGate)//self.pulseListLength
        return [length] + data

    """Compile each gate definition into its binary representation"""
    def gateCompile(self, gateDefinition ):
        logger = logging.getLogger(__name__)
        variables = self.pulseProgram.variables()
        pulseList = list(gateDefinition.PulseDefinition.values())
        self.pulseListLength = len(pulseList)
        for gatename, gate in gateDefinition.Gates.items():  # for all defined gates
            data = list()
            gateLength = 0
            for name, strvalue in gate.pulsedict:
                result = self.expression.evaluate(strvalue, variables )
                if name!=pulseList[ gateLength % self.pulseListLength ].name:
                    raise GateSequenceCompilerException("In gate {0} entry {1} found '{2}' expected '{3}'".format(gatename, gateLength, name, pulseList[ gateLength % self.pulseListLength ]))
                encoding = gateDefinition.PulseDefinition[name].encoding
                data.append( self.pulseProgram.convertParameter( result, encoding ) )
                gateLength += 1
            if gateLength % self.pulseListLength != 0:
                raise GateSequenceCompilerException("In gate {0} number of entries ({1}) is not a multiple of the pulse definition length ({2})".format(gatename, gateLength, self.pulseListLength))
            self.compiledGates[gatename] = data
            logger.info( "compiled {0} to {1}".format(gatename, data) )


if __name__=="__main__":
    from pulseProgram.PulseProgram import PulseProgram
    from gateSequence.GateDefinition import GateDefinition
    from gateSequence.GateSequenceContainer import GateSequenceContainer

    pp = PulseProgram()
    pp.debug = False
    pp.loadSource(r"C:\Users\Public\Documents\experiments\QGA\config\PulsePrograms\YbGateSequenceTomography.pp")

    gatedef = GateDefinition()
    gatedef.loadGateDefinition(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\StandardGateDefinitions.xml")
    gatedef.printGates()

    container = GateSequenceContainer(gatedef)
    container.loadXml(r"C:\Users\Public\Documents\experiments\QGA\config\GateSequences\GateSequenceDefinition.xml")
    container.validate()
    #print container

    compiler = GateSequenceCompiler(pp)
    compiler.gateCompile( container.gateDefinition )
    print(compiler.gateSequenceCompile( container.GateSequenceDict['S11']))

    address, data = compiler.GateSequencesCompile( container )
    print(address)
    print(data)


