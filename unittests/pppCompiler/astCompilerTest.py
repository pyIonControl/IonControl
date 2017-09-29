# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
#from pyparsing import ParserElement
#ParserElement.enablePackrat()
from unittests import loggingConfig
from pppCompiler import astCompiler as pppCompiler
from unittest import TestCase, main
import os

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
folder = os.path.join(os.getcwd(), 'test')
testfiles = [ "Condition", "Assignements", "if_then_else", "ShiftOperations", "RealWorld", "ProcedureCalls",
              "PulseCommand",
              "indented_blocks",
              "Master_uWave_program_v2",
              "Declarations"]

def test_generator(name):
    def test(self):
        self.assertTrue(pppCompiler.pppcompile(os.path.join(folder, name + ".ppp"), os.path.join(folder, name + ".ppc"),
                                               os.path.join(folder, name + ".ppc.reference")))
    return test


class pppCompilerTest(TestCase):
    pass


for name in testfiles:
    test_name = "test_{0}".format(name)
    test = test_generator(name)
    setattr(pppCompilerTest, test_name, test)


if __name__ == "__main__":
    main()


