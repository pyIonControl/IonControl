# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from pyparsing import lineno, line, LineEnd, Literal, alphanums, alphas, dblQuotedString, Keyword, Word, Regex, pythonStyleComment, nums, ZeroOrMore
from pyparsing import Optional, Forward, indentedBlock, Group, delimitedList, oneOf, ParseResults
import logging
import sys
import re
from .CompileException import CompileException

"""
BNF of grammar

program ::= decl*

decl ::= vardecl | constdecl

vardecl ::= "var" NAME VALUE "," PURPOSE "," UNIT "," ENCODING

PURPOSE ::= NAME NAME

constdecl ::= "const" NAME VALUE

VALUE ::= HEXVALUE | DECVALUE

HEXVALUE ::= 0x nums*

DECVALUE ::= nums* 
"""


var = Keyword("var").suppress()
const = Keyword("const").suppress()
insert = Keyword("insert").suppress()

comma = Literal(",").suppress()
colon = Literal(":").suppress()

identifier = Word(alphas+"_", alphanums+"_").setWhitespaceChars(" \t")
decvalue = Word( nums ).setWhitespaceChars(" \t")
hexvalue = Regex("0x[0-9a-f]+").setWhitespaceChars(" \t")
value = hexvalue | decvalue
assign = Literal("=").suppress()
type_ = Keyword("parameter") | Keyword("shutter") | Keyword("masked_shutter") | Keyword("trigger") | Keyword("var") | Keyword("counter") | Keyword("exitcode") | Keyword("address")
comparison = ( Literal("==") | Literal("!=") | Literal("<=") | Literal(">=") | Literal("<") | Literal(">")  )
addOperator = oneOf("+ -")
not_ = Keyword("not")

comparisonCommands = { "==": "CMPEQUAL",
                       "!=": "CMPNOTEQUAL",
                       "<": "CMPLESS",
                       ">": "CMPGREATER",
                       "<=": "CMPLE",
                       ">=": "CMPGE" }

shiftLookup = { "<<": "SHL", ">>": "SHR", "+": "ADDW", "-": "SUBW", "*": "MULTW", "/": 'DIVW' }

jmpNullCommands = { "==" : { True: "JMPZ", False: "JMPNZ"} ,
                    "!=" : { True: "JMPNZ", False: "JMPZ"},
                    ">" : {True: "JMPNZ", False: "JMPZ" } }

opassignmentLookup = { '+=': 'ADDW', '-=': 'SUBW', '*=': 'MULTW', '&=': 'ANDW', '|=': 'ORW', '>>=': "SHR", "<<=": "SHL", '/=': 'DIVW' }

from pppCompiler.Symbol import SymbolTable, FunctionSymbol, ConstSymbol, VarSymbol
#from .Symbol import SymbolTable, FunctionSymbol, ConstSymbol, VarSymbol

class CodeGenerator(object):
    def __call__(self):
        return "# CodeGenerator"

class WhileGenerator(CodeGenerator):
    def __init__(self, symbols, JMPCMD, block0, block1, block2 ):
        self.JMPCMD = JMPCMD
        self.block0 = block0
        self.block1 = block1
        self.block2 = block2
        self.symbols = symbols
        
    def __call__(self):
        labelNumber = self.symbols.getLabelNumber()
        topLabel = "while_label_{0}".format(labelNumber)
        endLabel = "end_while_label_{0}".format(labelNumber)
        code = list(self.block0)
        code.append("{0}: NOP".format(topLabel))
        code.extend( self.block1 )
        code.append("  {1} {0}".format(endLabel, self.JMPCMD))
        code.extend( self.block2 )
        code.extend([ "  JMP {0}".format(topLabel), "{0}: NOP".format(endLabel), "# end while" ])
        return code

class IfGenerator(CodeGenerator):
    def __init__(self, symbols, JMPCMD, block0, block1, block2 ):
        self.JMPCMD = JMPCMD
        self.block0 = block0
        self.block1 = block1
        self.block2 = block2
        self.symbols = symbols
        
    def __call__(self):
        labelNumber = self.symbols.getLabelNumber()
        elseLabel = "else_label_{0}".format( labelNumber )
        endifLabel = "end_if_label_{0}".format( labelNumber )
        code = list(self.block0)
        if self.block2 is None:
            code.append("  {1} {0}".format(endifLabel, self.JMPCMD))
            code.append( "# IF block")
            code.extend( self.block1 )
            code.append( "{0}: NOP".format(endifLabel))
        else:
            code.append("  {1} {0}".format(elseLabel, self.JMPCMD))
            code.append( "# IF block")
            code.extend( self.block1 )
            code += ["  JMP {0}".format(endifLabel),
                     "{0}: NOP".format(elseLabel),
                     "# ELSE block" ]
            code.extend( self.block2 )
            code.append( "{0}: NOP".format(endifLabel) )
        code.append( "# end if" )
        return code

def generate(l):
    for el in l:
        if isinstance(el, CodeGenerator):
            for sub in generate( el() ):
                yield sub
        else:
            yield el

def list_rtrim( l, trimvalue=None ):
    """in place list right trim"""
    while len(l)>0 and l[-1]==trimvalue:
        l.pop()
    return l
    

def find_and_get( parse_result, key ):
    result = parse_result
    if key in result:
        return result[key]
    while isinstance(result, ParseResults) and len(result)==1:
        result = result[0]
        if key in result:
            return result[key]
    return None


def is_power2(num):
    return ((num & (num - 1)) == 0) and num > 0


class pppCompiler:
    def __init__(self):
        self.initBNF()
        self.symbols = SymbolTable()
        
    def initBNF(self):
        indentStack = [1]
        encoding = Literal("<").suppress() + identifier("encoding") + Literal(">").suppress()
        constdecl = Group((const + identifier + assign + value).setParseAction(self.const_action))
        vardecl = Group((type_("type_") + Optional(encoding) + identifier("name") +  
                   Optional( assign + value("value") + Optional( identifier )("unit") ) ).setParseAction(self.var_action))
        insertdecl = Group((insert + dblQuotedString + LineEnd().suppress()).setParseAction(self.insert_action))
        procedurecall = Group((identifier + Literal("(").suppress() + Optional( delimitedList( (identifier  + Optional( assign + identifier )).setParseAction(self.named_param_action) ) ) 
                                 + Literal(")").suppress() ).setParseAction(self.procedurecall_action))
        condition = Group((identifier("leftidentifier") + comparison("comparison") + (identifier("identifier") | value.setParseAction(self.value_action))).setParseAction(self.condition_action))("condition")
        pointer = Literal("*") + identifier

        rExp = Forward()
        #numexpression = Forward()
        
        opexpression = (identifier("operand") + ( Literal(">>") | Literal("<<") | Literal("+") | Literal("*") | Literal("/") | Literal("-"))("op") + Group(rExp)("argument")).setParseAction(self.opexpression_action)
        rExp << ( procedurecall | opexpression | identifier("identifier") | value.setParseAction(self.value_action) | 
                  #Group( Suppress("(") + rExp + Suppress(")") ) |
                  #Group( "+" + rExp) |
                  #Group( "-" + rExp) |
                  Group( Literal("not") + rExp) )
        rExpCondition =  Group((Optional(not_)("not_")+rExp("rExp"))).setParseAction(self.rExp_condition_action)("condition")
        rExp.setParseAction(self.rExp_action)
        
        assignment = ((identifier | pointer)("lval") + assign + rExp("rval")).setParseAction(self.assignment_action)
        addassignment = (( identifier | pointer )("lval") + ( Literal("+=") | Literal("-=") | Literal("*=") | Literal("&=") | Literal("|=") | Literal(">>=") | Literal("/=") | Literal("<<="))("op") + Group(rExp)("rval")).setParseAction(self.addassignement_action)
        
        statement = Forward()
        statementBlock = indentedBlock(statement, indentStack).setParseAction(self.statementBlock_action)
        procedure_statement = Group( (Keyword("def").suppress() + identifier("funcname") + Literal("(").suppress() + Literal(")").suppress() + colon.suppress()
                                + statementBlock).setParseAction(self.def_action) )
        while_statement = Group((Keyword("while").suppress() + (condition | rExpCondition)("condition")  + colon.suppress() + statementBlock("statementBlock") ).setParseAction(self.while_action))
        if_statement = (Keyword("if") + condition + colon + statementBlock("ifblock") + 
                        Optional(Keyword("else").suppress()+ colon +statementBlock("elseblock")) ).setParseAction(self.if_action)
        statement << (procedure_statement | while_statement | if_statement | procedurecall | assignment | addassignment)
        
        decl = constdecl | vardecl | insertdecl | Group(statement)
        
        self.program = ZeroOrMore(decl)
        self.program.ignore(pythonStyleComment)
    
    def assignment_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "assignment_action {0} {1}".format( lineno(loc, text), arg ))
        try:
            code = [ "# line {0} assignment {1}".format(lineno(loc, text), line(loc, text)) ]
            rval_code = find_and_get(arg.rval, 'code')
            if rval_code is not None:
                code += arg.rval.code
            elif arg.rval=="*P":
                code.append( "  LDWI" )
            elif 'identifier'in arg:
                self.symbols.getVar( arg.identifier )
                code.append(  "  LDWR {0}".format(arg.identifier))
            if arg.lval=="*P":
                code.append( "  STWI" )
            elif arg.lval!="W":
                symbol = self.symbols.getVar(arg.lval)
                code.append( "  STWR {0}".format(symbol.name))
            if 'code' in arg:
                arg['code'].extend( code )
            else:
                arg['code'] = code
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        return arg
        
    def addassignement_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "addassignement_action {0} {1}".format( lineno(loc, text), arg ))
        try:
            code = [ "# line {0}: add_assignment: {1}".format(lineno(loc, text), line(loc, text)) ]
            if arg.rval[0]=='1' and arg.op in ['+=', '-=']:
                self.symbols.getVar(arg.lval)
                if arg.op=="+=":
                    code.append("  INC {0}".format(arg.lval))
                else:
                    code.append("  DEC {0}".format(arg.lval))
            else:
                if 'code'in arg.rval:
                    code += arg.rval.code
                    self.symbols.getVar(arg.lval)
                    if arg.op=="-=":
                        raise CompileException("-= with expression needs to be fixed in the compiler")
                    code.append( "  {0} {1}".format(opassignmentLookup[arg.op], arg.lval))
                elif 'identifier' in  arg.rval:
                    self.symbols.getVar(arg.rval.identifier)
                    code.append("  LDWR {0}".format(arg.lval))
                    self.symbols.getVar(arg.lval)
                    code.append( "  {0} {1}".format(opassignmentLookup[arg.op], arg.rval.identifier))
            code.append("  STWR {0}".format(arg.lval))
            arg['code'] = code
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        return arg
   
    def condition_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "condition_action {0} {1}".format( lineno(loc, text), arg ))
        try:
            code = [ "# line {0} condition {1}".format(lineno(loc, text), line(loc, text)) ]
            if arg.leftidentifier!="W":
                self.symbols.getVar(arg.leftidentifier)
                code.append('  LDWR {0}'.format(arg.leftidentifier))
            if arg.identifier=='NULL' and arg.comparison in jmpNullCommands:
                arg['jmpcmd'] = jmpNullCommands[arg.comparison]
            else:
                code.append('  {0} {1}'.format(comparisonCommands[arg.comparison], arg.identifier))
            arg["code"] = code
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        return arg
    
    def rExp_condition_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "rExp_condition_action {0} {1}".format( lineno(loc, text), arg ))
        try:
            code = [ "# line {0} rExp_condition {1}".format(lineno(loc, text), line(loc, text)) ]
            condition_code = arg.condition.rExp['code'] 
            if isinstance(condition_code, str):
                if 'not_' in arg['condition']:
                    code += [ "  CMPEQUAL NULL" ]
                else:
                    code += ["  CMPNOTEQUAL NULL"]
                arg['code'] = code
            else:
                if 'not_' in arg['condition']:
                    arg['code'] = { False: condition_code[True], True: condition_code[False] }
                else:
                    arg['code'] = condition_code
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        return arg
    
    def named_param_action(self, text, loc, arg):
        if len(arg)==2:
            arg[ arg[0] ] = arg[1]
        return arg
        
    def value_action(self, text, loc, arg):
        if arg[0][0:2]=='0x':
            value = int(arg[0], 16)
        else:
            value = int(arg[0])
        arg["identifier"] = self.symbols.getInlineParameter("inlinevar", value)
        return arg
        
    def opexpression_action(self, text, loc, arg):
        try:
            logging.getLogger(__name__).debug( "opexpression_action {0} {1}".format( lineno(loc, text), arg ))
            code = [  "# line {0}: shiftexpression {1}".format(lineno(loc, text), line(loc, text)),
                      "  LDWR {0}".format(arg.operand), "  {0} {1}".format(shiftLookup[arg.op], arg.argument.identifier)]
            arg['code'] = code
            logging.getLogger(__name__).debug( "shiftexpression generated code {0}".format(code))
        except Exception as e:
            raise CompileException(text, loc, str(e), self)
        return arg
        
    def procedurecall_action(self, text, loc, arg):
        try:
            logging.getLogger(__name__).debug( "procedurecall_action {0} {1}".format( lineno(loc, text), arg ))
            procedure = self.symbols.getProcedure(arg[0])
            code = [ "# line {0}: procedurecall {1}".format(lineno(loc, text), line(loc, text)) ]
            opcode = procedure.codegen(self.symbols, arg=arg.asList(), kwarg=arg.asDict())
            if isinstance(opcode, list):
                code += opcode
            else:
                code = opcode
            arg['code'] = code
            logging.getLogger(__name__).debug( "procedurecall generated code {0}".format(code))
        except Exception as e:
            raise CompileException(text, loc, str(e), self)
        return arg
        
    def rExp_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "rExp_action {0} {1}".format( lineno(loc, text), arg ))
        pass
        
    def if_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "if_action {0} {1}".format( lineno(loc, text), arg ))
        try:
            block0 = ["# line {0} if statement {1}".format(lineno(loc, text), line(loc, text)) ]
            if isinstance(arg.condition.code, list):
                block0 += arg.condition.code
                JMPCMD = arg.condition.get( 'jmpcmd', {False: "JMPNCMP"} )[False]
            else:
                JMPCMD = arg.condition.code[True]            

            if 'elseblock' in arg:
                block1 =  arg.ifblock.ifblock.code
                block2 = arg.elseblock.elseblock['code'] if 'elseblock' in arg.elseblock else arg.elseblock['code']
            else: 
                block1 = arg.ifblock.ifblock['code']
                block2 = None
            arg['code'] = [ IfGenerator( self.symbols, JMPCMD, block0, block1, block2 ) ]
        except Exception as e:
            raise CompileException(text, loc, str(e), self)                        
        return arg
        
    def while_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "while_action {0} {1}".format( lineno(loc, text),  arg ))
        try:
            block0 = [ "# line {0} while_statement {1}".format(lineno(loc, text), line(loc, text))]
            if 'code' in arg.condition:
                if isinstance(arg.condition.code, list):
                    block1 = arg.condition.code
                    JMPCMD = arg.condition.get('jmpcmd', {False: "JMPNCMP"} )[False]
                else:
                    JMPCMD = arg.condition.code[True]  
                    block1 = []          
            elif 'rExp' in arg.condition and 'code' in arg.condition.rExp:
                if isinstance(arg.condition.rExp.code, list):
                    block1 = arg.condition.rExp.code
                    JMPCMD = arg.condition.rExp.get('jmpcmd', "JMPNCMP" )
                else:
                    JMPCMD = arg.condition.rExp.code[True]     
                    block1 = []       
            block2 = arg.statementBlock.statementBlock['code']
                        
            arg['code'] =  [ WhileGenerator(self.symbols, JMPCMD, block0, block1, block2) ]
            logging.getLogger(__name__).debug( "while_action generated code ")
        except Exception as e:
            raise CompileException(text, loc, str(e), self)                        
        return arg
        
    def statementBlock_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "statementBlock_action {0} {1} {2}".format( lineno(loc, text), arg.funcname, arg ))
        try:
            code = list()
            for command in arg[0]:
                if 'code'in command:
                    code += command['code']
                elif 'code' in command[0]:
                    code += command[0]['code']
            arg[0]['code'] = code
            logging.getLogger(__name__).debug( "statementBlock generated code {0}".format(code))
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        return arg
        
    def def_action(self, text, loc, arg):
        logging.getLogger(__name__).debug( "def_action {0} {1} {2}".format( lineno(loc, text), arg.funcname, arg ))
        try:
            name = arg[0]
            self.symbols.checkAvailable(name)
            self.symbols[name] = FunctionSymbol(name, arg[1]['code']) 
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
       
    def const_action( self, text, loc, arg ):
        try:
            name, value = arg
            logging.getLogger(__name__).debug( "const_action {0} {1} {2} {3}".format(self.currentFile, lineno(loc, text), name, value) )
            self.symbols[name] = ConstSymbol(name, value)
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        
    def var_action( self, text, loc, arg):
        logging.getLogger(__name__).debug( "var_action {0} {1} {2} {3} {4} {5} {6}".format(self.currentFile, lineno(loc, text), arg["type_"], arg.get("encoding"), arg["name"], arg.get("value"), arg.get("unit") ) )
        try:
            type_ = arg["type_"] if arg["type_"]!="var" else None
            self.symbols[arg["name"]] = VarSymbol( type_=type_, name=arg["name"], value=arg.get("value"), encoding=arg.get("encoding"), unit=arg.get("unit") )
        except Exception as e:
            raise CompileException(text, loc, str(e), self)            
        
    def insert_action( self, text, loc, arg ):
        try:
            oldfile = self.currentFile
            myprogram = self.program.copy()
            self.currentFile = arg[0][1:-1]
            result = myprogram.parseFile( self.currentFile )
            self.currentFile = oldfile
        except Exception as e:
            raise CompileException(text, loc, str(e), self)                    
        return result
    
    def compileFile(self, filename):
        self.currentFile = filename
        result = self.program.parseFile( self.currentFile, parseAll=True )

        allcode = list()
        for element in result:
            if not isinstance(element, str) and 'code' in element:
                allcode += element['code']
            elif not isinstance(element[0], str) and 'code' in element[0]:
                allcode += element[0]['code']
        header = self.createHeader()        

        codetext = "\n".join(header + allcode)
        return codetext

    def compileString(self, programText):
        self.programText = programText
        self.currentFile = "Memory"
        result = self.program.parseString( self.programText, parseAll=True )

        allcode = list()
        for element in result:
            if not isinstance(element, str) and 'code' in element:
                allcode += element['code']
            elif not isinstance(element[0], str) and 'code' in element[0]:
                allcode += element[0]['code']
        header = self.createHeader() 
        codetext = """# autogenerated 
# DO NOT EDIT DIRECTLY
# The file will be overwritten by the compiler
#
"""   
        codetext += "\n".join(header + list(generate(allcode)))
        self.reverseLineLookup = self.generateReverseLineLookup( codetext )
        return codetext
    
    def generateReverseLineLookup(self, codetext):
        lookup = dict()
        sourceline = None
        for codeline, line in enumerate(codetext.splitlines()):
            m = re.search('^\# line (\d+).*$', line)
            if m:
                sourceline = int(m.group(1))
            else:
                lookup[codeline+1] = sourceline
        return lookup
    
    def createHeader(self):
        header = [ "# const values" ]
        for constval in self.symbols.getAllConst():
            header.append("const {0} {1}".format(constval.name, constval.value))
        header.append( "# variables ")
        for var in self.symbols.getAllVar():
            if var.type_ == "masked_shutter":
                header.append("var {0} {1}, {2}".format(var.name+"_mask", var.value if var.value is not None else 0, "mask"))
                header.append("var {0} {1}, {2}".format(var.name, var.value if var.value is not None else 0, "shutter {0}_mask".format(var.name)))
            else:
                optionals =  [s if s is not None else "" for s in list_rtrim([var.type_, var.unit, var.encoding])]
                varline = "var {0} {1}".format(var.name, var.value if var.value is not None else 0)
                if len(optionals)>0:
                    varline += ", " + ", ".join(optionals)
                header.append(varline)
        header.append("# inline variables")
#         for value, name in self.symbols.inlineParameterValues.items():
#             header.append("var {0} {1}".format(name, value))
        header.append( "# end header")
        header.append( "" )        
        return header

def pppcompile( sourcefile, targetfile, referencefile ):
    import difflib
    import os.path
    try:
        with open(sourcefile, "r") as f: 
            sourcecode = f.read()
        compiler = pppCompiler()
        assemblercode = compiler.compileString(sourcecode )
        with open(targetfile, "w") as f:
            f.write(assemblercode)
    except CompileException as e:
        print(str(e))
        print(e.line())
    # compare result to reference
    comppass = None
    if os.path.exists( referencefile ):
        with open(referencefile, "r") as f:
            referencecode = f.read()
        comppass = True
        for line in difflib.unified_diff(referencecode.splitlines(), assemblercode.splitlines()):
            print(line)
            comppass = False
    return comppass

def pppCompileString(sourcecode):
    compiler = pppCompiler()
    return compiler.compileString(sourcecode)


