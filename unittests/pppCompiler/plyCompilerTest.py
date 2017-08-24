# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from unittests import loggingConfig
from pppCompiler.plyCompiler import IndentLexer, plyParser
from unittest import TestCase, main
import os.path

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
testfiles = [ "Condition", "Assignements", "if_then_else", "ShiftOperations", "RealWorld", "ProcedureCalls",
              "PulseCommand",
              "indented_blocks",
              "Master_uWave_program_v2",
              "Declarations"]

def test_lex_generator(name):
    def test(self):
        #self.assertTrue(pppCompiler.pppcompile(os.path.join(folder, name + ".ppp"), os.path.join(folder, name + ".ppc"),
        #                       os.path.join(folder, name + ".ppc.reference")))
        with open(os.path.join('test', name + '.ppp'), 'r') as stream:
            code = stream.read()
        l = IndentLexer()
        l.input(code)
        for t in l.token_gen():
            print(t)
    return test

def test_parse_generator(name):
    def test(self):
        #self.assertTrue(pppCompiler.pppcompile(os.path.join(folder, name + ".ppp"), os.path.join(folder, name + ".ppc"),
        #                       os.path.join(folder, name + ".ppc.reference")))
        with open(os.path.join('test', name + '.ppp'), 'r') as stream:
            code = stream.read()

        parser = plyParser()
        tree = parser.parse(code)
        print(parser.symbols)
    return test


class pppCompilerTest(TestCase):
    pass


for name in testfiles:
    test_name = "test_lex_{0}".format(name)
    test = test_lex_generator(name)
    setattr(pppCompilerTest, test_name, test)

for name in testfiles:
    test_name = "test_parse_{0}".format(name)
    test = test_parse_generator(name)
    setattr(pppCompilerTest, test_name, test)

if __name__ == "__main__":
    main()

