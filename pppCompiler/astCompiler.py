# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ast
import copy
import re
import difflib
from pathlib import Path
from collections import deque, defaultdict, Counter, OrderedDict, UserList
from .astSymbol import SymbolTable, FunctionSymbol, ConstSymbol, VarSymbol, AssemblyFunctionSymbol, Builtin
from functools import partial
from .ppVirtualMachine import ppVirtualMachine, compareDicts, evalRawCode
from .pppCompiler import pppCompiler as oldpppCompiler

#List of all supported AST visitor nodes
fullASTPrimitives = {'AST', 'Add', 'And', 'Assert', 'Assign', 'AsyncFor', 'AsyncFunctionDef', 'AsyncWith', 'Attribute', 'AugAssign',
    'AugLoad', 'AugStore', 'Await', 'BinOp', 'BitAnd', 'BitOr', 'BitXor', 'BoolOp', 'Break', 'Bytes', 'Call', 'ClassDef',
    'Compare', 'Continue', 'Del', 'Delete', 'Dict', 'DictComp', 'Div', 'Ellipsis', 'Eq', 'ExceptHandler', 'Expr',
    'Expression', 'ExtSlice', 'FloorDiv', 'For', 'FunctionDef', 'GeneratorExp', 'Global', 'Gt', 'GtE', 'If', 'IfExp',
    'Import', 'ImportFrom', 'In', 'Index', 'Interactive', 'Invert', 'Is', 'IsNot', 'LShift', 'Lambda', 'List', 'ListComp',
    'Load', 'Lt', 'LtE', 'MatMult', 'Mod', 'Module', 'Mult', 'Name', 'NameConstant', 'NodeTransformer', 'NodeVisitor',
    'Nonlocal', 'Not', 'NotEq', 'NotIn', 'Num', 'Or', 'Param', 'Pass', 'Pow', 'PyCF_ONLY_AST', 'RShift', 'Raise', 'Return',
    'Set', 'SetComp', 'Slice', 'Starred', 'Store', 'Str', 'Sub', 'Subscript', 'Suite', 'Try', 'Tuple', 'UAdd', 'USub',
    'UnaryOp', 'While', 'With', 'Yield', 'YieldFrom'}

#List of visitor nodes supported in ppp
allowedASTPrimitives = {'Add', 'Sub','And', 'Assign', 'AugAssign', 'BinOp', 'BitAnd', 'BitOr', 'Break','Call', 'Compare', 'BoolOp', 'Div',
                        'Eq', 'Expr', 'Expression', 'FunctionDef', 'Gt', 'GtE', 'If', 'IfExp', 'Load', #'Lambda',
                        'LShift', 'Lt', 'LtE', 'Mod', 'Module', 'Mult', 'Name', 'NameConstant', 'Not', 'NotEq',
                        'Num', 'Or', 'Pass', 'RShift', 'Return',
                        'Store', 'Str', 'Sub', 'Suite', 'UAdd', 'USub', 'UnaryOp', 'While' }

ComparisonLUT = {ast.Gt:    "CMPGREATER",
                 ast.GtE:   "CMPGE",
                 ast.Lt:    "CMPLESS",
                 ast.LtE:   "CMPLE",
                 ast.Eq:    "CMPEQUAL",
                 ast.NotEq: "CMPNOTEQUAL"}

reverseJMPLUT = {"  JMPRAMVALID": "  JMPRAMINVALID",
                 "  JMPRAMINVALID": "  JMPRAMVALID",
                 "  JMPPIPEEMPTY": "  JMPPIPEAVAIL",
                 "  JMPPIPEAVAIL": "  JMPPIPEEMPTY" }

def list_rtrim( l, trimvalue=None ):
    """in place list right trim"""
    while len(l)>0 and l[-1]==trimvalue:
        l.pop()
    return l

def is_power2(num):
    return num and (num & (num - 1) == 0)

def ln_of_power2(num):
    if not is_power2(num):
        raise ValueError("ln_of_power2 needs power of 2 as input")
    power = 0
    while num:
        num >>= 1
        power += 1
    return power - 1

class OrderedSet(UserList):
    """Not really a set, more of a list that only contains unique elements"""
    def add(self, other):
        if other not in self.data:
            self.data.append(other)

class CompileException(Exception):
    def __init__(self, message, obj=None):
        self.message = message
        if obj and hasattr(obj, 'lineno'):
            self.lineno = "Exception on line {} of ppp file: ".format(obj.lineno)
        else:
            self.lineno = ""
        super().__init__(self.lineno+self.message)

def illegalLambda(error_message):
    """Generic function for unsupported visitor methods"""
    def gencall(self, node):
        raise CompileException("{} not supported!".format(error_message), node)
        self.generic_visit(node)
    return gencall

class astMeta(type):
    """metaclass for instantiating visitor functions that handle illegal calls"""
    def __new__(cls, name, bases, attrs):
        baseattrs = dict(attrs)
        baseattrs.update({"visit_{0}".format(name): illegalLambda(name) for name in fullASTPrimitives-allowedASTPrimitives})
        return super().__new__(cls, name, bases, baseattrs)

class pppCompiler(ast.NodeTransformer, metaclass=astMeta):
    def __init__(self, optimizePassByReference=True):
        self.builtinBool = None
        self.codestr = []
        self.maincode = []
        self.funcDeps = defaultdict(set)
        self.localNameSpace = deque()
        self.funcNames = OrderedSet()
        self.chameleonLabelsDeque = deque()
        self.lvctr = 1        #inline declaration counter
        self.ifctr = 10       #number of if statements
        self.elsectr = 10     #number of else statements
        self.whilectr = 10    #number of while statements
        self.fnctr = 10
        self.orctr = 10
        self.symbols = SymbolTable()
        self.localVarDict = dict()
        self.preamble = ""
        self.labelCounter = Counter()
        self.loopLabelStack = deque()
        self.leftlist = []
        self.rightlist = []
        self.oplist = []
        self.boolList = []
        self.boolLineNo = []
        self.returnSet = set() #list of functions with return values
        self.requiredReturnCalls = set()
        self.enableOptimizations = True
        self.passToOldPPPCompiler = False
        self.gt02bool = False
        self.inlineAll = True
        self.EnableNumericLabels = False
        FunctionSymbol.passByReferenceCheckCompleted = not optimizePassByReference
        self.ppRegexStr = r"# PPP LINE: +\d+"
        self.pplinnoColW = 105
        self.codeFmtStr = "{0:80} # PPP LINE: {1:>4}"
        self.numberInitLines = 0

    def _ppFormatLine(self, code, lineno):
        return self.codeFmtStr.format(code, lineno+self.numberInitLines)

    def ppFormatLine(self, code, lineno):
        if isinstance(code, list):
            return list(map(lambda c: self.ppFormatLine(c, lineno), code))
        elif '\n' in code:
            return '\n'.join(self.ppFormatLine(code.split('\n'), lineno))
        return self._ppFormatLine(code, lineno)

    def safe_generic_visit(self, node):
        """Modified generic_visit call, currently just returning generic_visit directly"""
        self.generic_visit(node)

    def valLUT(self, obj):
        """Look for preexisting variables in local and global scopes, if return value is a number then
           return a flag that instantiates an inline variable or can be handled later"""
        if isinstance(obj, ast.Num):
            if obj.n == 0:
                return 'NULL', False
            return obj.n, True
        elif isinstance(obj, ast.Name):
            if self.localNameSpace:
                for ns in reversed(self.localNameSpace):
                    localname = ns+"_"+obj.id
                    if localname in self.symbols.keys():
                        return self.symbols[localname].name, False
                if obj.id in self.symbols.keys():
                    return self.symbols[obj.id].name, False
                return self.localNameSpace[-1]+'_'+obj.id, False
        elif isinstance(obj, ast.Call):
            return obj.func.id, False
        elif isinstance(obj, ast.NameConstant):
            if obj.value:
                return 1, True
            else:
                return 0, True
        if hasattr(obj, 'id'):
            return obj.id, False
        else:
            raise CompileException("Can't get a value from {0} object on line {1}".format(obj.__class__, obj.lineno))

    def localVarHandler(self, nv):
        """Looks up pre-existing variables and declares undeclared variables"""
        right, localvar = self.valLUT(nv)
        if localvar:
            if right in self.localVarDict.keys(): #checks if inlinevar of the same value has already been created
                return self.localVarDict[right], localvar
            else:
                self.symbols.setInlineParameter(name="inlinevar_{0}".format(self.lvctr), value=right)
                self.localVarDict[right] = "inlinevar_{0}".format(self.lvctr)
                right = "inlinevar_{0}".format(self.lvctr)
                self.lvctr += 1
        return right, localvar

    def visit_Assign(self, node):
        """Node visitor for variable assignment"""
        if len(node.targets) == 1 and hasattr(node.targets[0],'id'):
            target,_ = self.valLUT(node.targets[0])
            if target not in self.symbols.keys():
                self.symbols[target] = VarSymbol(name=target, value=0)
            if any(map(lambda t: isinstance(node.value, t), [ast.Name, ast.Num, ast.NameConstant])):
                right,_ = self.localVarHandler(node.value)
                self.codestr += [self.ppFormatLine("LDWR {0}".format(right), node.lineno)]
        self.safe_generic_visit(node)
        self.codestr += [self.ppFormatLine("STWR {0}".format(target), node.lineno)]
        if not self.localNameSpace:
            self.maincode += self.codestr
            self.codestr = []

    def visit_AugAssign(self, node):
        """Node visitor for augmented assignment, eg x += 1"""
        if 'n' in node.value._fields:
            nodetid = "_".join(self.localNameSpace+deque(node.target.id))
            if nodetid not in self.symbols.keys():
                nodetid = node.target.id
            n_value = node.value.n
        else:
            nodetid, _ = self.localVarHandler(node.target)
            n_value = None
        nodevid, _ = self.localVarHandler(node.value)
        self.codestr += [self.ppFormatLine("LDWR {}".format(nodetid), node.lineno)]
        if isinstance(node.op, ast.Add):
            if n_value == 1:
                self.codestr += self.ppFormatLine("INC {0}\nSTWR {0}".format(nodetid).split('\n'), node.lineno)
            else:
                self.codestr += self.ppFormatLine("ADDW {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.Sub):
            if n_value == 1:
                self.codestr += self.ppFormatLine("DEC {0}\nSTWR {0}".format(nodetid).split('\n'), node.lineno)
            else:
                self.codestr += self.ppFormatLine("SUBW {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.Mult):
            if is_power2(n_value):
                node.value.n = ln_of_power2(n_value)
                nodevid, _ = self.localVarHandler(node.value)
                self.codestr += self.ppFormatLine("SHL {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
            else:
                self.codestr += self.ppFormatLine("MULTW {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.Div):
            if is_power2(n_value):
                node.value.n = ln_of_power2(n_value)
                nodevid, _ = self.localVarHandler(node.value)
                self.codestr += self.ppFormatLine("SHR {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
            else:
                self.codestr += self.ppFormatLine("DIVW {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.RShift):
            self.codestr += self.ppFormatLine("SHR {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.LShift):
            self.codestr += self.ppFormatLine("SHL {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.BitAnd):
            self.codestr += self.ppFormatLine("ANDW {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        elif isinstance(node.op, ast.BitOr):
            self.codestr += self.ppFormatLine("ORW {0}\nSTWR {1}".format(nodevid, nodetid).split('\n'), node.lineno)
        self.safe_generic_visit(node)
        if not self.localNameSpace:
            self.maincode += self.codestr
            self.codestr = []

    def visit_BinOp(self, node):
        """Node visitor for binary (inline) operations like +,-,*,&,|,<<,>>"""
        nodetid,_ = self.localVarHandler(node.left)
        nodevid,_ = self.localVarHandler(node.right)
        self.codestr += [self.ppFormatLine("LDWR {}".format(nodetid), node.lineno)]
        if isinstance(node.op, ast.Add):
            self.codestr += [self.ppFormatLine("ADDW {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.Sub):
            self.codestr += [self.ppFormatLine("SUBW {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.Mult):
            if isinstance(node.right, ast.Num) and is_power2(node.right.n):
                node.right.n = ln_of_power2(node.right.n)
                nodevid, _ = self.localVarHandler(node.right)
                self.codestr += [self.ppFormatLine("SHL {0}".format(nodevid), node.lineno)]
            else:
                self.codestr += [self.ppFormatLine("MULTW {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Num) and is_power2(node.right.n):
                node.right.n = ln_of_power2(node.right.n)
                nodevid, _ = self.localVarHandler(node.right)
                self.codestr += [self.ppFormatLine("SHR {0}".format(nodevid), node.lineno)]
            else:
                self.codestr += [self.ppFormatLine("DIVW {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.RShift):
            self.codestr += [self.ppFormatLine("SHR {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.LShift):
            self.codestr += [self.ppFormatLine("SHL {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.BitAnd):
            self.codestr += [self.ppFormatLine("ANDW {0}".format(nodevid), node.lineno)]
        elif isinstance(node.op, ast.BitOr):
            self.codestr += [self.ppFormatLine("ORW {0}".format(nodevid), node.lineno)]
        self.safe_generic_visit(node)

    def visit_Compare(self, node):
        """handles boolean comparisons (>,<,!=,...) and iterates through all comparators for cases
           such as 10 < y < 20"""
        leftiter = node.left
        cmpcnt = 0
        for rightiter, opiter in zip(node.comparators, node.ops):
            cmpcnt += 1
            if isinstance(leftiter, ast.Call):
                currentcodestr = copy.copy(self.codestr)
                self.codestr = []
                self.visit_Call(leftiter)
                left = [leftiter.func.id, copy.copy(self.codestr)]
                self.codestr = copy.copy(currentcodestr)
            else:
                left,_ = self.localVarHandler(leftiter)
            right,_ = self.localVarHandler(rightiter)
            if opiter.__class__ in ComparisonLUT.keys():
                op = ComparisonLUT[opiter.__class__]
            else:
                raise CompileException("Objects of type {} not supported!".format(opiter.__class__), node)
            leftiter = rightiter
            self.compTestPush(False, left, right, op, node.lineno)

    def checkIfBuiltinWithReturn(self,node, boolVal):
        """Special function that handles the dictionary output from pipe_empty and read_ram_valid builtins"""
        op = None
        returncodestr = None
        if hasattr(node, 'func'):
            if node.func.id in ['pipe_empty','read_ram_valid']:
                procedure = self.symbols.getProcedure(node.func.id)
                retdict = procedure.codegen(self.symbols, arg=[node.func.id], kwarg=dict())
                if isinstance(retdict, dict): #special case for dealing with dicts returned by pipe_empty/read_ram_valid
                    op = retdict[boolVal]
            else:
                currentcodestr = copy.copy(self.codestr)
                self.codestr = []
                self.visit_Call(node)
                returncodestr = [node.func.id, copy.copy(self.codestr)]
                self.codestr = copy.copy(currentcodestr)
        return op, returncodestr

    def visit_BoolOp(self, node):
        """visitor for boolean operators such as and/or"""
        for n in node.values:
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
                op, retstr = self.checkIfBuiltinWithReturn(n.operand, True)
                if op:
                    raise CompileException("{} not currently supported with other boolean statements!".format(n.operand.func.id), n)
                elif retstr:
                    left = retstr
                    right, op = None, 'N'
                else:
                    left,_ = self.localVarHandler(n.operand)
                    right, op = None, 'N'
                self.compTestPush(True if isinstance(node.op, ast.Or) else False, left, right, op, node.lineno)
            elif isinstance(n, ast.Name) or isinstance(n, ast.NameConstant):
                left,_ = self.localVarHandler(n)
                right, op = None, ''
                self.compTestPush(True if isinstance(node.op, ast.Or) else False, left, right, op, node.lineno)
            elif isinstance(n, ast.Call):
                op, retstr = self.checkIfBuiltinWithReturn(n, False)
                if op:
                    raise CompileException("{} not current supported with other boolean statements!".format(n.operand.func.id), n)
                elif retstr:
                    left = retstr
                    right, op = None, ''
                self.compTestPush(True if isinstance(node.op, ast.Or) else False, left, right, op, node.lineno)
            else:
                currentCompTestPushLen = len(self.boolList)
                self.visit(n)
                if len(self.boolList) > currentCompTestPushLen:
                    self.boolList[-1] = True if isinstance(node.op, ast.Or) else False

    def compTestPush(self, boolVal, leftVal, rightVal, opVal, lineno):
        """helper function to deal with multiple boolean statements in if and while tests"""
        self.leftlist.append(leftVal)
        self.rightlist.append(rightVal)
        self.oplist.append(opVal)
        self.boolList.append(boolVal)
        self.boolLineNo.append(lineno)

    def compTestClear(self):
        """helper function to clear multiple boolean statements once they've been parsed"""
        self.boolList.clear()
        self.rightlist.clear()
        self.leftlist.clear()
        self.oplist.clear()
        self.boolLineNo.clear()

    def visit_IfTests(self, node):
        """intermediate visitor for handling boolean tests in if and while statements"""
        if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
            op, retstr = self.checkIfBuiltinWithReturn(node.test.operand, True)
            if op:
                left, right = None, None
                self.compTestPush(False, left, right, op, node.lineno)
            elif retstr:
                left = retstr
                right, op = None, 'N'
                self.compTestPush(False, left, right, op, node.lineno)
            else:
                left,_ = self.localVarHandler(node.test.operand)
                self.compTestPush(False, left, None, 'N', node.lineno)
        elif isinstance(node.test, ast.Name) or isinstance(node.test, ast.NameConstant):
            left,_ = self.localVarHandler(node.test)
            self.compTestPush(False, left, None, '', node.lineno)
        elif isinstance(node.test, ast.Call):
            op, retstr = self.checkIfBuiltinWithReturn(node.test, False)
            if op:
                left, right = None, None
                self.compTestPush(False, left, right, op, node.lineno)
            elif retstr:
                left = retstr
                right, op = None, ''
                self.compTestPush(False, left, right, op, node.lineno)
        else:
            self.visit(node.test)

    def testStatementHandler(self, label1, label2):
        """generates assembly for boolean arguments for if and while loops, handles special JMP types 
           as well as and/or statements with multiple boolean tests"""
        self.boolList[-1] = False
        totalOrs = sum(self.boolList)
        orcnt = 0
        orLabelNeeded = False
        orlabel = "or_label_{0}".format(self.orctr)
        for ind,orStatement,right,left,op,lineno in zip(list(reversed(range(len(self.leftlist)))), self.boolList, self.rightlist, self.leftlist, self.oplist, self.boolLineNo):
            if orStatement:
                orcnt += 1
                if left is None:
                    self.codestr += self.ppFormatLine("{0} {1}".format(reverseJMPLUT[op],label1).split('\n'), lineno)
                    continue
                elif isinstance(left, list):
                    self.requiredReturnCalls.add(left[0])
                    self.codestr += self.ppFormatLine(left[1], lineno)
                else:
                    self.codestr += self.ppFormatLine(["LDWR {0}".format(left)], lineno)
                if ind:
                    if right is None:
                        self.codestr += self.ppFormatLine(["JMP{0}Z {1}".format('' if op else 'N',label1)], lineno)
                    else:
                        self.codestr += self.ppFormatLine("{0} {1}\nJMPCMP {2}".format(op,right,label1).split('\n'), lineno)
                else:
                    if left is None:
                        self.codestr += self.ppFormatLine(["{0} {1}".format(op,label2)], lineno)
                        continue
                    elif isinstance(left, list):
                        self.requiredReturnCalls.add(left[0])
                        self.codestr += self.ppFormatLine(left[1], lineno)
                    else:
                        self.codestr += self.ppFormatLine(["LDWR {0}".format(left)], lineno)
                    if right is None:
                        self.codestr += self.ppFormatLine(["JMP{0}Z {1}".format(op,label2)], lineno)
                    else:
                        self.codestr += self.ppFormatLine("{0} {1}\nJMPNCMP {2}".format(op,right,label2).split('\n'), lineno)
                if orLabelNeeded:
                    self.codestr += self.ppFormatLine([orlabel+": NOP"], lineno)
                    self.orctr += 1
                    orlabel = "or_label_{0}".format(self.orctr)
                    orLabelNeeded = False
            else:
                if left is None:
                    self.codestr += self.ppFormatLine("{0} {1}".format(op,label2).split('\n'), lineno)
                    continue
                elif isinstance(left, list):
                    self.requiredReturnCalls.add(left[0])
                    self.codestr += self.ppFormatLine(left[1], lineno)
                else:
                    self.codestr += self.ppFormatLine(["LDWR {0}".format(left)], lineno)
                if orcnt == totalOrs:
                    if right is None:
                        self.codestr += self.ppFormatLine(["JMP{0}Z {1}".format(op,label2)], lineno)
                    else:
                        self.codestr += self.ppFormatLine("{0} {1}\nJMPNCMP {2}".format(op,right,label2).split('\n'), lineno)
                else:
                    orLabelNeeded = True
                    if right is None:
                        self.codestr += self.ppFormatLine(["JMP{0}Z {1}".format(op,orlabel)], lineno)
                    else:
                        self.codestr += self.ppFormatLine("{0} {1}\nJMPNCMP {2}".format(op,right,orlabel).split('\n'), lineno)
        self.compTestClear()

    def visit_If(self, node):
        """Node visitor for if statements, handles else and elif statements via subnodes"""
        currentIfCtr = copy.copy(self.ifctr)
        appendStr = [self.ppFormatLine("end_if_label_{0}: NOP".format(currentIfCtr), node.lineno)]
        self.ifctr += 1
        self.compTestClear()
        self.visit_IfTests(node)
        prependStr = [self.ppFormatLine("begin_if_label_{0}: NOP".format(currentIfCtr), node.lineno)]
        if node.orelse:
            currentElseCtr = copy.copy(self.elsectr)
            appendElse = self.ppFormatLine("JMP end_if_label_{0}\nelse_label_{1}: NOP".format(currentIfCtr,currentElseCtr).split('\n'), node.lineno)
            self.elsectr += 1
            self.testStatementHandler('begin_if_label_{0}'.format(currentIfCtr), 'else_label_{0}'.format(currentElseCtr))
            self.codestr += prependStr
            if hasattr(node.body, '__iter__'):
                for subnode in node.body:
                    self.visit(subnode)
            else:
                self.visit(node.body)
            self.codestr += appendElse
            if hasattr(node.orelse, '__iter__'):
                for subnode in node.orelse:
                    self.visit(subnode)
            else:
                self.visit(node.orelse)
        else:
            self.testStatementHandler('begin_if_label_{0}'.format(currentIfCtr), 'end_if_label_{0}'.format(currentIfCtr))
            self.codestr += prependStr
            if hasattr(node.body, '__iter__'):
                for subnode in node.body:
                    self.visit(subnode)
            else:
                self.visit(node.body)
        self.codestr += appendStr
        if not self.localNameSpace:
            self.maincode += self.codestr
            self.codestr = []

    def visit_IfExp(self, node):
        """visitor for if expressions: x = y if z > 0 else w"""
        self.visit_If(node)

    def visit_Pass(self, node):
        """visitor for pass statements"""
        pass

    def visit_While(self, node):
        """Node visitor for while statements"""
        currentWhileCtr = copy.copy(self.whilectr)
        self.codestr += [self.ppFormatLine("begin_while_label_{}: NOP".format(currentWhileCtr), node.lineno)]
        self.compTestClear()
        self.visit_IfTests(node)
        self.testStatementHandler('begin_body_while_label_{0}'.format(currentWhileCtr), 'end_while_label_{0}'.format(currentWhileCtr))
        self.codestr += [self.ppFormatLine("begin_body_while_label_{0}: NOP".format(currentWhileCtr), node.lineno)]
        self.whilectr += 1
        self.loopLabelStack.append(["JMP end_while_label_{0}".format(currentWhileCtr)])
        self.safe_generic_visit(node)
        self.codestr += self.ppFormatLine("JMP begin_while_label_{0}\nend_while_label_{0}: NOP".format(currentWhileCtr).split('\n'), node.lineno)
        self.loopLabelStack.pop()
        if not self.localNameSpace:
            self.maincode += self.codestr
            self.codestr = []

    def visit_Break(self, node):
        """visitor for break statements"""
        if self.loopLabelStack:
            self.codestr += self.ppFormatLine(self.loopLabelStack[-1], node.lineno)
        self.safe_generic_visit(node)

    def visit_FunctionDef(self, node):
        """visitor for function definitions"""
        inline = False
        assy = False
        if node.decorator_list:
            if node.decorator_list[0].id == 'inline':
                inline = True
            elif node.decorator_list[0].id == 'assembly':
                assy = True
        if self.inlineAll:
            inline = True
        if node.name in self.symbols.keys():
            raise CompileException("Function {} has already been declared!".format(node.name), node)
        for arg in node.args.args:
            target = node.name+"_"+arg.arg
            self.symbols[target] = VarSymbol(name=target, value=0)
        defaults = []
        for default in node.args.defaults:
            defarg,_ = self.localVarHandler(default)
            defaults.append(defarg)
        fullarglist = [node.name+'_'+arg.arg for arg in node.args.args]
        arglist = []
        numargs = len(fullarglist)-len(defaults)
        for i,arg in enumerate(fullarglist):
            if i<numargs:
                arglist.append(arg)
            else:
                break
        kwarglist = OrderedDict(reversed(list(zip(reversed(fullarglist),reversed(defaults)))))
        self.localNameSpace.append(node.name) # push function context for maintaining local variable definitions
        self.funcNames.add(node.name)
        if len(set(self.localNameSpace)) != len(self.localNameSpace):
            print('RECURSION ERROR')
            raise CompileException('Recursion not supported!', node)
        self.safe_generic_visit(node)         # walk inner block
        self.localNameSpace.pop()             # pop function context
        self.codestr += [self.ppFormatLine("end_function_label_{}: NOP".format(self.fnctr), node.lineno)]
        self.fnctr += 1
        if assy:
            code = node.body[0].value.s
            self.symbols[node.name] = AssemblyFunctionSymbol(node.name, code, nameSpace=node.name, argn=arglist, kwargn=kwarglist, startline=node.lineno)
        else:
            self.symbols[node.name] = FunctionSymbol(node.name, copy.copy(self.codestr),
                                                     nameSpace=node.name, argn=arglist,
                                                     kwargn=kwarglist, symbols=self.symbols,
                                                     maincode=self, returnval=node.name in self.returnSet,
                                                     inline=inline, startline=node.lineno)
        self.codestr = []

    def visit_Call(self, node):
        """visitor for function calls"""
        if hasattr(node.func, 'id'):
            if self.localNameSpace:
                self.funcDeps[self.localNameSpace[-1]].add(node.func.id)
            if len(set(self.localNameSpace)) != len(self.localNameSpace):
                raise CompileException('Recursion not supported!', node)
            if node.func.id in self.symbols.keys(): # if the function has already been defined, incorporate its code directly
                procedure = self.symbols.getProcedure(node.func.id)
                if node.keywords:
                    kwdict = {kw.arg: self.localVarHandler(kw.value)[0] for kw in node.keywords}
                else:
                    kwdict = dict()
                arglist = [node.func.id]
                if node.args:
                    arglist += [self.localVarHandler(arg)[0] for arg in node.args]
                if node.func.id in ['pipe_empty','read_ram_valid']:
                    retdict = procedure.codegen(self.symbols, arg=arglist, kwarg=kwdict)
                    #raise CompileException("{0}() needs to be called in an if/while statement!".format(node.func.id))
                    #if isinstance(retdict, dict): #special case for dealing with dicts returned by pipe_empty/read_ram_valid
                        #self.codestr[-1] = retdict[self.builtinBool]+self.codestr[-1]
                else:
                    if isinstance(self.symbols[node.func.id], Builtin):
                        self.codestr += self.ppFormatLine(procedure.codegen(self.symbols, arg=arglist, kwarg=kwdict), node.lineno)
                    else:
                        self.codestr += procedure.codegen(self.symbols, arg=arglist, kwarg=kwdict)
                if True in self.codestr:
                    raise CompileException('Bool in codestr', node)
            else: # put in a placeholder that can be used to generate the assembly after the function is defined
                if node.keywords:
                    kwdict = {kw.arg: self.localVarHandler(kw.value)[0] for kw in node.keywords}
                else:
                    kwdict = dict()
                arglist = [node.func.id]
                if node.args:
                    arglist += [self.localVarHandler(arg)[0] for arg in node.args]
                self.codestr += [[self.symbols.getProcedure, node.func.id, arglist, kwdict]]
        self.safe_generic_visit(node)
        returncodestr = copy.copy(self.codestr)
        if not self.localNameSpace:
            self.maincode += self.codestr
            self.codestr = []
        return returncodestr

    def visit_Return(self, node):
        """Node visitor for return statements"""
        if isinstance(node.value, ast.Call):
            self.visit(node.value)
            self.codestr += [self.ppFormatLine("JMP end_function_label_{0}".format(self.fnctr), node.lineno)]
        else:
            if isinstance(node.value, ast.Name):
                res, _ = self.localVarHandler(node.value)
                self.codestr += [self.ppFormatLine("LDWR {0}\nJMP end_function_label_{1}".format(res,self.fnctr), node.lineno)]
                self.safe_generic_visit(node)
            else:
                self.visit(node.value)
                self.codestr += [self.ppFormatLine("JMP end_function_label_{0}".format(self.fnctr), node.lineno)]
        if self.localNameSpace:
            self.returnSet.add(self.localNameSpace[-1])
        else:
            raise CompileException("Function return called outside of function definition!", node)

    def compileString(self, code):
        """Compile the ppp code"""
        splitcode = code.splitlines()
        initlines = len(splitcode)*1
        for l,line in enumerate(splitcode):
            splitcode[l] = self.preprocessCode(splitcode[l])
        finlines = len(splitcode)
        self.numberInitLines = initlines-finlines
        preprocessed_code = '\n'.join(splitcode)
        if self.passToOldPPPCompiler:
            oldcompiler = oldpppCompiler()
            result = oldcompiler.compileString(code)
            self.reverseLineLookup = oldcompiler.reverseLineLookup
            return result
        tree = ast.parse(preprocessed_code)
        self.visit(tree)
        self.optimize()
        self.preamble = '\n'.join(self.createHeader())+'\n'
        self.reverseLineLookup = self.generateReverseLineLookup(self.preamble+self.maincode)
        return self.preamble+self.maincode

    def preprocessCode(self, code):
        """Code preprocessor to collect all variable declarations"""
        preprocessed_code = re.sub(r"#COMPILER_FLAG *(\S+) *= *(\S+)", self.checkCompilerFlags, code)
        preprocessed_code = re.sub(r"(.*)(#.*)", lambda m: m.group(1), preprocessed_code)
        preprocessed_code = re.sub(r"^\s*const\s*(\S+)\s*=\s*(\S+)", self.collectConstants, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*exitcode\s*(\S+)\s*=\s*(\S+)", self.collectExitcodes, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*address\s*(\S+)\s*=\s*(\S+)", self.collectAddresses, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*address\s*(\S+)", self.collectAddresses, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*var\s*(\S+)\s*=\s*(\S+) *$", self.collectVars, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*var\s*(\S+)\s*=\s*([0-9x.]+) *([a-zA-Z]+)", self.collectVars, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*var\s*(\S+)", self.collectVars, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*parameter\s*<(\S+)>\s*(\S+)\s*=\s*([0-9\.x]+) *([a-zA-Z]+)", self.collectTypedParameters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*parameter\s*<(\S+)>\s*(\S+)\s*=\s*([0-9\.x]+)", self.collectTypedParameters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*parameter\s*<(\S+)>\s*(\S+)", self.collectTypedParameters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*parameter\s*(\S+)\s*=\s*([0-9\.x]+) *([a-zA-Z]+)", self.collectParameters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*parameter\s*(\S+)\s*=\s*([0-9\.x]+)", self.collectParameters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*parameter\s*(\S+)", self.collectParameters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*masked_shutter\s*(\S+)\s*=\s*(\S+)", self.collectMaskedShutters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*shutter\s*(\S+)\s*=\s*(\S+)", self.collectShutters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*trigger\s*(\S+)\s*=\s*(\S+)", self.collectTriggers, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*counter\s*(\S+)\s*=\s*(\S+)", self.collectCounters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*masked_shutter\s*(\S+)", self.collectMaskedShutters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*shutter\s*(\S+)", self.collectShutters, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*trigger\s*(\S+)", self.collectTriggers, preprocessed_code)
        preprocessed_code = re.sub(r"^\s*counter\s*(\S+)", self.collectCounters, preprocessed_code)
        return preprocessed_code

    def optimize(self):
        """Optimizes final pp code by condensing unnecessary calls"""
        self.recursionMapper()              # Look for any mutually recursive calls
        self.assembleMainCode()             # Finalize assembly by filling in placeholder declarations
        if self.enableOptimizations:
            self.optimizeRedundantSTWR_LDWRs()  # Get rid of STWR x\nLDWR x (the load is unnecessary)
            self.optimizeDoubleSTWRs()          # Get rid of STWR x\nSTWR x that shows up from function returns
            self.optimizeDoubleLDWRs()          # Get rid of LDWR x\nLDWR x that shows up from function returns
            self.optimizeRedundantSTWR_LDWRs_STWRs()
            self.optimizeChameleonLabels()      # Collapse consecutive labels into a single label
            self.optimizeOneLineJMPs()
            self.optimizeLabelNumbers()         # Re-number all labels in a sensible way
            self.optimizeLabelNOPs()            # Remove unnecessary NOPs after labels -> put label in front of next line
        if self.gt02bool:
            self.optimizeBoolForGt0()
        self.cleanupPPLineNumbers()
        if self.EnableNumericLabels:
            self.replaceWithNumericLabels()

    def assembleMainCode(self):
        """Goes through main code and looks for functions that include calls to other functions
           that hadn't been defined yet and fills in the missing assembly code"""
        functionDeclarations = list()
        for fn in self.funcNames:
            procedure = self.symbols.getProcedure(fn)
            if not procedure.inline:
                functionDeclarations += procedure.codegenInit(self.symbols)
        if self.requiredReturnCalls-self.returnSet:
            raise CompileException("Expected returned values form the following functions: {}",self.requiredReturnCalls-self.returnSet)
        justInCaseCounter = 0
        containsList = True
        while containsList:
            justInCaseCounter += 1
            containsList = False
            for ln, line in enumerate(functionDeclarations):
                if not isinstance(line, str):
                    containsList=True
                    try:
                        procedure = line[0](line[1])
                        functionDeclarations[ln] = procedure.codegen(self.symbols, arg=line[2], kwarg=line[3])
                        if len(functionDeclarations)-1 > ln:
                            functionDeclarations = functionDeclarations[:ln]+procedure.codegen(self.symbols, arg=line[2], kwarg=line[3])+functionDeclarations[ln+1:]
                        else:
                            functionDeclarations = functionDeclarations[:ln]+procedure.codegen(self.symbols, arg=line[2], kwarg=line[3])
                        break
                    except:
                        raise CompileException("Function {} is not declared!".format(line[1]))
            if justInCaseCounter > 1e6:
                raise CompileException("Compiler seems to have encountered an endless loop! Perhaps there's some recursion it didn't catch!")
        containsList = True
        while containsList:
            justInCaseCounter += 1
            containsList = False
            for ln, line in enumerate(self.maincode):
                if not isinstance(line, str):
                    containsList=True
                    try:
                        procedure = line[0](line[1])
                        self.maincode[ln] = procedure.codegen(self.symbols, arg=line[2], kwarg=line[3])
                        if len(self.maincode)-1 > ln:
                            self.maincode = self.maincode[:ln]+procedure.codegen(self.symbols, arg=line[2], kwarg=line[3])+self.maincode[ln+1:]
                        else:
                            self.maincode = self.maincode[:ln]+procedure.codegen(self.symbols, arg=line[2], kwarg=line[3])
                        break
                    except:
                        raise CompileException("Function {} is not declared!".format(line[1]))
            if justInCaseCounter > 1e6:
                raise CompileException("Compiler seems to have encountered an endless loop! Perhaps there's some recursion it didn't catch!")
        self.maincode = '\n'.join(self.maincode+["END"]+functionDeclarations)+'\n'
        self.maincode += "END\n"

    def recursionMapper(self):
        """Wrapper for traceCalls to look for mutual recursion"""
        self.traceCalls(set(self.funcDeps.keys()))

    def traceCalls(self, c, calls=None):
        """Looks for all function dependencies for each function and seeks out cyclic 
           graphs in a way that doesn't lead to recursion depth failures."""
        if not calls:
            for call in c:
                self.traceCalls(call,set([call]))
        else:
            subcalls = self.funcDeps[c]
            if subcalls:
                if subcalls & calls:
                    raise CompileException("Recursion is not supported!\n  --> Mutual calls between {}".format(", ".join(subcalls|calls|set([c]))))
                for call in subcalls:
                    if call:
                        self.traceCalls(call, calls|set([c]))

    def optimizeLabelNumbers(self):
        """Renumber all labels in the order that they appear for better readability of generated pp files"""
        replacements = set()
        rep = re.findall(r"(\S+_label_)(\d+):", self.maincode)
        for s in rep:
            joined_s = ''.join(s)
            if joined_s not in replacements:
                replacements.add(joined_s)
                self.maincode = self.maincode.replace(joined_s,'{0}{1}'.format(s[0],self.labelCounter[s[0]]))
            self.labelCounter[s[0]] += 1
        return

    def optimizeChameleonLabels(self):
        """reduce redundant labels of mixed type"""
        m = re.search(r"^(\S+_label_\d+):\sNOP *.*\n(\S+_label_\d+):\sNOP *.*", self.maincode, flags=re.MULTILINE)
        while m:
            self.maincode = re.sub(r"^(\S+_label_\d+):\sNOP *({0})*\n(\S+_label_\d+):\sNOP *({0})*".format(self.ppRegexStr), self.reduceChameleonEndLabels, self.maincode, flags=re.MULTILINE)
            m = re.search(r"^(\S+_label_\d+):\sNOP *.*\n(\S+_label_\d+):\sNOP *.*", self.maincode, flags=re.MULTILINE)
        while self.chameleonLabelsDeque:
            replList = self.chameleonLabelsDeque.popleft()
            self.maincode = re.sub(replList[1], partial(self.reduceChameleonLabels,replList[0]), self.maincode, flags=re.MULTILINE)
        return

    def optimizeOneLineJMPs(self):
        """Remove JMP statements for return statements that occur at the end of a function"""
        self.maincode = re.sub(r"JMP\s(?P<labelName>\S+_label_\d+)\s*({0})*\s*((?P=labelName):)".format(self.ppRegexStr), self.reduceOneLineJMPs, self.maincode)
        return

    def optimizeRedundantSTWR_LDWRs(self):
        """Prevents consecutive STWR and LDWR commands that reference the same variable:

            ...                 ...
            STWR var_1   ===>   STWR var_1
            LDWR var_1          ...  #LDWR unnessecary since var_1 is already in W register
            ...

            """
        self.maincode = re.sub("STWR\s(\S+) *({0})*\nLDWR\s(\S+) *({0})*\n".format(self.ppRegexStr), self.reduceRedundantStLd, self.maincode)
        return

    def optimizeRedundantSTWR_LDWRs_STWRs(self):
        """Prevents consecutive STWR and LDWR commands that reference the same variable:

            ...                 ...
            STWR var_1   ===>   STWR var_1
            LDWR var_1          ...  #LDWR unnessecary since var_1 is already in W register
            ...

            """
        self.maincode = re.sub("( *LDWR\s(?P<varname>\S+) *({0})*\n *STWR\s\S+ *({0})*)\n *LDWR\s(?P=varname) *({0})*\n".format(self.ppRegexStr), self.reduceRedundantStLdSt, self.maincode)
        return

    def optimizeDoubleSTWRs(self):
        """Gets rid of any redundant STWR calls:
        
               STWR a      ===>    STWR a
               STWR a
           
           This problem can come about when saving something in a variable and subsequently
           returning that variable from a function;
           
               def f(x):
                   a = x**2
                   return a
               
           """
        self.maincode = re.sub(r"STWR (?P<varname>\S+)\s*({0})*\nSTWR (?P=varname)\s*({0})*\n".format(self.ppRegexStr), self.reduceDoubleSTWRs, self.maincode)
        return

    def optimizeDoubleLDWRs(self):
        """Gets rid of any redundant LDWR calls:
        
               LDWR a      ===>    LDWR a
               LDWR a
           
           """
        self.maincode = re.sub(r"LDWR (?P<varname>\S+)\s*({0})*\nLDWR (?P=varname)\s*({0})*\n".format(self.ppRegexStr), self.reduceDoubleLDWRs, self.maincode)
        return

    def optimizeLabelNOPs(self):
        """Takes an end label with a NOP and puts it in front of the next line:
                
                end_label_1: NOP  ===> end_label_1: STWR a
                STWR a
            
            """
        #while re.search(r"(\S*label\S*: ) *NOP *({0})*\n([^\n]+)".format(self.ppRegexStr), self.maincode):
            #self.maincode = re.sub(r"(\S*label\S*: ) *NOP *({0})*\n([^\n]+)".format(self.ppRegexStr), self.reduceRedundantNOPs, self.maincode)
        while re.search(r"(\S*label\S*: ) *NOP.*\n([^\n]+)".format(self.ppRegexStr), self.maincode):
            self.maincode = re.sub(r"(\S*label\S*: ) *NOP.*\n([^\n]+)".format(self.ppRegexStr), self.reduceRedundantNOPs, self.maincode)
        return

    def optimizeBoolForGt0(self):
        self.maincode = re.sub(r"CMPGREATER NULL *({0})*\nJMPNCMP (\S+) *({0})*".format(self.ppRegexStr), self.reduceGt02Bool, self.maincode)


    def cleanupPPLineNumbers(self):
        newcode = []
        for line in self.maincode.splitlines():
            if '#' in line:
                parts = line.split('# PPP LINE:')
                newcode += ["{1:{0}} # PPP LINE:{2}".format(self.pplinnoColW, parts[0].rstrip(), parts[1])]
            else:
                newcode += [line]
        self.maincode = '\n'.join(newcode)

    def replaceWithNumericLabels(self):
        self.labelLUT = dict()
        preambleLen = len(self.createHeader())+1
        newcode = []
        for lineno, line in enumerate(self.maincode.splitlines()):
            if '# PPP LINE' in line:
                lsplit = line.split('# PPP LINE:')
                if ':' in lsplit[0]:
                    lsplit0 = lsplit[0].split(':')
                    newl = "{0:6}{1} #{2}".format("{0}: ".format(lineno+preambleLen), lsplit0[1].strip(), lsplit0[0])
                    self.labelLUT[lsplit0[0]] = lineno+preambleLen
                    lsplit[0] = "{1:{0}}".format(self.pplinnoColW, newl)
                    newcode += ["{1:{0}} # PPP LINE:{2}".format(self.pplinnoColW, newl, lsplit[1])]
                else:
                    newcode += ["      {1:{0}} # PPP LINE:{2}".format(self.pplinnoColW-6, lsplit[0].strip(), lsplit[1])]
            else:
                lsplit = [line]
                if ':' in lsplit[0]:
                    lsplit0 = lsplit[0].split(':')
                    newl = "{0:6}{1} #{2}".format("{0}: ".format(lineno+preambleLen), lsplit0[1].strip(), lsplit0[0])
                    newcode += ["{1:{0}}".format(self.pplinnoColW, newl)]
                else:
                    newcode += ["      {1:{0}}".format(self.pplinnoColW-6, line.strip())]
        self.maincode = '\n'.join(newcode)
        self.fixJumps()

    def cleanupPPLineNumbers2(self):
        newcode = []
        for line in self.maincode.splitlines():
            if '# PPP LINE' in line:
                parts = line.split('# PPP LINE:')
                subparts = parts[0].split('#')
                if len(subparts)>1:
                    newcode += ["{2:{0}} #{3:{1}} # PPP LINE:{4}".format(self.pplinnoColW-42, 40, subparts[0].rstrip(), subparts[1].strip(), parts[1])]
                else:
                    newcode += ["{1:{0}} # PPP LINE:{2}".format(self.pplinnoColW, parts[0].rstrip(), parts[1])]
            else:
                newcode += [line]
        self.maincode = '\n'.join(newcode)

    def fixJumps(self):
        newcode = []
        for line in self.maincode.splitlines():
            if 'label' in line:
                newcode += [re.sub(r"(\s*\S+\s+)(\S+label_\d+)(.*)", self.numericLabelLookup, line)]
            else:
                newcode += [line]
        self.maincode = '\n'.join(newcode)
        self.cleanupPPLineNumbers2()

    def numericLabelLookup(self, m):
        if m.group(2) in self.labelLUT.keys():
            if len(m.group(3).split('# PPP LINE:'))>1:
                pplinespl = m.group(3).split('# PPP LINE:')
                newstr = "{0}{1} {2}".format(m.group(1),self.labelLUT[m.group(2)], pplinespl[0].strip())
                return "{1:{0}} # PPP LINE:{2}".format(self.pplinnoColW, newstr, pplinespl[1])
            newstr = "{0}{1}".format(m.group(1),self.labelLUT[m.group(2)])
            return "{1:{0}} {2}".format(self.pplinnoColW, newstr, m.group(3).strip())
        return m.group(1)+m.group(2)+m.group(3)

    ###########################################
    #### Helper functions for re.sub calls ####
    ###########################################

    def reformatLineNumbers(self, m):
        print(m.group(1))
        print(m.group(2))
        return self.codeFmtStr.format(m.group(1).strip(), m.group(2).strip())

    def reduceOneLineJMPs(self, m):
        return m.group(3)

    def reduceDoubleSTWRs(self, m):
        return "STWR {1:{0}} {2}\n".format(self.pplinnoColW, m.group('varname'), m.group(2) or " ")

    def reduceDoubleLDWRs(self, m):
        return "LDWR {0} {1}\n".format(m.group('varname'), m.group(2) or " ")

    def reduceRedundantStLd(self, m):
        p1,p2 = m.group(1),m.group(3)
        if p1 == p2:
            return "STWR {0:60} {1}\n".format(m.group(1), m.group(2) or " ")
        return "STWR {0:60} {1}\nLDWR {2:60} {3}\n".format(m.group(1), m.group(2) or " ", m.group(3), m.group(4) or " ")

    def reduceRedundantStLdSt(self, m):
        return m.group(1)+'\n'

    def reduceRedundantNOPs(self, m):
        return "{0} {1}".format(m.group(1), m.group(2))

    def reduceChameleonEndLabels(self, m):
        self.chameleonLabelsDeque.append([m.group(1),m.group(3)])
        return "{0:60} {1}".format(m.group(1)+": NOP", m.group(2))

    def reduceChameleonLabels(self, repl, m):
        return repl

    def reduceGt02Bool(self, m):
        return "JMPZ {0:60} {1}".format(m.group(2), m.group(3))

    ########################################################################
    #### Grab all parameters/vars/triggers/... instantiated in the code ####
    ########################################################################

    def checkCompilerFlags(self, code):
        if code.group(1) == 'SAFE_PASS_BY_REFERENCE':
            if code.group(2) == 'True':
                FunctionSymbol.passByReferenceCheckCompleted = False
            elif code.group(2) == 'False':
                FunctionSymbol.passByReferenceCheckCompleted = True
            else:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be True or False".format(code.group(1), code.group(2)))
        if code.group(1) == 'USE_STANDARD_PPP_COMPILER':
            if code.group(2) == 'True':
                self.passToOldPPPCompiler = True
            elif code.group(2) == 'False':
                self.passToOldPPPCompiler = False
            else:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be True or False".format(code.group(1), code.group(2)))
        if code.group(1) == 'SUBSTITUTE_BOOL_FOR_GREATER_THAN_ZERO':
            if code.group(2) == 'True':
                self.gt02bool = True
            elif code.group(2) == 'False':
                self.gt02bool = False
            else:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be True or False".format(code.group(1), code.group(2)))
        if code.group(1) == 'ENABLE_OPTIMIZATIONS':
            if code.group(2) == 'True':
                self.enableOptimizations = True
            elif code.group(2) == 'False':
                self.enableOptimizations = False
            else:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be True or False".format(code.group(1), code.group(2)))
        if code.group(1) == 'INLINE_ALL_FUNCTIONS':
            if code.group(2) == 'True':
                self.inlineAll = True
            elif code.group(2) == 'False':
                self.inlineAll = False
            else:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be True or False".format(code.group(1), code.group(2)))
        if code.group(1) == 'USE_NUMERIC_LABELS':
            if code.group(2) == 'True':
                self.EnableNumericLabels = True
            elif code.group(2) == 'False':
                self.EnableNumericLabels = False
            else:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be True or False".format(code.group(1), code.group(2)))
        if code.group(1) == 'PPP_LINE_COLUMN_OFFSET':
            try:
                coloffset = int(code.group(2))
                if coloffset < 0:
                    raise CompileException("Unable to set compiler flag {0} to {1}, must be a positive integer".format(code.group(1), code.group(2)))
                self.pplinnoColW = int(code.group(2))
            except:
                raise CompileException("Unable to set compiler flag {0} to {1}, must be an integer".format(code.group(1), code.group(2)))
        return ""

    def collectConstants(self, code):
        """Parse const declarations and add them to symbols dictionary"""
        self.symbols[code.group(1)] = ConstSymbol(code.group(1), code.group(2))
        return ""

    def collectVars(self, code):
        """Parse var declarations with a value and add them to symbols dictionary"""
        if code.re.groups == 3:
            self.symbols[code.group(1)] = VarSymbol(name=code.group(1), value=code.group(2), unit=code.group(3))
        elif code.re.groups == 2:
            self.symbols[code.group(1)] = VarSymbol(name=code.group(1), value=code.group(2))
        else:
            self.symbols[code.group(1)] = VarSymbol(name=code.group(1), value=0)
        return ""

    def collectEmptyVars(self, code):
        """Parse var declarations with no value and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(name=code.group(1), value=0)
        return ""

    def collectParameters(self, code):
        """Parse parameter declarations with no encoding and add them to symbols dictionary"""
        if code.re.groups == 3:
            self.symbols[code.group(1)] = VarSymbol(type_="parameter",
                                                    name=code.group(1),
                                                    value=code.group(2),
                                                    unit=code.group(3))
        elif code.re.groups == 2:
            self.symbols[code.group(1)] = VarSymbol(type_="parameter", name=code.group(1), value=code.group(2))
        else:
            self.symbols[code.group(1)] = VarSymbol(type_="parameter", name=code.group(1), value=0)
        return ""

    def collectTypedParameters(self, code):
        """Parse parameter declarations with encoding and add them to symbols dictionary"""
        if code.re.groups == 4:
            self.symbols[code.group(2)] = VarSymbol(type_="parameter",
                                                    encoding=code.group(1),
                                                    name=code.group(2),
                                                    value=code.group(3),
                                                    unit=code.group(4))
        elif code.re.groups == 3:
            self.symbols[code.group(2)] = VarSymbol(type_="parameter",
                                                    encoding=code.group(1),
                                                    name=code.group(2),
                                                    value=code.group(3))
        elif code.re.groups == 2:
            self.symbols[code.group(2)] = VarSymbol(type_="parameter",
                                                    encoding=code.group(1),
                                                    name=code.group(2),
                                                    value=0)
        return ""

    def collectShutters(self, code):
        """Parse shutter declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="shutter", name=code.group(1), value=0 if code.re.groups == 1 else code.group(2))
        return ""

    def collectMaskedShutters(self, code):
        """Parse masked_shutter declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="masked_shutter", name=code.group(1), value=0 if code.re.groups == 1 else code.group(2))
        return ""

    def collectTriggers(self, code):
        """Parse trigger declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="trigger", name=code.group(1), value=0 if code.re.groups == 1 else code.group(2))
        return ""

    def collectCounters(self, code):
        """Parse counter declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="counter", name=code.group(1), value=0 if code.re.groups == 1 else code.group(2))
        return ""

    def collectExitcodes(self, code):
        """Parse exitcode declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="exitcode", name=code.group(1), value=code.group(2) if code.re.groups == 2 else 0)
        return ""

    def collectAddresses(self, code):
        """Parse address declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="address", name=code.group(1), value=code.group(2) if code.re.groups == 2 else 0)
        return ""

    def createHeader(self):
        """Creates pp header with all declarations from symbols dictionary"""
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

    def generateReverseLineLookup(self, codetext):
        lookup = dict()
        sourceline = 0
        for codeline, line in enumerate(codetext.splitlines()):
            m = re.search('# PPP LINE: *(\d+)', line)
            if m:
                sourceline = int(m.group(1))
                lookup[codeline+1] = sourceline
            else:
                lookup[codeline+1] = sourceline
        return lookup


def pppcompile(sourcefile, targetfile, referencefile, verbose=False, keepoutput=False, printFinalVars=False):
    import os.path
    try:
        with open(sourcefile, "r") as f:
            sourcecode = f.read()
        compiler = pppCompiler()
        #assembly = compiler.compileString(sourcecode)
        #assemblercode = virtualMachineOptimization(assembly)
        assemblercode = compiler.compileString(sourcecode )

        with open(targetfile, "w") as f:
            f.write(assemblercode)
    except CompileException as e:
        print(str(e))
        print(e.line())
    # compare result to reference
    if os.path.exists( referencefile ):
        with open(referencefile, "r") as f:
            referencecode = f.read()
        outfilenew = None
        outfileref = None
        if keepoutput:
            outfilenew = Path(targetfile+'.vm')
            outfileref = Path(referencefile+'.vm')
            outfilenew.write_text("#NewFile\n")
            outfileref.write_text("#RefFile\n")
        ppvm = ppVirtualMachine(assemblercode)
        ppvm.runCode(verbose, outfile=outfilenew)
        dast = ppvm.varDict
        ppvm2 = ppVirtualMachine(referencecode)
        ppvm2.runCode(verbose, outfile=outfileref)
        dcomp = ppvm2.varDict
        dictComparison = compareDicts(dast,dcomp)
        if printFinalVars:
            for k, v in sorted(dast.items(), key=lambda x: x[0]):
                print("{}: {}".format(k, v))
        if dictComparison:
            print(dictComparison)
            return False
        if keepoutput:
            for line in difflib.unified_diff(outfilenew.read_text().splitlines(), outfileref.read_text().splitlines()):
                print(line)
        return True
    return True

def pppCompileString(sourcecode):
    compiler = pppCompiler()
    assembly = compiler.compileString(sourcecode)
    optassy = virtualMachineOptimization(assembly)
    return optassy

def virtualMachineOptimization(assemblercode):
    ppvm = ppVirtualMachine(assemblercode)
    unnecessaryLines = ppvm.runCode(False)
    assemblercodeSplit = assemblercode.split('\n')
    print("orig length: ", len(assemblercodeSplit))
    for l, line in reversed(sorted(unnecessaryLines, key=lambda x: x[0])):
        print("line : ", l, "   code:  ", assemblercodeSplit[l-1])
        m = re.match(r"(.*: ).*", line)
        if m:
            assemblercodeSplit[l] = m.group(1)+assemblercodeSplit[l]
        del assemblercodeSplit[l-1]
    print("fin length: ", len(assemblercodeSplit))
    return '\n'.join(assemblercodeSplit)



if __name__=='__main__':
    mycode = """#code
parameter<AD9912_PHS> xx = 5.352  
const chan = 2
var retval = 0
var retval8 = 12
var retval3 = 0
var arg1 = 0
#masked_shutter shutter2
#shutter mainshutter


#var d = 5

def myFunc(c,j):
    d = 5
    k = 3
    b = c*2 if c < 4 else c*3
    #b=c
    while k<15:
        if 12 > b or b < 56 and b:
            b *= k
            b = b
        elif b == 36:
            b = 37
        elif b > 500:
            break
        else:
            b += k
            b = b
            b *= 2
            b = b
        k += 1
        #d = b# << 1
        if b > 930:
            pass
            #return b
    #set_dds(channel=chan, phase=xx)
    #rand_seed(d)
    #update()
    #b = secf(d)
    #b = roundabout(d)
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
#for someval in range(10):
    #arg5 = someval
retval = myFunc(arg1,6)
g=3*arg2
g *= arg2
arg1 = 4
arg2 = 4
myFunc(arg1,arg2)
retval = 10
arg2 = 6
retval8 = secf(arg2)
g*=2
arg2 = 4
retval3 = secf(arg2)
g*=2
arg2 = 4
retval2 = roundabout(arg2)
g1 = retval8
g2 = retval2
arg3 = 2
"""

    ppAn = pppCompiler()
    compcode = ppAn.compileString(mycode)
    print('-------------')
    print('Compiled Code')
    print('-------------')
    print(compcode)
    ppvm = ppVirtualMachine(compcode)
    print('\n------------------------')
    print('Virtual Machine Sequence')
    print('------------------------')
    ppvm.runCode(True)
    print('\nFinal State:')
    ppvm.printState()
    print('')
    dcomp = ppvm.varDict
    draw = evalRawCode(mycode)
    #print(draw)
    dictComp = compareDicts(dcomp,draw)
    if dictComp:
        print("\nFinal states are not equal!\n", dictComp)
    else:
        print("\nFinal states are equal, life is good :)")


