# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
#from cPyparsing import ParserElement
#ParserElement.enablePackrat()
from unittests import loggingConfig
from pppCompiler import pppCompiler
import os.path
import pytest


def ppCompile(assemblerfile):
    from pulseProgram.PulseProgram import PulseProgram
    pp = PulseProgram()
    pp.debug = True
    pp.loadSource(r"YtterbiumScan.auto.pp")

    pp.toBytecode()
    print("updateVariables")

    for op, val in pp.bytecode:
        print(hex(op), hex(val))

    pp.toBinary()


resultMessage = {None: 'no comparison', False: 'failed', True: 'passed'}
folder = "test"
testfiles = ["Condition", "Assignements", "if_then_else", "ShiftOperations", "RealWorld", "ProcedureCalls",
             "PulseCommand",
             "indented_blocks",
             "Master_uWave_program_v2",
             "Declarations",
             "Microwave",
             "Division",
             "BinOp"
             ]


@pytest.mark.parametrize("name", testfiles)
def test_compile(name):
    assert pppCompiler.pppcompile(os.path.join(folder, name + ".ppp"), os.path.join(folder, name + ".ppc"),
                                  os.path.join(folder, name + ".ppc.reference"))



