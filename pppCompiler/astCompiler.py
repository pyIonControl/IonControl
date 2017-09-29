# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ast
import copy
import re
from collections import deque, defaultdict
from .Symbol import SymbolTable, FunctionSymbol, ConstSymbol, VarSymbol
from itertools import starmap
from functools import partial

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
allowedASTPrimitives = {'Add', 'Sub','And', 'Assign', 'AugAssign', 'BinOp', 'BitAnd', 'BitOr', 'Call', 'Compare',
                        'Eq', 'Expr', 'Expression', 'For', 'FunctionDef', 'GeneratorExp', 'Global', 'Gt', 'GtE', 'If', 'IfExp', 'Load',
                        #'Index', 'Interactive', 'Invert', 'Is', 'IsNot', 'LShift', 'Lambda', 'List', 'ListComp',
                        'LShift', 'Lt', 'LtE', 'Mod', 'Module', 'Mult', 'Name', 'NameConstant', 'Nonlocal', 'Not', 'NotEq',
                        'NotIn', 'Num', 'Or', 'Pass', 'RShift', 'Return',
                        'Store', 'Str', 'Sub', 'Suite', 'UAdd', 'USub', 'UnaryOp', 'While' }

ComparisonLUT = {ast.Gt:    "CMPGREATER",
                 ast.GtE:   "CMPGE",
                 ast.Lt:    "CMPLESS",
                 ast.LtE:   "CMPLE",
                 ast.Eq:    "CMPEQUAL",
                 ast.NotEq: "CMPNOTEQUAL"}

BaseFunctions = {'set_dds': '',
                 'set_trigger': '',
                 'set_shutter': '',
                 'update': ''}

def list_rtrim( l, trimvalue=None ):
    """in place list right trim"""
    while len(l)>0 and l[-1]==trimvalue:
        l.pop()
    return l

class CompileException(Exception):
    pass

class pppCompiler(ast.NodeTransformer):
    def __init__(self):
        self.builtinBool = None
        self.codestr = []
        self.maincode = ""
        self.upd_funcs = set()
        self.varnames = set()
        self.funcnames = set()
        self.funcDeps = defaultdict(set)
        #self.fnLUT = dict()
        self.localNameSpace = deque()
        self.chameleonLabelsDeque = deque()
        self.ntvar = set()
        self.currfn = None
        self.lvpreamble = ""    #initial inline declarations
        self.lvctr = 1          #inline declaration counter
        self.ifctr = 1000          #number of if statements
        self.elsectr = 1000        #number of else statements
        self.whilectr = 1000      #number of while statements
        self.fnctr = 1000
        self.symbols = SymbolTable()
        self.localVarDict = dict()
        self.preamble = ""

    def safe_generic_visit(self, node):
        """Modified generic_visit call, currently just returning generic_visit directly"""
        self.generic_visit(node)

    def valLUT(self, obj):
        """Look for preexisting variables in local and global scopes, if return value is a number then
           return a flag that instantiates an inline variable or can be handled later"""
        if isinstance(obj, ast.Num):
            return obj.n, True
        elif isinstance(obj, ast.Name):
            if obj.id in self.symbols.keys():
                return self.symbols[obj.id].name, False
            if self.localNameSpace:
                for ns in self.localNameSpace:
                    localname = ns+"_"+obj.id
                    if localname in self.symbols.keys():
                        return self.symbols[localname].name, False
                #if obj.id in self.symbols.keys():
                    #return self.symbols[obj.id].name, False
                if self.localNameSpace[-1]+'_'+obj.id in self.symbols.keys():
                    return self.localNameSpace[-1]+'_'+obj.id, False
        elif isinstance(obj, ast.Call):
            return obj.func.id, False
        return obj.id, False

    def localVarHandler(self, nv):
        """Looks up pre-existing variables and declares undeclared variables"""
        right, localvar = self.valLUT(nv)
        if localvar:
            if right in self.localVarDict.keys(): #checks if inlinevar of the same value has already been created
                return self.localVarDict[right], localvar
            else:
                self.lvpreamble += "var inlinevar_{0} {1}\n".format(self.lvctr, right)
                self.symbols.setInlineParameter(name="inlinevar_{0}".format(self.lvctr), value=right)
                self.localVarDict[right] = "inlinevar_{0}".format(self.lvctr)
                right = "inlinevar_{0}".format(self.lvctr)
                self.lvctr += 1
        return right, localvar

    def visit_Assign(self, node):
        """Node visitor for variable assignment"""
        fret = False
        if len(node.targets) == 1 and hasattr(node.targets[0],'id'):
            target,_ = self.valLUT(node.targets[0])
            if target in self.symbols.keys():
                if hasattr(node.value,'func') or hasattr(node.value, 'op'):
                    fret = True
                else:
                    right,_ = self.localVarHandler(node.value)
                    self.codestr += ["LDWR {0}\nSTWR {1}".format(right,target)]
                    self.symbols[target] = VarSymbol(name=target, value=0)
            else:
                if hasattr(node.value,'func') or hasattr(node.value, 'op'):
                    fret = True
                    self.lvpreamble += "var {0} 0\n".format(target)
                    self.symbols[target] = VarSymbol(name=target, value=0)
                else:
                    right,localvar = self.localVarHandler(node.value)
                    self.codestr += ["LDWR {0}\nSTWR {1}".format(right,target)]
                    self.symbols[target] = VarSymbol(name=target, value=right)
                    self.lvpreamble += "var {0} {1}\n".format(target, right)
        self.safe_generic_visit(node)
        if fret:
            self.codestr += ["STWR {0}".format(target)]
        if not self.localNameSpace:
            self.maincode += '\n'.join(self.codestr)+'\n'
            self.codestr = []

    def visit_AugAssign(self, node):
        """Node visitor for augmented assignment, eg x += 1"""
        if 'n' in node.value._fields and node.value.n == 1:
            nodetid = "_".join(self.localNameSpace+deque(node.target.id))
            if nodetid not in self.symbols.keys():
                nodetid = node.target.id
            if isinstance(node.op, ast.Add):
                self.codestr += ["INC {0}".format(nodetid)]
            elif isinstance(node.op, ast.Sub):
                self.codestr += ["DEC {0}".format(nodetid)]
        else:
            nodetid,_ = self.localVarHandler(node.target)
            nodevid,_ = self.localVarHandler(node.value)
            self.codestr += ["LDWR {}".format(nodetid)]
            if isinstance(node.op, ast.Add):
                self.codestr += ["ADDW {0}\nSTWR {1}".format(nodevid, nodetid)]
            elif isinstance(node.op, ast.Sub):
                self.codestr += ["SUBW {0}\nSTWR {1}".format(nodevid, nodetid)]
            elif isinstance(node.op, ast.Mult):
                self.codestr += ["MULW {0}\nSTWR {1}".format(nodevid, nodetid)]
            elif isinstance(node.op, ast.RShift):
                self.codestr += ["SHR {0}\nSTWR {1}".format(nodevid, nodetid)]
            elif isinstance(node.op, ast.LShift):
                self.codestr += ["SHL {0}\nSTWR {1}".format(nodevid, nodetid)]
            elif isinstance(node.op, ast.BitAnd):
                self.codestr += ["ANDW {0}\nSTWR {1}".format(nodevid, nodetid)]
            elif isinstance(node.op, ast.BitOr):
                self.codestr += ["ORW {0}\nSTWR {1}".format(nodevid, nodetid)]
        self.safe_generic_visit(node)
        if not self.localNameSpace:
            self.maincode += '\n'.join(self.codestr)+'\n'
            self.codestr = []

    def visit_BinOp(self, node):
        """Node visitor for binary (inline) operations like +,-,*,&,|,<<,>>"""
        nodetid,_ = self.localVarHandler(node.left)
        nodevid,_ = self.localVarHandler(node.right)
        self.codestr += ["LDWR {}".format(nodetid)]
        if isinstance(node.op, ast.Add):
            self.codestr += ["ADDW {0}".format(nodevid)]
        elif isinstance(node.op, ast.Sub):
            self.codestr += ["SUBW {0}".format(nodevid)]
        elif isinstance(node.op, ast.Mult):
            self.codestr += ["MULW {0}".format(nodevid)]
        elif isinstance(node.op, ast.RShift):
            self.codestr += ["SHR {0}".format(nodevid)]
        elif isinstance(node.op, ast.LShift):
            self.codestr += ["SHL {0}".format(nodevid)]
        elif isinstance(node.op, ast.BitAnd):
            self.codestr += ["ANDW {0}".format(nodevid)]
        elif isinstance(node.op, ast.BitOr):
            self.codestr += ["ORW {0}".format(nodevid)]
        self.safe_generic_visit(node)

    def visit_If(self, node):
        """Node visitor for if statements, handles else and elif statements via subnodes"""
        currentIfCtr = copy.copy(self.ifctr)
        if hasattr(node.test, 'left'):
            left,_ = self.localVarHandler(node.test.left)
            right,_ = self.localVarHandler(node.test.comparators[0])
            op = ComparisonLUT[node.test.ops[0].__class__]
        elif isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
            left,_ = self.localVarHandler(node.test.operand)
            right, op = None, 'N'
        else:
            left,_ = self.localVarHandler(node.test)
            right, op = None, ''
        if node.orelse:
            if right is None:
                self.codestr += ["LDWR {0}\nJMP{1}Z else_label_{2}".format(left,op,self.elsectr)]
            else:
                self.codestr += ["LDWR {0}\n{1} {2}\nJMPNCMP else_label_{3}".format(left,op,right,self.elsectr)]
            self.ifctr += 1
            for subnode in node.body:
                self.visit(subnode)
            self.codestr += ["JMP end_if_label_{0}\nelse_label_{1}: NOP".format(currentIfCtr,self.elsectr)]
            self.elsectr += 1
            for subnode in node.orelse:
                self.visit(subnode)
            self.codestr += ["end_if_label_{0}: NOP".format(currentIfCtr)]
        else:
            if right is None:
                self.codestr += ["LDWR {0}\nJMP{1}Z end_if_label_{2}".format(left,op,currentIfCtr)]
            else:
                self.codestr += ["LDWR {0}\n{1} {2}\nJMPNCMP end_if_label_{3}".format(left,op,right,currentIfCtr)]
            self.ifctr += 1
            self.safe_generic_visit(node)
            self.codestr += ["end_if_label_{0}: NOP".format(currentIfCtr)]
        if not self.localNameSpace:
            self.maincode += '\n'.join(self.codestr)+'\n'
            self.codestr = []

    def visit_While(self, node):
        """Node visitor for while statements"""
        currentWhileCtr = copy.copy(self.whilectr)
        self.codestr += ["while_label_{}: NOP".format(currentWhileCtr)]
        if hasattr(node.test, 'left'):
            left,_ = self.localVarHandler(node.test.left)
            right,_ = self.localVarHandler(node.test.comparators[0])
            op = ComparisonLUT[node.test.ops[0].__class__]
            self.codestr += ["LDWR {0}\n{1} {2}\nJMPNCMP end_while_label_{3}".format(left,op,right,currentWhileCtr)]
        elif isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
            left,_ = self.localVarHandler(node.test.operand)
            right, op = None, 'N'
            if hasattr(node.test.operand, 'func'):
                self.builtinBool = True
                self.codestr += [" end_while_label_{0}".format(currentWhileCtr)]
            else:
                self.codestr += ["LDWR {0}\nJMP{1}Z end_while_label_{0}".format(left,op,currentWhileCtr)]
        else:
            left,_ = self.localVarHandler(node.test)
            right, op = None, ''
            if hasattr(node.test.operand, 'func'):
                self.builtinBool = False
                self.codestr += [" end_while_label_{0}".format(currentWhileCtr)]
            else:
                self.codestr += ["LDWR {0}\nJMP{1}Z end_while_label_{0}".format(left,op,currentWhileCtr)]
        #if right is None:
            #self.codestr += ["LDWR {0}\nJMP{1}Z".format(left,op), " end_while_label_{0}".format(currentWhileCtr)]
        #else:
            #self.codestr += ["LDWR {0}\n{1} {2}\nJMPNCMP end_while_label_{3}".format(left,op,right,currentWhileCtr)]
        self.whilectr += 1
        self.safe_generic_visit(node)
        self.codestr += ["JMP while_label_{0}\nend_while_label_{0}: NOP".format(currentWhileCtr)]
        if not self.localNameSpace:
            self.maincode += '\n'.join(self.codestr)+'\n'
            self.codestr = []

    def visit_FunctionDef(self, node):
        if node.name in self.symbols.keys():
            raise CompileException("Function {} has already been declared!".format(node.name))
        for arg in node.args.args:
            self.lvpreamble += "var {0}_{1} 0\n".format(node.name, arg.arg)
            target = node.name+"_"+arg.arg
            self.symbols[target] = VarSymbol(name=target, value=0)
        self.localNameSpace.append(node.name) # push function context for maintaining local variable definitions
        if len(set(self.localNameSpace)) != len(self.localNameSpace):
            print('RECURSION ERROR')
            raise CompileException('Recursion not supported!')
        self.safe_generic_visit(node)         # walk inner block
        self.localNameSpace.pop()             # pop function context
        self.codestr += ["end_function_label_{}: NOP".format(self.fnctr)]
        self.fnctr += 1
        self.symbols[node.name] = FunctionSymbol(node.name, copy.copy(self.codestr),
                                                 nameSpace=node.name, argn=[node.name+'_'+arg.arg for arg in node.args.args],
                                                 symbols=self.symbols, maincode=self)
        self.codestr = []

    def getChameleonSymbol(self, obj):
        if self.localNameSpace:
            target = "_".join(self.localNameSpace+deque(obj.id))
            if target in self.symbols.keys():
                return self.symbols[target]
        if obj.id in self.symbols.keys():
            return self.symbols[obj.id]

    def visit_Call(self, node):
        if hasattr(node.func, 'id'):
            if self.localNameSpace:
                self.funcDeps[self.localNameSpace[-1]].add(node.func.id)
            #self.localNameSpace.append(node.func.id)
            if len(set(self.localNameSpace)) != len(self.localNameSpace):
                raise CompileException('Recursion not supported!')
            if node.func.id in self.symbols.keys():
                procedure = self.symbols.getProcedure(node.func.id)
                if node.keywords:
                    kwdict = {kw.arg: self.valLUT(kw.value)[0] for kw in node.keywords}
                else:
                    kwdict = dict()
                arglist = [node.func.id]
                if node.args:
                    arglist += [self.valLUT(arg)[0] for arg in node.args]
                else:
                    arglist += []
                if node.func.id in ['pipe_empty','read_ram_valid']:
                    retdict = procedure.codegen(self.symbols, arg=arglist, kwarg=kwdict)
                    if isinstance(retdict, dict):
                        #retdict = retdict[self.builtinBool]
                        self.codestr[-1] = retdict[self.builtinBool]+self.codestr[-1]#procedure.codegen(self.symbols, arg=arglist, kwarg=kwdict)[self.builtinBool]
                    #self.codestr[-2] += self.codestr[-1]
                    #del self.codestr[-1]
                else:
                    self.codestr += procedure.codegen(self.symbols, arg=arglist, kwarg=kwdict)
                if True in self.codestr:
                    raise Exception('Bool in codestr')
        self.safe_generic_visit(node)
        #self.localNameSpace.pop()
        if not self.localNameSpace:
            self.maincode += '\n'.join(self.codestr)+'\n'
            self.codestr = []

    def visit_Return(self, node):
        """Node visitor for return statements"""
        res, _ = self.localVarHandler(node.value)
        self.codestr += ["LDWR {0}\nJMP end_function_label_{1}".format(res,self.fnctr)]
        self.safe_generic_visit(node)

    def compileString(self, code):
        """Compile the ppp code"""
        preprocessed_code = self.preprocessCode(code)
        tree = ast.parse(preprocessed_code)
        self.visit(tree)
        self.optimize()
        #self.optimize()
        self.preamble = '\n'.join(self.createHeader())+'\n'
        return self.preamble+self.maincode

    def preprocessCode(self, code):
        """Code preprocessor to collect all variable declarations"""
        preprocessed_code = re.sub(r"const\s*(\S+)\s*=\s*(\S+)", self.collectConstants, code)
        preprocessed_code = re.sub(r"exitcode\s*(\S+)\s*=\s*(\S+)", self.collectExitcodes, preprocessed_code)
        preprocessed_code = re.sub(r"address\s*(\S+)\s*=\s*(\S+)", self.collectAddresses, preprocessed_code)
        preprocessed_code = re.sub(r"var\s*(\S+)\s*=\s*(\S+)", self.collectVars, preprocessed_code)
        preprocessed_code = re.sub(r"var\s*(\S+)", self.collectVars, preprocessed_code)
        preprocessed_code = re.sub(r"parameter\s*<(\S+)>\s*(\S+)\s*=\s*([0-9.]+) *([a-zA-Z]+)", self.collectTypedParameters, preprocessed_code)
        preprocessed_code = re.sub(r"parameter\s*<(\S+)>\s*(\S+)\s*=\s*([0-9.]+)", self.collectTypedParameters, preprocessed_code)
        preprocessed_code = re.sub(r"parameter\s*(\S+)\s*=\s*([0-9.]+) *([a-zA-Z]+)", self.collectParameters, preprocessed_code)
        preprocessed_code = re.sub(r"parameter\s*(\S+)\s*=\s*([0-9.]+)", self.collectParameters, preprocessed_code)
        preprocessed_code = re.sub(r"parameter\s*(\S+)", self.collectParameters, preprocessed_code)
        preprocessed_code = re.sub(r"masked_shutter\s*(\S+)\s*=\s*(\S+)", self.collectMaskedShutters, preprocessed_code)
        preprocessed_code = re.sub(r"^shutter\s*(\S+)\s*=\s*(\S+)", self.collectShutters, preprocessed_code, flags=re.MULTILINE)
        preprocessed_code = re.sub(r"^trigger\s*(\S+)\s*=\s*(\S+)", self.collectTriggers, preprocessed_code, flags=re.MULTILINE)
        preprocessed_code = re.sub(r"^counter\s*(\S+)\s*=\s*(\S+)", self.collectCounters, preprocessed_code, flags=re.MULTILINE)
        preprocessed_code = re.sub(r"masked_shutter\s*(\S+)", self.collectMaskedShutters, preprocessed_code)
        preprocessed_code = re.sub(r"^shutter\s*(\S+)", self.collectShutters, preprocessed_code, flags=re.MULTILINE)
        preprocessed_code = re.sub(r"^trigger\s*(\S+)", self.collectTriggers, preprocessed_code, flags=re.MULTILINE)
        preprocessed_code = re.sub(r"^counter\s*(\S+)", self.collectCounters, preprocessed_code, flags=re.MULTILINE)
        return preprocessed_code

    def optimize(self):
        """Optimizes final pp code by condensing unnecessary calls"""
        self.recursionMapper()
        self.matches = set()
        self.maincode = re.sub("STWR\s(\S+)\nLDWR\s(\S+)\n", self.reduceRedundantStLd, self.maincode)
        self.optimizeChameleonLabels()
        self.optimizeIfLabels()
        self.optimizeElseLabels()
        self.optimizeWhileLabels()
        self.optimizeFunctionLabels()
        self.optimizeLabelNOPs()

    def recursionMapper(self):
        self.traceCalls(set(self.funcDeps.keys()))

    def traceCalls(self, c, calls=None):
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


    def traceCalls2(self, calls=set(), parentCalls=set()):
        if calls:
            if parentCalls:
                if parentCalls & calls:
                    raise CompileException("Recursion is not supported!\n  --> Mutual calls between {}".format(", ".join(parentCalls|calls)))
            return set(starmap(self.traceCalls2, [(self.funcDeps[c],calls|parentCalls) for c in calls]))
        return None

    def optimizeIfLabels(self):
        """Reduces number of excess end_if_labels for nested if (or multiple elif) statements"""
        m = re.search(r"(end_if_label_\d+):\sNOP\s*\n(end_if_label_\d+):\sNOP\n", self.maincode)
        while m:
            # look for consecutive end_if_labels and condense
            self.maincode = re.sub("(end_if_label_\d+):\sNOP\s*\n(end_if_label_\d+):\sNOP\n", self.reduceNestedIfs, self.maincode)
            # rename reduced end_if_labels for all JMP commands
            for v in self.matches:
                self.maincode = self.maincode.replace(v[0],v[1])
            self.matches = set()
            m = re.search(r"(end_if_label_\d+):\sNOP\s*\n(end_if_label_\d+):\sNOP\n", self.maincode)
        # if end_if_labels present, rename them starting from 0
        m = re.search(r"end_if_label_\d+", self.maincode)
        if m:
            for n,s in enumerate(set(re.findall(r"\S*\s*(end_if_label_\d+)", self.maincode))):
                self.maincode = self.maincode.replace(s,'end_if_label_{}'.format(n))
        return

    def optimizeElseLabels(self):
        """Reduces number of excess end_if_labels for nested if (or multiple elif) statements"""
        #m = re.search(r"(else_label_\d+):\sNOP\s*\n(else_label_\d+):\sNOP\n", self.maincode)
        #while m:
            ## look for consecutive end_if_labels and condense
            #self.maincode = re.sub("(else_label_\d+):\sNOP\s*\n(else_label_\d+):\sNOP\n", self.reduceNestedIfs, self.maincode)
            ## rename reduced end_if_labels for all JMP commands
            #for v in self.matches:
                #self.maincode = self.maincode.replace(v[0],v[1])
            #self.matches = set()
            #m = re.search(r"(else_label_\d+):\sNOP\s*\n(else_label_\d+):\sNOP\n", self.maincode)
        # if end_if_labels present, rename them starting from 0
        m = re.search(r"else_label_\d+", self.maincode)
        if m:
            for n,s in enumerate(set(re.findall(r"\S*\s*(else_label_\d+)", self.maincode))):
                self.maincode = self.maincode.replace(s,'else_label_{}'.format(n))
        return

    def optimizeWhileLabels(self):
        """Sequentially order while labels"""
        for n,s in enumerate(set(re.findall(r"\S*\s*\S*(while_label_\d+)", self.maincode))):
            self.maincode = self.maincode.replace(s,'while_label_{}'.format(n))
        return

    def optimizeFunctionLabels(self):
        """Remove JMP statements for return statements that occur at the end of a function"""
        m = re.search(r"JMP\s(end_function_label_\d+)\s*\S*\n(end_function_label_\d+):\sNOP\n", self.maincode)
        while m:
            # look for consecutive end_if_labels and condense
            self.maincode = re.sub(r"JMP\s(end_function_label_\d+)\s*\S*\n(end_function_label_\d+):\sNOP\n", self.reduceNestedIfs, self.maincode)
            # rename reduced end_if_labels for all JMP commands
            for v in self.matches:
                self.maincode = self.maincode.replace(v[0],v[1])
            self.matches = set()
            m = re.search(r"JMP\s(end_function_label_\d+)\s*\S*\n(end_function_label_\d+):\sNOP\n", self.maincode)
        # if end_function_labels present, rename them starting from 0
        m = re.search(r"end_function_label_\d+", self.maincode)
        if m:
            for n,s in enumerate(set(re.findall(r"\S*\s*\S*(end_function_label_\d+)", self.maincode))):
                self.maincode = self.maincode.replace(s,'end_function_label_{}'.format(n))
        return

    def optimizeChameleonLabels(self):
        """reduce redundant labels of mixed type"""
        m = re.search(r"^(\S+_label_\d+):\sNOP\n(\S+_label_\d+):\sNOP", self.maincode, flags=re.MULTILINE)
        while m:
            self.maincode = re.sub(r"^(\S+_label_\d+):\sNOP\n(\S+_label_\d+):\sNOP", self.reduceChameleonEndLabels, self.maincode, flags=re.MULTILINE)
            m = re.search(r"^(\S+_label_\d+):\sNOP\n(\S+_label_\d+):\sNOP", self.maincode, flags=re.MULTILINE)
        while self.chameleonLabelsDeque:
            replList = self.chameleonLabelsDeque.pop()
            self.maincode = re.sub(replList[1], partial(self.reduceChameleonLabels,replList[0],), self.maincode, flags=re.MULTILINE)
        return

    def optimizeLabelNOPs(self):
        while re.search(r"(\S*label\S*:\s)(NOP\n)", self.maincode):
            self.maincode = re.sub(r"(\S*label\S*:\s)(NOP\n)", self.reduceRedundantNOPs, self.maincode)
        return

    def reduceRedundantStLd(self, m):
        """Prevents consecutive STWR and LDWR commands that reference the same variable:

            ...                 ...
            STWR var_1   ===>   STWR var_1
            LDWR var_1          ...  #LDWR unnessecary since var_1 is already in W register
            ...

            """
        p1,p2 = m.group(1),m.group(2)
        if p1 == p2:
            return "STWR {}\n".format(m.group(1))
        return "STWR "+m.group(1)+"\nLDWR "+ m.group(2)+"\n"

    def reduceRedundantNOPs(self, m):
        return m.group(1)

    def reduceNestedIfs(self, m):
        """Used in re.sub to replace consecutive end_if_labels with the second label:

            ...                           ...
            end_if_label_3: NOP    ===>   end_if_label_2: NOP
            end_if_label_2: NOP           ...
            ...

        """
        self.matches.add((m.group(1),m.group(2)))
        return m.group(2)+": NOP\n"

    def reduceUnnessecaryFnJMPs(self, m):
        self.matches.add((m.group(1),m.group(2)))
        return m.group(2)+": NOP\n"

    def reduceChameleonEndLabels(self, m):
        self.chameleonLabelsDeque.append([m.group(1),m.group(2)])
        return m.group(1)+": NOP"

    def reduceChameleonLabels(self, repl, m):
        return repl

    def collectConstants(self, code):
        """Parse const declarations and add them to symbols dictionary"""
        self.symbols[code.group(1)] = ConstSymbol(code.group(1), code.group(2))
        return ""


    def collectVars(self, code):
        """Parse var declarations with a value and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(name=code.group(1), value=code.group(2) if code.re.groups == 2 else 0)
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
        else:
            self.symbols[code.group(2)] = VarSymbol(type_="parameter",
                                                    encoding=code.group(1),
                                                    name=code.group(2),
                                                    value=code.group(3))
        return ""

    def collectShutters(self, code):
        """Parse shutter declarations with encoding and add them to symbols dictionary"""
        self.symbols[code.group(1)] = VarSymbol(type_="shutter", name=code.group(1), value=1 if code.re.groups == 1 else code.group(2))
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
        self.symbols[code.group(1)] = VarSymbol(type_="exitcode", name=code.group(1), value=code.group(2) if code.re.groups == 2 else 0)
        return ""

    def collectAddresses(self, code):
        self.symbols[code.group(1)] = VarSymbol(type_="address", name=code.group(1), value=code.group(2) if code.re.groups == 2 else 0)
        return ""

        #type_ = Keyword("parameter") | Keyword("shutter") | Keyword("masked_shutter") | Keyword("trigger") | Keyword("var") | Keyword("counter") | Keyword("exitcode") | Keyword("address")
        #var MicrowaveFreq 40, parameter, MHz, AD9912_FRQ

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

def illegalLambda(error_message):
    """Generic function for unsupported visitor methods"""
    def gencall(self, node):
        raise CompileException("{} not supported!".format(error_message))
        self.generic_visit(node)
    return gencall

def instantiateIllegalCalls():
    """Add all unsupported visitor methods to pppCompiler class"""
    for name in fullASTPrimitives-allowedASTPrimitives:
        visit_name = "visit_{0}".format(name)
        visit_fn = illegalLambda(name)
        setattr(pppCompiler, visit_name, visit_fn)


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

        self.mainCode = re.sub(r"^(end_if_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(while_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(end_while_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(else_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.mainCode = re.sub(r"^(end_function_label_\d+:\s)(.*)", self.replaceLabel, self.mainCode, flags=re.MULTILINE)
        self.code = self.mainCode.split('\n')
        #print(self.labelDict)

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
                #elif "x" in m.group(3):
                    #self.varDict[m.group(2)] = hex(m.group(3))
                else:
                    self.varDict[m.group(2)] = int(m.group(3),0)
                continue
            else:
                m = re.match(r"(var)\s(\S+)\s+(\S+)",line)
                if m:
                    self.varDict[m.group(2)] = m.group(3)
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
                    self.varDict[m.group(2)] = m.group(3)
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
                #self.varDict[m.group(2)] -= 1
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

def pppcompile( sourcefile, targetfile, referencefile ):
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
    if os.path.exists( referencefile ):
        with open(referencefile, "r") as f:
            referencecode = f.read()
        ppvm = ppVirtualMachine(assemblercode)
        ppvm.runCode()
        dast = ppvm.varDict
        ppvm2 = ppVirtualMachine(referencecode)
        ppvm2.runCode()
        dcomp = ppvm2.varDict
        dictComparison = compareDicts(dast,dcomp)
        if dictComparison:
            print(dictComparison)
            return False
        return True
    return True

def pppCompileString(sourcecode):
    compiler = pppCompiler()
    return compiler.compileString(sourcecode)


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

    print(preprocessed_code)
    d = dict()
    ex = exec(compile(preprocessed_code, '<string>', 'exec', optimize=2),d,d)
    return d
    #exec(compile(str(self.fullname)).read(), str(self.fullname), 'exec'), d, d) #run the script

def correctDeclarations(code):
    """Parse var declarations with no value and add them to symbols dictionary"""
    return "{0} = {1}\n".format(code.group(1), code.group(2))

def correctEmptyDeclarations(code):
    """Parse var declarations with no value and add them to symbols dictionary"""
    return "\n"

def printAllSettings(code):
    if code.group(2)[0] != '#':
        return "{0}{1} = {2}{0}print('{1} = ', {1})".format(code.group(1),code.group(2),code.group(3))
    return "{0}{1} = {2}".format(code.group(1),code.group(2),code.group(3))

def compareDicts(d1,d2):
    dout = dict()
    for k,v in d1.items():
        if "inlinevar" not in k:
            if k in d2.keys():
                if d2[k] != v:
                    dout[k] = {'d1': v, 'd2': d2[k]}
    return dout



if __name__=='__main__':
    #tree = ast.parse(mycode)

    mycode = """#code
parameter<AD9912_PHS> xx = 5.352  
const chan = 2
var retval = 0
var retval8 = 12
var retval3 = 0
var arg1 = 0
masked_shutter shutter2
shutter mainshutter


var d

def myFunc(c,j):
    d = 5
    k = 3
    b = c*2
    #b=c
    while k<15:
        if 12 < b:
            b *= k
        elif b:
            b -= 12
        elif b == 36:
            b = 37
        else:
            b += k
            b <<= 2
        k += 1
        d = b << 1
        if d > 30:
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
arg2 = 6
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

    ppAn = pppCompiler()
    instantiateIllegalCalls()
    ppAn.compileString(mycode)
    #ppAn.visit(tree)
    print(ppAn.preamble + ppAn.maincode)
    compcode = ppAn.preamble + ppAn.maincode
    ppvm = ppVirtualMachine(compcode)
    ppvm.runCode()
    ppvm.printState()
    dcomp = ppvm.varDict
    draw = evalRawCode(mycode)
    print(draw)
    print("Dicts equal? ", compareDicts(dcomp,draw))

    #print(draw)
    #for k,v in dcomp.items():
    #    if k in draw.keys():
    #        print("{0}: comp: {1}, raw: {2}".format(k,v,draw[k]))
    #def repl(m):
        #inner_word = list(m.group(2))
        #print("const("+m.group(1)+","+ m.group(2)+")\n")
        #return "const("+m.group(1)+","+ m.group(2)+")\n"
        #return ""
    #text = "const pi = 3.14\nconst e = 2.71"
    #print(re.sub(r"\s*const\s*(\S+)\s*=\s*(\S+)", repl, text))
    #print(text)
#
    #import uncompyle6 as uc
    #
    #compcode =compile('map(lambda x: x ** 2, [i*2/2 for i in range(10)])', '<string>', 'eval', optimize=2)
    #with open('tmpout.py', 'w+') as file:
        #uc.deparse_code(3.5, compcode, file)
    #import py_compile
    #print(py_compile.compile("plyCompiler.py", optimize=2))
    #with open('tmpout.py', 'w+') as file:
        ##uc.deparse_code(3.5,py_compile.compile("pppCompiler.py"),file)
        #uc.decompile_file('__pycache__\plyCompiler.cpython-35.opt-2.pyc', file)

