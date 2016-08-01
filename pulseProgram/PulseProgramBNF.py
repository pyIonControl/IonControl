# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
  
import collections
import logging
import math
import re, os
import struct

from pyparsing import lineno, LineEnd, Literal, alphanums, alphas, dblQuotedString, Keyword, Word, Regex, pythonStyleComment, nums, ZeroOrMore, Optional

from modules.quantity import Q, is_Q

VAR = Keyword("var").suppress()
CONST = Keyword("const").suppress()
INSERT = Keyword("insert").suppress()

COMMA = Literal(",").suppress()
COLON = Literal(":").suppress()

IDENTIFIER = Word(alphas+"_", alphanums+"_")
NAME = Word(alphas+"_", alphanums+"_")
DECVALUE = Word( nums )
HEXVALUE = Regex("0x[0-9a-f]+")
VALUE = HEXVALUE | DECVALUE
  
  
class ppexception(Exception):
    def __init__(self, message, filename, line, context):
        super(ppexception, self).__init__(message)
        self.file = filename
        self.line = line
        self.context = context
  
# Code definitions
OPS = {'NOP'    : 0x00,
       'DDSFRQ' : 0x01,
       'DDSAMP' : 0x02,
       'DDSPHS' : 0x03,
       'DDSCHN' : 0x04,
       'SHUTR'  : 0x05,
       'COUNT'  : 0x06,
       'DELAY'  : 0x07,
       'LDWR'   : 0x08,
       'LDWI'   : 0x09,
       'STWR'   : 0x0A,
       'STWI'   : 0x0B,
       'LDINDF' : 0x0C,
       'ANDW'   : 0x0D,
       'ADDW'   : 0x0E,
       'INC'    : 0x0F,
       'DEC'    : 0x10,
       'CLRW'   : 0x11,
       'CMP'    : 0x12,
       'JMP'    : 0x13,
       'JMPZ'   : 0x14,
       'JMPNZ'  : 0x15,
       'DAC'    : 0x17,
       'DACUP'  : 0x18,
       'COUNT1'    : 0x20,
       'COUNTBOTH' : 0x21,
       'LDWR1'    : 0x22,
       'STWR1'  : 0x23,
       'CMP1'   : 0x24,
       'JMPZ1'  : 0x25,
       'JMPNZ1'    : 0x26,
       'CLRW1'    : 0x27,
       'SHUTRVAR':0x28,
       'SHUTTERMASK' : 0x30,
       'ASYNCSHUTTER' : 0x31,
       'COUNTERMASK' : 0x32,
       'TRIGGER' : 0x33,
       'UPDATE' : 0x34,
       'WAIT' : 0x35,
       'DDSFRQFINE' : 0x36,
       'LDCOUNT' : 0x37,
       'WRITEPIPE' : 0x38,
       'READPIPE' : 0x39,
       'LDTDCCOUNT' : 0x3a,
       'CMPEQUAL' : 0x3b,
       'JMPCMP' : 0x3c,
       'JMPNCMP': 0x3d,
       'JMPPIPEAVAIL': 0x3e,
       'JMPPIPEEMPTY': 0x3f,
       'READPIPEINDF': 0x40,
       'WRITEPIPEINDF': 0x41,
       'SETRAMADDR': 0x42,
       'RAMREADINDF' : 0x43,
       'RAMREAD' : 0x44,
       'JMPRAMVALID' : 0x45,
       'JMPRAMINVALID' : 0x46,
       'CMPGE' : 0x47,
       'CMPLE' : 0x48, 
       'CMPGREATER' : 0x4a,
       'ORW' : 0x4b,
       'UPDATEINDF' : 0x4d,
       'WAITDDSWRITEDONE' : 0x4e,
       'CMPLESS' : 0x4f,
       'ASYNCINVSHUTTER' : 0x50,
       'END'    : 0xFF }

class Dimensions:
    time = (0, 1, 0, 0, 0, 0, 0, 0, 0)
    frequency = (0, -1, 0, 0, 0, 0, 0, 0, 0)
    voltage = (2, -3, 0, 1, -1, 0, 0, 0, 0)
    current = (0, 0, 0, 0, 1, 0, 0, 0, 0)
    dimensionless = (0, 0, 0, 0, 0, 0, 0, 0, 0)

class Variable:
    def __init__(self):
        self.enabled = True        
        
    def __setstate__(self, d):
        self.__dict__ = d
        
    def __repr__(self):
        return str(self.__dict__)

encodings = { 'AD9912_FRQ': (1e9/2**32, 'Hz', Dimensions.frequency, 0xffffffff ),
              'AD9912_FRQFINE': (1e9/2**48, 'Hz', Dimensions.frequency, 0xffff ),
              'AD9912_PHASE': (360./2**14, '', Dimensions.dimensionless, 0x3fff),
              'CURRENT': (1, 'A', Dimensions.current, 0xffffffff ),
              'VOLTAGE': (1, 'V', Dimensions.voltage, 0xffffffff ),
              'TIME' : ( 5, 'ns', Dimensions.time, 0xffffffffffff ),
              None: (1, '', Dimensions.dimensionless, 0xffffffff ),
              'None': (1, '', Dimensions.dimensionless, 0xffffffff ) }


def variableValueDict( variabledict ):
    returndict = dict()
    for name, var in variabledict.items():
        returndict[name] = var.value
    return returndict

class PulseProgram:    
    """ Encapsulates a PulseProgrammer Program
    loadSource( filename ) loads the contents of the file
    The code is compiled in the following steps
        parse()         generates self.code
        toBytecode()    generates self.bytecode
        toBinary()      generates self.binarycode
    the procedure updateVariables( dictionary )  updates variable values in the bytecode
    """    
    def __init__(self):
        self.variabledict = collections.OrderedDict()        # keeps information on all variables to easily change them later
        self.labeldict = dict()          # keep information on all labels
        self.source = collections.OrderedDict()             # dictionary of source code files (stored as strings)
        self.code = []                   # this is a list of lines
        self.bytecode = []               # list of op, argument tuples
        self.binarycode = bytearray()    # binarycode to be uploaded
        self._exitcodes = dict()          # generate a reverse dictionary of variables of type exitcode
        self.constDict = dict()
        
        class Board:
            channelLimit = 1    
            halfClockLimit = 500000000
        self.adIndexList = [(x, 0) for x in range(6) ]
        self.adBoards = [ Board() ]*6
        
        self.timestep = Q(20.0, 'ns')
        self.initBNF()
        
    def initBNF(self):
        constdecl = (CONST + NAME + VALUE).setParseAction(self.const_action)
        vardecl = (VAR + NAME + VALUE + Optional( COMMA + Regex("[^#\n]*")) ).setParseAction(self.var_action)
        insertdecl = (INSERT + dblQuotedString + LineEnd().suppress()).setParseAction(self.insert_action)
        
        LABEL = IDENTIFIER + COLON
        COMMANDEXP = (IDENTIFIER.setWhitespaceChars(" \t")  + Regex("[^#\n]*").setWhitespaceChars(" \t") + LineEnd().suppress() )
        COMMAND = COMMANDEXP.setParseAction(self.command_action)
        LABELEDCOMMAND = (LABEL + COMMANDEXP ).setParseAction(self.label_command_action)
        
        
        decl = constdecl | vardecl | insertdecl | LABELEDCOMMAND | COMMAND
        
        self.program = ZeroOrMore(decl)
        self.program.ignore(pythonStyleComment)

    def const_action( self, text, loc, arg ):
        """ add the const to the self.constDict dictionary
        """
        logger = logging.getLogger(__name__)
        logger.debug("{0}:{1} const {2}".format(self.currentFile, lineno(loc, text), arg))
        label, value = arg
        if label in self.constDict:
            logger.error( "Error parsing const in file '{0}': attempted to redefine'{1}' to '{2}' from '{3}'".format(self.currentFile, label, value, self.constDict[label]) )
            raise ppexception("Redefining variable", self.currentFile, lineno, label)    
        else:
            self.constDict[label] = int(value)
        
    def var_action( self, text, loc, arg):
        print("var_action", self.currentFile, lineno(loc, text), arg[0:2], arg[2].split(",") if len(arg)>2 else "") 
        """ add a variable to the self.variablesdict
        """
        logger = logging.getLogger(__name__)
        logger.debug( "{0}:{1} Variable {2}".format( self.currentFile, lineno(loc, text), arg ) )
        var = Variable()
        label, data = arg[:2]
        fields = arg[2].split(",") if len(arg)>2 else [None]*3
        fields += [None]*(3-len(fields))
        var.type, unit, var.encoding = [ x if x is None or '' else x.strip() for x in fields ]
        var.name = label
        var.origin = self.currentFile
        var.enabled = True

        if var.encoding not in encodings:
            raise ppexception("unknown encoding {0} in file '{1}':{2}".format(var.encoding, self.currentFile, lineno(loc, text)), self.currentFile, lineno, var.encoding)

        try:
            data = str(eval(data, globals(), self.defines))
        except Exception:
            logger.exception( "Evaluation error in file '{0}' on line: '{1}'".format(self.currentFile, data) )

        if unit is not None:
            var.value = Q(float(data), unit)
            data = self.convertParameter( var.value, var.encoding )
        else:
            var.value = Q(float(data))
            data = int(round(float(data)))

        if label in self.defines:
            logger.error( "Error in file '%s': attempted to reassign '%s' to '%s' (from prev. value of '%s') in a var statement." %(self.currentFile, label, data, self.defines[label]) )
            raise ppexception("variable redifinition", self.currentFile, lineno, label)
        else:
            self.defines[label] = label # add the variable to the dictionary of definitions to prevent identifiers and variables from having the same name
                                        # however, we do not want it replaced with a number but keep the name for the last stage of compilation
            pass
        var.data = data
        self.variabledict.update({ label: var})
        if var.type == "exitcode":
            self._exitcodes[data & 0x0000ffff] = var
    
    def command_action( self, text, loc, arg):
        print("command_action", self.currentFile, lineno(loc, text), arg[0:1], arg[1].split(",") if len(arg)>1 else "") 
        
    def label_command_action( self, text, loc, arg):
        print("label_command_action", self.currentFile, lineno(loc, text), arg[0:2], arg[2].split(",") if len(arg)>2 else "") 
     
    def addLabel(self, label, address, sourcename, lineno):
        if label is not None:
            self.labeldict[label] = address

    
    def insert_action( self, text, loc, arg ):
        oldfile = self.currentFile
        print("insert_action", lineno(loc, text), arg)
        myprogram = self.program.copy()
        self.currentFile = arg[0][1:-1]
        result = myprogram.parseFile( self.currentFile )
        self.currentFile = oldfile
        print(result)
        return result
    
    def assembleFile(self, filename):
        self.currentFile = filename
        result = self.program.parseFile( self.currentFile )
        return result

    def setHardware(self, adIndexList, adBoards, timestep ):
        self.adIndexList = adIndexList
        self.adBoards = adBoards
        self.timestep = timestep
        assert self.timestep.has_dimension('s')
        
    def saveSource(self):
        for name, text in self.source.items():
            with open(os.path.join(self.pp_dir, name), 'w') as f:
                f.write(text)            
        
    def loadSource(self, pp_file):
        """ Load the source pp_file
        #include files are loaded recursively
        all code lines are added to self.sourcelines
        for each source file the contents are added to the dictionary self.source
        """
        self.source.clear()
        self.pp_dir, self.pp_filename = os.path.split(pp_file)
        self.sourcelines = []
        self.insertSource(self.pp_filename)
        self.compileCode()

    def updateVariables(self, variables ):
        """ update the variable values in the bytecode
        """
        logger = logging.getLogger(__name__)
        for name, value in variables.items():
            if name in self.variabledict:
                var = self.variabledict[name]
                address = var.address
                var.value = value
                logger.debug( "updateVariables {0} at address 0x{2:x} value {1}, 0x{3:x}".format(name, value, address, int(var.data)) )
                var.data = self.convertParameter(value, var.encoding )
                self.bytecode[address] = (self.bytecode[address][0], var.data )
                self.variabledict[name] = var
            else:
                logger.error( "variable {0} not found in dictionary.".format(name) )
        return self.bytecode
        
    def variables(self):
        mydict = dict()
        for name, var in self.variabledict.items():
            mydict.update( {name: var.value })
        return mydict
        
    def variable(self, variablename ):
        return self.variabledict.get(variablename).value

    def variableUpdateCode(self, variablename, value ):
        """returns the code to update the variable directly on the fpga
        consists of variablelocation and variablevalue
        """
        var = self.variabledict[variablename]
        data = self.convertParameter(value, var.encoding )
        return bytearray( struct.pack('II', (var.address, data)))
        
    def flattenList(self, l):
        return [item for sublist in l for item in sublist]
        
    def variableScanCode(self, variablename, values):
        var = self.variabledict[variablename]
        # [item for sublist in l for item in sublist] idiom for flattening of list
        return self.flattenList( [ (var.address, self.convertParameter(x, var.encoding)) for x in values ] )
                   
    def loadFromMemory(self):
        """Similar to loadSource
        only this routine loads from self.source
        """
        self.sourcelines = []
        self._exitcodes = dict()
        self.insertSource(self.pp_filename)
        self.compileCode()

    def toBinary(self):
        """ convert bytecode to binary
        """
        logger = logging.getLogger(__name__)
        self.binarycode = bytearray()
        for wordno, (op, arg) in enumerate(self.bytecode):
            logger.debug( "{0} {1} {2} {3}".format( hex(wordno), hex(int(op)), hex(int(arg)), hex(int((int(op)<<24) + int(arg))) ) )
            self.binarycode += struct.pack('I', int((op<<24) + arg))
        return self.binarycode
        
    def currentVariablesText(self):
        lines = list()
        for name, var in iter(sorted(self.variabledict.items())):
            lines.append("{0} {1}".format(name, var.value))
        return '\n'.join(lines)
           

# routines below here should not be needed by the user   

    insertPattern = re.compile('#insert\s+([\w.-_]+)', re.IGNORECASE)
    codelinePattern = re.compile('(#define|\s*[^#\s]+)', re.IGNORECASE)
    def insertSource(self, pp_file):
        """ read a source file pp_file
        calls itself recursively to for #insert
        adds the contents of this file to the dictionary self.source
        """
        logger = logging.getLogger(__name__)
        if pp_file not in self.source:
            with open(os.path.join(self.pp_dir, pp_file)) as f:
                self.source[pp_file] = ''.join(f.readlines())
        sourcecode = self.source[pp_file]
        for line, text in enumerate(sourcecode.splitlines()):
            m = self.insertPattern.match(text)
            if m:
                filename = m.group(1)
                logger.info( "inserting code from {0}".format(filename) )
                self.insertSource(filename)
            else:
                if self.codelinePattern.match(text):
                    self.sourcelines.append((text, line+1, pp_file))


    labelPattern = re.compile('(\w+):\s+([^#\n\r]*)')
    opPattern = re.compile('\s*(\w+)(?:\s+([^#\n\r]*)){0,1}', re.IGNORECASE)
    varPattern = re.compile('var\s+(\w+)\s+([^#,\n\r]+)(?:,([^#,\n\r]+)){0,1}(?:,([^#,\n\r]+)){0,1}(?:,([^#,\n\r]+)){0,1}(?:#([^\n\r]+)){0,1}') #
    def parse(self):
        """ parse the code
        """
        logger = logging.getLogger(__name__)
        self.code = []
        self.variabledict = collections.OrderedDict() 
        self.defines = dict()
        addr_offset = 0
    
        for text, lineno, sourcename in self.sourcelines:    
            m = self.varPattern.match(text)
            if m:
                self.addVariable(m, lineno, sourcename)
            else:
                m = self.definePattern.match(text)
                if m:
                    self.addDefine(m, lineno, sourcename)
                else:
                    # extract any JMP label, if present
                    m = self.labelPattern.match(text)
                    if m:
                        label, text = m.groups() #so the operation after ":" still gets parsed CWC 08162012
                    else:
                        label = None #The label for non-jump label line is NONE CWC 08172012
            
                    # search OPS list for a match to the current line
                    m = self.opPattern.match(text)
                    if m:
                        op, args = m.groups()
                        op = op.upper()
                        # split and remove whitespace 
                        arglist = [0] if args is None else [ 0 if x is None else x.strip() for x in args.split(',')]
                        #substitute the defined variable directly with the corresponding value CWC 08172012
                        arglist = [ self.defines[x] if x in self.defines else x for x in arglist ] 
                        #check for dds commands so CHAN commands can be inserted
                        if (op[:3] == 'DDS'):
                            try:
                                board = self.adIndexList[int(arglist[0])][0]
                            except ValueError:
                                raise ppexception("DDS argument does not resolve to integer", sourcename, lineno, arglist[0])
                            chan = self.adIndexList[int(arglist[0])][1]
                            if (self.adBoards[board].channelLimit != 1):
                                #boards with more than one channel require an extra channel selection command
                                chanData = self.adBoards[board].addCMD(chan)
                                chanData += (int(board) << 16)
                                self.code.append((len(self.code)+addr_offset, 'DDSCHN', chanData, label, sourcename, lineno))
                        data = arglist if len(arglist)>1 else arglist[0]

                        self.addLabel( label, len(self.code), sourcename, lineno)
                        self.code.append((len(self.code)+addr_offset, op, data, label, sourcename, lineno))
                    else:
                        logger.error( "Error processing line {2}: '{0}' in file '{1}' (unknown opcode?)".format(text, sourcename, lineno) )
                        raise ppexception("Error processing line {2}: '{0}' in file '{1}' (unknown opcode?)".format(text, sourcename, lineno),
                                          sourcename, lineno, text)
        self.appendVariableCode()
        return self.code

                
    def appendVariableCode(self):
        """ append all variables to the instruction part of the code
        """
        for var in list(self.variabledict.values()):
            address = len(self.code)
            self.code.append((address, 'NOP', var.data if var.enabled else 0, None, var.origin, 0 ))
            var.address = address        

    def addVariable(self, m, lineno, sourcename):
        """ add a variable to the self.variablesdict
        """
        logger = logging.getLogger(__name__)
        logger.debug( "Variable {0} {1} {2}".format( m.groups(), lineno, sourcename ) )
        var = Variable()
        label, data, var.type, unit, var.encoding, var.comment = [ x if x is None else x.strip() for x in m.groups()]
        var.name = label
        var.origin = sourcename
        var.enabled = True

        if var.encoding not in encodings:
            raise ppexception("unknown encoding {0} in file '{1}':{2}".format(var.encoding, sourcename, lineno), sourcename, lineno, var.encoding)

        try:
            data = str(eval(data, globals(), self.defines))
        except Exception:
            logger.exception( "Evaluation error in file '{0}' on line: '{1}'".format(sourcename, data) )

        if unit is not None:
            var.value = Q(float(data), unit)
            data = self.convertParameter( var.value, var.encoding )
        else:
            var.value = Q(float(data))
            # var.value.output_prec(0)   # without dimension the parameter has to be int. Thus, we do not want decimal places :)
            data = int(round(float(data)))

        if label in self.defines:
            logger.error( "Error in file '%s': attempted to reassign '%s' to '%s' (from prev. value of '%s') in a var statement." %(sourcename, label, data, self.defines[label]) )
            raise ppexception("variable redifinition", sourcename, lineno, label)
        else:
            self.defines[label] = label # add the variable to the dictionary of definitions to prevent identifiers and variables from having the same name
                                        # however, we do not want it replaced with a number but keep the name for the last stage of compilation
            pass
        var.data = data
        self.variabledict.update({ label: var})
        if var.type == "exitcode":
            self._exitcodes[data & 0x0000ffff] = var

    # code is (address, operation, data, label or variablename, currentfile)
    def toBytecode(self):
        """ generate bytecode from code
        """
        logger = logging.getLogger(__name__)
        logger.debug( "\nCode ---> ByteCode:" )
        self.bytecode = []
        for line in self.code:
            logger.debug( "{0}: {1}".format(hex(line[0]),  line[1:] )) 
            bytedata = 0
            if line[1] not in OPS:
                raise ppexception("Unknown command {0}".format(line[1]), line[4], line[5], line[1]) 
            byteop = OPS[line[1]]
            try:
                data = line[2]
                #attempt to locate commands with constant data
                if (data == ''):
                    #found empty data
                    bytedata = 0
                elif isinstance(data, (int, int)):
                    bytedata = data
                elif isinstance(data, float):
                    bytedata = int(data)
                elif isinstance(data, str): # now we are dealing with a variable and need its address
                    bytedata = self.variabledict[line[2]].address if line[2] in self.variabledict else self.labeldict[line[2]]
                elif isinstance(data, list): # list is what we have for DDS, will have 8bit channel and 16bit address
                    channel, data = line[2]
                    if isinstance(data, str):
                        data = self.variabledict[data].address
                    bytedata = ((int(channel) & 0xf) << 16) | (int(data) & 0x0fff)
            except KeyError:
                logger.error( "Error assembling bytecode from file '{0}': Unknown variable: '{1}'. \n".format(line[4], data) )
                raise ppexception("{0}: Unknown variable {1}".format(line[4], data), line[4], line[5], data)
            self.bytecode.append((byteop, bytedata))
            logger.debug( "---> {0} {1}".format(hex(byteop), hex(bytedata)) )
    
        return self.bytecode 


    def convertParameter(self, mag, encoding=None ):
        """ convert a dimensioned parameter to the binary value
        expected by the hardware. The conversion is determined by the variable encoding
        """
        if is_Q(mag):
            if mag.dimensionality == Dimensions.time:
                result = int(round(mag / self.timestep))
            else:
                step, unit, _, mask = encodings[encoding]
                result = int(round(mag.m_as(unit) / step)) & mask
        else:
            if encoding:
                step, unit, _, mask = encodings[encoding]
                result = int(round(mag/step)) & mask
            else:
                result = mag
        return result

    def compileCode(self):
        self.parse()
        self.toBytecode()
        
    def exitcode(self, code):
        if code in self._exitcodes:
            var = self._exitcodes[code]
            if var.comment:
                return var.comment
            else:
                return var.name
        else:
            return "Exitcode {0} Not found".format(code)

if __name__ == "__main__":
    pp = PulseProgram()
    pp.debug = True
    pp.loadSource(r"prog\Ions\Bluetest.pp")
    #pp.loadSource(r"prog\single_pulse_exp_adiabatic.pp")
    
        
    pp.toBytecode()
    print("updateVariables")
    pp.updateVariables({'coolingFreq': Q(125, 'MHz')})
    
    for op, val in pp.bytecode:
        print(hex(op), hex(val))
        
    pp.toBinary()
        
#    for var in pp.variabledict.items():
#        print var
    
