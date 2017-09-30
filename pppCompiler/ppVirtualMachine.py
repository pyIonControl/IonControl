# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import copy
import re
import random
from modules.quantity import Q

def DDS(amp=0,freq=0,phase=0):
    return {'amp': amp, 'freq': freq, 'phase': phase}

class ppVirtualMachine:
    """A virtual machine that mimics the soft-core processor on the FPGA for bug testing"""
    def __init__(self, code):
        random.seed(1)   # this must be set consistently for comparing pulse programs in unittests
        self.mainCode = code
        self.code = code.split('\n')
        self.labelDict = dict()
        self.labelLUT = self.findLabelLocations(self.code)
        self.varDict = dict()
        self.R = 0
        self.CMP = 0
        self.DDSChannels = 12
        self.DDSs = [DDS() for i in range(self.DDSChannels)]
        self.ddsWriteTimer = 0
        self.timer = 0
        self.varDict['DDSs'] = self.DDSs
        self.SHUTTER = 0  # dummy variables for shutters and counters, put here as a placeholder until
        self.COUNTER = 0  # we come up with a better way of tracking the state as a function of time

        # self.fmtstr sets the column widths for print strings. If your screen is not wide enough, adjust
        # the parameters behind the colons to reduce the column widths
        self.fmtstr = "{0:50}{1:80}{2}"
        self.timestr = "ELAPSED CLOCK CYCLES: {0}"

    def printState(self):
        print(self.varDict)
        return self.varDict

    def findLabelLocations(self, code):
        """Find all label locations in terms of line number in the pp code"""
        for n, line in enumerate(self.code):
            m = re.match("^(\S+):", line, flags=re.MULTILINE)
            if m:
                if m.group(1) in self.labelDict.keys():
                    raise Exception("Label {} already in dict!".format(m.group(1)))
                self.labelDict[m.group(1)] = n
        # now that label locations are known, remove actual labels for parsing
        self.mainCode = re.sub(r"^(\S+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.code = self.mainCode.split('\n')

    def replaceLabel(self, m):
        return m.group(2)

    def runCode(self, printAll=False):
        """Execute pp code"""
        i = 0
        pipe = 10
        self.timer = 0
        self.ddsWriteTimer = 0
        while i<len(self.code):
            line = self.code[i]
            i += 1
            self.timer += 1
            if self.ddsWriteTimer > 0:
                self.ddsWriteTimer -= 1
            else:
                self.ddsWritetimer = 0 # just in case
            m = re.match(r"^ *#", line, re.MULTILINE)
            if m:
                self.timer -= 1
                continue
            m = re.match(r"(var)\s(\S+)\s+(\S+), parameter, ([a-zA-Z]+)",line)
            if m:
                if "." in m.group(3):
                    if m.group(4) in ['s', 'ms', 'us', 'ns']:
                        numClockCycles = round(Q(float(m.group(3)),m.group(4)).m_as('ns')/5)
                        self.varDict[m.group(2)] = numClockCycles
                    else:
                        self.varDict[m.group(2)] = float(m.group(3))
                else:
                    if m.group(4) in ['s', 'ms', 'us', 'ns']:
                        numClockCycles = round(Q(int(m.group(3),0),m.group(4)).m_as('ns')/5)
                        self.varDict[m.group(2)] = numClockCycles
                    else:
                        self.varDict[m.group(2)] = int(m.group(3),0) #0 allows for hex conversion
                continue
            m = re.match(r"(var)\s(\S+)\s+(\S+),",line)
            if m:
                if "." in m.group(3):
                    self.varDict[m.group(2)] = float(m.group(3))
                else:
                    self.varDict[m.group(2)] = int(m.group(3),0) #0 allows for hex conversion
                continue
            else:
                m = re.match(r"(var)\s(\S+)\s+(\S+)",line)
                if m:
                    if "." in m.group(3):
                        self.varDict[m.group(2)] = float(m.group(3))
                    else:
                        self.varDict[m.group(2)] = int(m.group(3))
                    continue
                else:
                    m = re.match(r"(var)\s(\S+)",line)
                    if m:
                        self.varDict[m.group(2)] = None
                        continue
            m = re.match(r"(const)\s(\S+)\s+(\S+),",line)
            if m:
                if "." in m.group(3):
                    self.varDict[m.group(2)] = float(m.group(3))
                else:
                    self.varDict[m.group(2)] = int(m.group(3))
                continue
            else:
                m = re.match(r"(const)\s(\S+)\s+(\S+)",line)
                if m:
                    if "." in m.group(3):
                        self.varDict[m.group(2)] = float(m.group(3))
                    else:
                        self.varDict[m.group(2)] = int(m.group(3))
                    continue
                else:
                    m = re.match(r"(const)\s(\S+)",line)
                    if m:
                        self.varDict[m.group(2)] = None
                        continue
            m = re.match(r"\s*(LDWR)\s(\S+)", line)
            if m:
                self.R = copy.copy(int(self.varDict[m.group(2)]))
                if printAll:
                    msg =  " --> self.R = {0}".format(self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(STWR)\s(\S+)", line)
            if m:
                self.varDict[m.group(2)] = copy.copy(self.R)
                if printAll:
                    msg =  " --> {0} = {1}".format(m.group(2),self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(CMPLESS)\s(\S+)", line)
            if m:
                self.CMP = int(self.varDict[m.group(2)]) > self.R
                if printAll:
                    msg =  " --> CMP = {0} < {1} = {2}".format(self.R, self.varDict[m.group(2)], self.CMP)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(CMPGREATER)\s(\S+)", line)
            if m:
                self.CMP = int(self.varDict[m.group(2)]) < self.R
                if printAll:
                    msg =  " --> CMP = {0} > {1} = {2}".format(self.R, self.varDict[m.group(2)], self.CMP)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(CMPEQUAL)\s(\S+)", line)
            if m:
                self.CMP = int(self.varDict[m.group(2)]) == self.R
                if printAll:
                    msg = " --> CMP = {0} == {1} = {2}".format(self.R, self.varDict[m.group(2)], self.CMP)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(MULW)\s(\S+)", line)
            if m:
                self.R *= int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R *= {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(ADDW)\s(\S+)", line)
            if m:
                self.R += int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R += {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(SUBW)\s(\S+)", line)
            if m:
                self.R -= int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R -= {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(ORW)\s(\S+)", line)
            if m:
                self.R = self.R | int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R |= {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(ANDW)\s(\S+)", line)
            if m:
                self.R = self.R & int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R &= {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(SHL)\s(\S+)", line)
            if m:
                self.R <<= int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R <<= {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(SHR)\s(\S+)", line)
            if m:
                self.R >>= int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> R >>= {0} -> {1}".format(self.varDict[m.group(2)],self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(INC)\s(\S+)", line)
            if m:
                self.varDict[m.group(2)] = int(self.varDict[m.group(2)]) + 1
                self.R = self.varDict[m.group(2)]
                if printAll:
                    msg = " --> {0} += 1 -> {1}".format(m.group(2),self.varDict[m.group(2)])
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(DEC)\s(\S+)", line)
            if m:
                self.varDict[m.group(2)] = int(self.varDict[m.group(2)]) - 1
                self.R = self.varDict[m.group(2)]
                if printAll:
                    msg = " --> {0} -= 1 -> {1}".format(m.group(2),self.varDict[m.group(2)])
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(JMPNCMP)\s(\S+)", line)
            if m:
                if not self.CMP:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        msg = " --> JUMPING TO LINE {0}".format(i)
                        print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(JMPZ)\s(\S+)", line)
            if m:
                if not self.R:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        msg = " --> JUMPING TO LINE {0}".format(i)
                        print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(JMPPIPEEMPTY)\s(\S+)", line)
            if m:
                if pipe<=0:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        msg = " --> JUMPING TO LINE {0}".format(i)
                        print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                pipe -= 1
                continue
            m = re.match(r"\s*(JMPNZ)\s(\S+)", line)
            if m:
                if self.R:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        msg = " --msg = > JUMPING TO LINE {0}".format(i)
                        print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(JMP)\s(\S+)", line)
            if m:
                i = self.labelDict[m.group(2)]
                if printAll:
                    msg = " --> JUMPING TO LINE {0}".format(i)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(JMPNINTERRUPT)\s(\S+)", line)
            if m:
                i = self.labelDict[m.group(2)]
                if printAll:
                    msg = " --> JUMPING TO LINE {0}".format(i)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(DDSFRQ)\s(\S+),\s(\S+)", line)
            if m:
                self.DDSs[int(self.varDict[m.group(2)])]['freq'] = self.varDict[m.group(3)]
                self.ddsWriteTimer += 48
                if printAll:
                    msg = " --> SETTING FREQUENCY TO {0} ON DDS CHANNEL {1}".format(m.group(3),m.group(2))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(DDSPHS)\s(\S+),\s(\S+)", line)
            if m:
                self.DDSs[int(self.varDict[m.group(2)])]['phase'] = self.varDict[m.group(3)]
                self.ddsWriteTimer += 48
                if printAll:
                    msg = " --> SETTING PHASE TO {0} ON DDS CHANNEL {1}".format(m.group(3),m.group(2))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(DDSAMP)\s(\S+),\s(\S+)", line)
            if m:
                self.DDSs[int(self.varDict[m.group(2)])]['amp'] = self.varDict[m.group(3)]
                self.ddsWriteTimer += 48
                if printAll:
                    msg = " --> SETTING AMPLITUDE TO {0} ON DDS CHANNEL {1}".format(m.group(3),m.group(2))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(LDCOUNT)\s(\S+)", line)
            if m:
                self.R = random.randint(0,30)
                if printAll:
                    msg = " --> LOADED {0} (RANDOM) COUNTS FROM CHANNEL {1}".format(self.R,int(self.varDict[m.group(2)]))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(RAMREAD)", line)
            if m:
                self.R = random.randint(0,30)
                if printAll:
                    msg = " --> READING FROM RAM: {} (RANDOM)".format(self.R)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(COUNTERMASK)\s(\S+)", line)
            if m:
                self.COUNTER = m.group(2)
                if printAll:
                    msg = " --> SETTING COUNTER TO {0}".format(m.group(2))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(SHUTTERMASK)\s(\S+)", line)
            if m:
                self.SHUTTER = m.group(2)
                if printAll:
                    msg = " --> SETTING COUNTER TO {0}".format(m.group(2))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"WAITDDSWRITEDONE", line)
            if m:
                self.timer += self.ddsWriteTimer
                if printAll:
                    msg = " --> WAITING {0} CLOCK CYCLES FOR DDS WRITE".format(self.ddsWriteTimer)
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                self.ddsWriteTimer = 0
                continue
            m = re.match(r"\s*(UPDATE)\s1, (\S+)", line)
            if m:
                self.timer += int(self.varDict[m.group(2)])
                if int(self.varDict[m.group(2)]) > self.ddsWriteTimer:
                    self.ddsWriteTimer = 0
                else:
                    self.ddsWriteTimer -= int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> PULSED UPDATE FOR {0} CLOCK CYCLES".format(self.varDict[m.group(2)])
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(UPDATE)\s([a-zA-Z]+)", line)
            if m:
                self.timer += int(self.varDict[m.group(2)])
                if int(self.varDict[m.group(2)]) > self.ddsWriteTimer:
                    self.ddsWriteTimer = 0
                else:
                    self.ddsWriteTimer -= int(self.varDict[m.group(2)])
                if printAll:
                    msg = " --> UPDATE FOR {0} CLOCK CYCLES".format(self.varDict[m.group(2)])
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
            m = re.match(r"\s*(END)", line)
            if m:
                if printAll:
                    msg = " --> PROGRAM END"
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                break
            m = re.match(r"\s*(ASYNCINVSHUTTER)\s(\S+)", line)
            if m:
                self.SHUTTER = m.group(2)
                if printAll:
                    msg = " --> INVERTING {0} SHUTTER".format(m.group(2))
                    print(self.fmtstr.format(line, msg, self.timestr.format(self.timer)))
                continue
        print("ELAPSED CLOCK CYCLES: ", self.timer)
        return self.timer

def compareDicts(d1,d2):
    dout = dict()
    for k,v in d1.items():
        if "inlinevar" not in k:
            if k in d2.keys():
                if d2[k] != v:
                    dout[k] = {'d1': v, 'd2': d2[k]}
    return dout

########################################################################################################################
#### Begin code for testing of ppp files with raw python, correcting for ppp variable types and running it directly ####
########################################################################################################################

def evalRawCode(code):
    preprocessed_code = re.sub(r"const\s+(\S+)\s*=\s*(\S+)\s*\n", correctDeclarations, code)
    preprocessed_code = re.sub(r"parameter\<\S+\>\s+(\S+)\s*=\s*(\S+).*\n", correctDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"parameter\s+(\S+)\s+=\s*(\S+).*\n", correctDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"var\s+(\S+)\s*=\s*(\S+).*\n", correctDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"shutter\s+(\S+)\s*=\s*(\S+).*\n", correctDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"trigger\s+(\S+)\s*=\s*(\S+).*\n", correctDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"counter\s+(\S+)\s*=\s*(\S+).*\n", correctDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"const\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"parameter\<\S+\>\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"parameter\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"var\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"masked_shutter\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"shutter\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"trigger\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"counter\s+(\S+)\s*\n", correctEmptyDeclarations, preprocessed_code)
    preprocessed_code = re.sub(r"(\s*)(\S+)\s=\s(.*)", printAllSettings, preprocessed_code)

    print('---------------------------------------')
    print('Preprocessed Code For Python Evaluation')
    print('---------------------------------------')
    print(preprocessed_code)
    d = dict()
    ex = exec(compile(preprocessed_code, '<string>', 'exec', optimize=2),d,d)
    return d

def correctDeclarations(code):
    """Parse var declarations with no value and add them to symbols dictionary"""
    return "{0} = {1}\n".format(code.group(1), code.group(2))

def correctEmptyDeclarations(code):
    """Parse var declarations with no value and add them to symbols dictionary"""
    return "\n"

def printAllSettings(code):
    """Add a print statement after every assignment for tracking the variable state"""
    if code.group(2)[0] != '#':
        return "{0}{1} = {2}{0}print('{1} = ', {1})".format(code.group(1),code.group(2),code.group(3))
    return "{0}{1} = {2}".format(code.group(1),code.group(2),code.group(3))



