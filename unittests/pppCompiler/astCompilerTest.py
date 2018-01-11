# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
#from pyparsing import ParserElement
#ParserElement.enablePackrat()
import pytest

from unittests import loggingConfig
from pppCompiler import astCompiler as pppCompiler
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

verbose = False  # if verbose is True, the virtual machine prints line by line results
keep_output = False

resultMessage = {None: 'no comparison', False: 'failed', True: 'passed'}
folder = os.path.join(os.getcwd(), 'test')
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
def test_astCompile(name):
    result = (pppCompiler.pppcompile(os.path.join(folder, name + ".ppp"), os.path.join(folder, name + ".ppc"),
                                     os.path.join(folder, name + ".ppc.reference"), verbose=verbose,
                                     keepoutput=keep_output, printFinalVars=True))
    assert result


if __name__ == "__main__":

    mycode = """#code
    
parameter<AD9912_PHS> xx = 5.352  
const chan = 2
var retval = 0
var retval8 = 12
var retval3 = 0
var arg1 = 0
masked_shutter shutter2
shutter mainshutter



def myFunc(c,j):
    d = 5
    k = 3
    b = c*2
    #b=c
    while k<18:
        if 1 < b and b < 1006 or 12 < k < b < 20000000:
            b = b*k
        elif b:
            b -= 12
        elif b == 36:
            b = 37
        else:
            b += k
            b <<= 2
        k += 1
        d = b << 1
        if d > 3000000000:
            return d
    #set_dds(channel=chan, phase=xx)
    #rand_seed(d)
    #update()
    #b = secf(d)
    b = roundabout(d)
    return b
    
def secf(r):
    #def innersec(ik):
        #llk = ik+6
        #return llk
    #u = innersec(r)
    u = r*2
    u *= r
    x = 0
    x = myFunc(u,r)
    return x
    
def roundabout(x):
    ff = sec2(x)
    return ff
    
def sec2(x):
    fk = sec3(x)
    return fk

def sec3(x):
    #kn = innersec(x) 
    kn = x+2
    return kn
    
arg1 = 5
arg2 = 6
#retval = myFunc(arg1,6)
g=3*arg2
#g *= arg2
arg1 = 4
arg2 = 4
#myFunc(arg1,arg2)
retval = 10
arg2 = 5
retval8 = secf(arg2)
g*=2
arg2 = 4
retval3 = secf(arg2)
g*=2
arg2 = 4
retval2 = secf(arg2)
g1 = retval8
g2 = retval2
arg3 = 2
"""



    ppAn = pppCompiler.pppCompiler()
    ppAn.compileString(mycode)
    #ppAn.visit(tree)
    print(ppAn.preamble + ppAn.maincode)

    compcode = ppAn.preamble + ppAn.maincode
    ppvm = pppCompiler.ppVirtualMachine(compcode)
    ppvm.runCode()
    ppvm.printState()
    dcomp = ppvm.varDict
    draw = pppCompiler.evalRawCode(mycode)
    print(draw)
    print("Dicts equal? ", pppCompiler.compareDicts(dcomp,draw))


