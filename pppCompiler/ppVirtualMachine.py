# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import copy
import re

class ppVirtualMachine:
    """A virtual machine that mimics the soft-core processor on the FPGA for bug testing"""
    def __init__(self, code):
        self.mainCode = code
        self.code = code.split('\n')
        self.labelDict = dict()
        self.labelLUT = self.findLabelLocations(self.code)
        self.varDict = dict()
        self.R = 0
        self.CMP = 0

    def printState(self):
        print(self.varDict)
        return self.varDict

    def findLabelLocations(self, code):
        """Find all label locations in terms of line number in the pp code"""
        for n, line in enumerate(self.code):
            m = re.match("^(end_if_label_\d+):", line, flags=re.MULTILINE)
            if m:
                if m.group(1) in self.labelDict.keys():
                    raise Exception("Label {} already in dict!".format(m.group(1)))
                self.labelDict[m.group(1)] = n
            m = re.match("^(while_label_\d+):", line, flags=re.MULTILINE)
            if m:
                if m.group(1) in self.labelDict.keys():
                    raise Exception("Label {} already in dict!".format(m.group(1)))
                self.labelDict[m.group(1)] = n
            m = re.match("^(end_while_label_\d+):", line, flags=re.MULTILINE)
            if m:
                if m.group(1) in self.labelDict.keys():
                    raise Exception("Label {} already in dict!".format(m.group(1)))
                self.labelDict[m.group(1)] = n
            m = re.match("^(else_label_\d+):", line, flags=re.MULTILINE)
            if m:
                if m.group(1) in self.labelDict.keys():
                    raise Exception("Label {} already in dict!".format(m.group(1)))
                self.labelDict[m.group(1)] = n
            m = re.match("^(end_function_label_\d+):", line, flags=re.MULTILINE)
            if m:
                if m.group(1) in self.labelDict.keys():
                    raise Exception("Label {} already in dict!".format(m.group(1)))
                self.labelDict[m.group(1)] = n
        # now that label locations are known, remove actual labels for parsing
        self.mainCode = re.sub(r"^(end_if_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(while_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(end_while_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(else_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(end_function_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.code = self.mainCode.split('\n')

    def replaceLabel(self, m):
        return m.group(2)

    def runCode(self, printAll=False):
        """Execute pp code"""
        i = 0
        pipe = 10
        while i<len(self.code):
            line = self.code[i]
            i += 1
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
                    print(line, " --> self.R = {0}".format(self.R))
                continue
            m = re.match(r"\s*(STWR)\s(\S+)", line)
            if m:
                self.varDict[m.group(2)] = copy.copy(self.R)
                if printAll:
                    print(line, " --> {0} = {1}".format(m.group(2),self.R))
                continue
            m = re.match(r"\s*(CMPLESS)\s(\S+)", line)
            if m:
                self.CMP = int(self.varDict[m.group(2)]) > self.R
                if printAll:
                    print(line, " --> CMP = {0} < {1} = {2}".format(self.R, self.varDict[m.group(2)], self.CMP))
                continue
            m = re.match(r"\s*(CMPGREATER)\s(\S+)", line)
            if m:
                self.CMP = int(self.varDict[m.group(2)]) < self.R
                if printAll:
                    print(line, " --> CMP = {0} > {1} = {2}".format(self.R, self.varDict[m.group(2)], self.CMP))
                continue
            m = re.match(r"\s*(CMPEQUAL)\s(\S+)", line)
            if m:
                self.CMP = int(self.varDict[m.group(2)]) == self.R
                if printAll:
                    print(line, " --> CMP = {0} == {1} = {2}".format(self.R, self.varDict[m.group(2)], self.CMP))
                continue
            m = re.match(r"\s*(MULW)\s(\S+)", line)
            if m:
                self.R *= int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R *= {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(ADDW)\s(\S+)", line)
            if m:
                self.R += int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R += {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(SUBW)\s(\S+)", line)
            if m:
                self.R -= int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R -= {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(ORW)\s(\S+)", line)
            if m:
                self.R = self.R | int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R |= {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(ANDW)\s(\S+)", line)
            if m:
                self.R = self.R & int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R &= {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(SHL)\s(\S+)", line)
            if m:
                self.R <<= int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R <<= {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(SHR)\s(\S+)", line)
            if m:
                self.R >>= int(self.varDict[m.group(2)])
                if printAll:
                    print(line, " --> R >>= {0} -> {1}".format(self.varDict[m.group(2)],self.R))
                continue
            m = re.match(r"\s*(INC)\s(\S+)", line)
            if m:
                self.varDict[m.group(2)] = int(self.varDict[m.group(2)]) + 1
                self.R = self.varDict[m.group(2)]
                if printAll:
                    print(line, " --> {0} += 1 -> {1}".format(m.group(2),self.varDict[m.group(2)]))
                continue
            m = re.match(r"\s*(DEC)\s(\S+)", line)
            if m:
                self.varDict[m.group(2)] = int(self.varDict[m.group(2)]) - 1
                self.R = self.varDict[m.group(2)]
                if printAll:
                    print(line, " --> {0} -= 1 -> {1}".format(m.group(2),self.varDict[m.group(2)]))
                continue
            m = re.match(r"\s*(JMPNCMP)\s(\S+)", line)
            if m:
                if not self.CMP:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        print(line," --> JUMPING TO LINE {0}".format(i))
                continue
            m = re.match(r"\s*(JMPZ)\s(\S+)", line)
            if m:
                if not self.R:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        print(line," --> JUMPING TO LINE {0}".format(i))
                continue
            m = re.match(r"\s*(JMPPIPEEMPTY)\s(\S+)", line)
            if m:
                if pipe<=0:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        print(line," --> JUMPING TO LINE {0}".format(i))
                pipe -= 1
                continue
            m = re.match(r"\s*(JMPNZ)\s(\S+)", line)
            if m:
                if self.R:
                    i = self.labelDict[m.group(2)]
                    if printAll:
                        print(line," --> JUMPING TO LINE {0}".format(i))
                continue
            m = re.match(r"\s*(JMP)\s(\S+)", line)
            if m:
                i = self.labelDict[m.group(2)]
                if printAll:
                    print(line," --> JUMPING TO LINE {0}".format(i))
                continue

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



