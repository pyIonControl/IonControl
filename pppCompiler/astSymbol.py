# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import OrderedDict
import inspect
from . import Builtins
#import Builtins
from .CompileException import SymbolException
import re

class Symbol(object):
    def __init__(self, name):
        self.name = name

class ConstSymbol(Symbol):
    def __init__(self, name, value):
        super(ConstSymbol, self).__init__(name)
        self.value = value

class VarSymbol(Symbol):
    def __init__(self, type_=None, encoding=None, name=None, value=None, unit=None):
        super(VarSymbol, self).__init__(name)
        self.type_ = type_
        self.encoding = encoding
        self.value = value
        self.unit = unit

class AssemblyFunctionSymbol(Symbol):
    def __init__(self, name, block=None, argn=list(), kwargn=OrderedDict(), nameSpace=None, symbols=None, maincode=None, returnval=False, inline=True, startline=0):
        super().__init__(name)
        self.name = name
        self.startline = startline
        self.block = [l+"   # PPP LINE: {0:>4}".format(lineno+self.startline+3) for lineno,l in enumerate(list(map(lambda x: x.lstrip(), block.lstrip().rstrip().splitlines())))]
        self.argn, self.kwargn, self.nameSpace, self.symbols, \
        self.maincode, self.returnval, self.inline = argn, kwargn, nameSpace, symbols, maincode, returnval, inline

    def substituteReferenceVars(self, args, kwargs):
        subBlock = []
        if len(args)>1:
            fullargs = args[1:]+[val for val in kwargs.values()]
        else:
            fullargs = [val for val in kwargs.values()]
        fullargn = self.argn+[k for k in self.kwargn.keys()]
        for i,st in enumerate(self.block):
            if isinstance(st, str):
                newstr = st
                for argn, argv in zip(fullargn, fullargs):
                    substr = argn if self.nameSpace+'_' not in argn else argn.split(self.nameSpace+'_')[-1]
                    newstr = re.sub(r" {}".format(substr), ' '+argv, st)
                    #if newstr != st:
                        #break
                subBlock.append(newstr)
            else:
                return self.block
        return subBlock

    def codegen(self, symboltable, arg=list(), kwarg=dict()):
        return self.substituteReferenceVars(arg, kwarg)

class FunctionSymbol(Symbol):
    passByReferenceCheckCompleted = False
    def __init__(self, name, block=None, argn=list(), kwargn=OrderedDict(), nameSpace=None, symbols=None, maincode=None, returnval=False, inline=False, startline=0):
        super(FunctionSymbol, self).__init__(name)
        self.block = block
        self.startline = startline
        self.codestr = list()
        self.nameSpace = nameSpace
        self.argn = argn
        self.kwargn = kwargn
        self.symbols = symbols
        self.maincode = maincode
        self.labelsCustomized = False
        self.name = name
        self.variablesPassedByReference = set()
        self.returnval = returnval
        self.startLabel = "begin_function_{}_label_0".format(self.name)
        self.inline = inline
        #self.startLabel = ["begin_function_{}_label_0: NOP".format(self.name)]

    def instantiateInputParameters(self, args=list(), kwargs=dict()):
        self.codestr = list()
        fullargn = self.argn+[k for k in self.kwargn.keys()]
        if len(args)>1:
            for i,arg in enumerate(args[1:]):
                if fullargn[i] not in self.variablesPassedByReference:
                    if self.nameSpace:
                        argf = self.nameSpace+'_{}'.format(arg)
                        if argf not in self.symbols.keys():
                            argf = arg
                    else:
                        argf = arg
                    self.codestr += self.maincode.ppFormatLine(["LDWR {0}\nSTWR {1}".format(argf, fullargn[i])], self.startline)
        for k,v in kwargs.items():
            if k not in self.variablesPassedByReference:
                if self.nameSpace:
                    argf = self.nameSpace+'_{}'.format(v)
                    if argf not in self.symbols.keys():
                        argf = v
                else:
                    argf = v
                self.codestr += self.maincode.ppFormatLine(["LDWR {0}\nSTWR {1}".format(argf, k)], self.startline)
        return True

    def incrementLabels(self, repstr, ctr):
        mset = set()
        for i,st in enumerate(self.block):
            if isinstance(st, str):
                m = re.search(repstr, st)
                if m:
                    mset.add(int(m.group(2)))
                    self.block[i]=re.sub(repstr, lambda s: self.repLabels(s,ctr), st)
        return len(mset)+1 #+1 prevents weird race condition that screws up labeling (once out of every ~10 runs with the same code)

    def incrementTags(self):
        self.maincode.ifctr += self.incrementLabels(r"(if_\S+_label_)(\d+)", self.maincode.ifctr)
        self.maincode.orctr += self.incrementLabels(r"(or_\S+_label_)(\d+)", self.maincode.orctr)
        self.maincode.elsectr += self.incrementLabels(r"(else_\S+_label_)(\d+)", self.maincode.elsectr)
        self.maincode.whilectr += self.incrementLabels(r"(while_\S+_label_)(\d+)", self.maincode.whilectr)
        self.maincode.fnctr += self.incrementLabels(r"(end_function_\S+_label_)(\d+)", self.maincode.fnctr)

    def repLabels(self, m, inc):
        incval = int(m.group(2))+inc
        return '{0}{1}'.format(m.group(1),incval)

    def customizeLabels(self):
        self.labelsCustomized = True
        for i,st in enumerate(self.block):
            if isinstance(st, str):
                m = re.search(r"(or_|while_|if_|function_|else_)+(label_)(\d+)", st)
                if m:
                    self.block[i]=re.sub(r"(or_|while_|if_|function_|else_)+(label_)(\d+)", lambda s: m.group(1)+self.name+'_{0}{1}'.format(m.group(2),m.group(3)), st)
            else:
                self.labelsCustomized = False

    def checkForVariablesPassedByReference(self):
        overwrittenVars = set()
        self.passByReferenceCheckCompleted = True
        fullargs = self.argn+[k for k in self.kwargn.keys()]
        for i,st in enumerate(self.block):
            if isinstance(st, str):
                for fargn in fullargs:
                    m = re.search(r"STWR (\S+)".format(fargn), st)
                    if m:
                        if m.group(1) in self.argn:
                            overwrittenVars.add(m.group(1))
            else:
                self.passByReferenceCheckCompleted = False
                return
        self.variablesPassedByReference = set(fullargs)-overwrittenVars

    def substituteReferenceVars(self, args, kwargs):
        if not self.variablesPassedByReference:
            return self.block
        subBlock = []
        if len(args)>1:
            fullargs = args[1:]+[val for val in kwargs.values()]
        else:
            fullargs = [val for val in kwargs.values()]
        fullargn = self.argn+[k for k in self.kwargn.keys()]
        for i,st in enumerate(self.block):
            if isinstance(st, str):
                newstr = st
                for override in self.variablesPassedByReference:
                    if override in self.kwargn.keys() and override.split(self.nameSpace+'_')[1] not in kwargs.keys() and \
                                    override not in fullargn[0:len(fullargs)]:
                        newstr = re.sub(override, self.kwargn[override], st) #pass in defaults for unmodified kw defaults
                    elif override.split(self.nameSpace+'_')[1] in kwargs.keys():#[self.nameSpace+'_'+k for k in kwargs.keys() if self.nameSpace]:
                        newstr = re.sub(override, kwargs[override.split(self.nameSpace+'_')[1]], st)
                    else:
                        newstr = re.sub(override, fullargs[fullargn.index(override)], st)
                subBlock.append(newstr)
            else:
                self.passByReferenceCheckCompleted = False
                return self.block
        return subBlock

    def codegenInit(self, symboltable, arg=list(), kwarg=dict()):
        if not self.inline:
            if not self.labelsCustomized:
                self.customizeLabels()
            self.incrementTags()
            overrideBlock = self.block
            localBlock = [self.startLabel+': NOP']+overrideBlock+["JMPPOP\n"]
            return localBlock
        return ["\n"]

    def codegen(self, symboltable, arg=list(), kwarg=dict()):
        if self.inline:
            if not self.labelsCustomized:
                self.customizeLabels()
            if not self.passByReferenceCheckCompleted:
                self.checkForVariablesPassedByReference()
        self.instantiateInputParameters(arg,kwarg)
        if self.inline:
            self.incrementTags()
            overrideBlock = self.substituteReferenceVars(arg, kwarg)
            localBlock = self.codestr+overrideBlock
        else:
            localBlock = self.codestr+self.maincode.ppFormatLine("JMPPUSH {}".format(self.startLabel).split('\n'), self.startline)
        return localBlock

class Builtin(FunctionSymbol):
    def __init__(self, name, codegen):
        super(Builtin, self).__init__(name)
        self.codegen = codegen
        self.doc = inspect.getdoc(codegen)

class SymbolTable(OrderedDict):

    def __init__(self):
        super(SymbolTable, self).__init__()
        self.addBuiltins()
        self.inlineParameterValues = dict()
        self.setInlineParameter( 'NULL', 0 )
        self.setInlineParameter( 'FFFFFFFF', 0xffffffffffffffff )
        self.setInlineParameter( 'INTERRUPT_EXITCODE', 0xfffe100000000000 )
        self.labelNumber = 0

    def addBuiltins(self):
        self['set_shutter'] = Builtin('set_shutter', Builtins.set_shutter)
        self['set_inv_shutter'] = Builtin('set_inv_shutter', Builtins.set_inv_shutter)
        self['set_counter'] = Builtin('set_counter', Builtins.set_counter)
        self['clear_counter'] = Builtin('clear_counter', Builtins.clear_counter)
        self['update'] = Builtin('update', Builtins.update)
        self['load_count'] = Builtin('load_count', Builtins.load_count)
        self['set_trigger'] = Builtin( 'set_trigger', Builtins.set_trigger )
        self['set_dds'] = Builtin( 'set_dds', Builtins.set_dds)
        self['read_pipe'] = Builtin( 'read_pipe', Builtins.read_pipe )
        self['write_pipe'] = Builtin( 'write_pipe', Builtins.write_pipe )
        self['exit'] = Builtin( 'exit', Builtins.exit_ )
        self['pipe_empty'] = Builtin( 'pipe_empty', Builtins.pipe_empty )
        self['apply_next_scan_point'] = Builtin( 'apply_next_scan_point', Builtins.apply_next_scan_point )
        self['set_ram_address'] = Builtin( 'set_ram_address', Builtins.set_ram_address )
        self['read_ram'] = Builtin( 'read_ram', Builtins.read_ram )
        self['wait_dds'] = Builtin( 'wait_dds', Builtins.wait_dds )
        self['wait_trigger'] = Builtin( 'wait_trigger', Builtins.wait_trigger )
        self['write_result'] = Builtin( 'write_result', Builtins.write_result )
        self['serial_write'] = Builtin( 'serial_write', Builtins.serial_write )
        self['set_parameter'] = Builtin( 'set_parameter', Builtins.set_parameter )
        self['set_dac'] = Builtin( 'set_dac', Builtins.set_dac )
        self['pulse'] = Builtin( 'pulse', Builtins.pulse )
        self['rand'] = Builtin('rand', Builtins.rand)
        self['rand_seed'] = Builtin('rand_seed', Builtins.rand_seed)
        self['set_sync_time'] = Builtin('set_sync_time', Builtins.set_sync_time)
        self['wait_sync'] = Builtin('wait_sync', Builtins.wait_sync)
        self['nop'] = Builtin('nop', Builtins.nop)

    def setInlineParameter(self, name, value):
        self.inlineParameterValues[value] = name
        self[name] = VarSymbol(name=name, value=value)

    def getInlineParameter(self, prefix, value):
        if value not in self.inlineParameterValues:
            name = "{0}_{1}".format(prefix, len(self.inlineParameterValues))
            self.inlineParameterValues[value] = name
            self[name] = VarSymbol(name=name, value=value)
        return self.inlineParameterValues[value]

    def getLabelNumber(self):
        self.labelNumber += 1
        return self.labelNumber

    def getConst(self, name):
        """get a const symbol"""
        if name not in self or not isinstance( self[name], ConstSymbol):
            raise SymbolException("Constant '{0}' is not defined".format(name))
        return self[name]

    def getVar(self, name, type_=None):
        """check for the availability and type of a vaiabledefinition"""
        if name not in self or not isinstance( self[name], VarSymbol):
            raise SymbolException("Variable '{0}' is not defined".format(name))
        var = self[name]
        if type_ is not None and var.type_!=type_:
            raise SymbolException("Variable '{0}' is of type {1}, required type: {2}".format(name, var.type_, type_))
        return self[name]

    def getProcedure(self, name):
        if name not in self or (not isinstance( self[name], FunctionSymbol) and not isinstance( self[name], AssemblyFunctionSymbol)):
            raise SymbolException("Function '{0}' is not defined".format(name))
        return self[name]

    def checkAvailable(self, name):
        if name in self:
            raise SymbolException("symbol {0} already exists.".format(name))

    def getAllConst(self):
        return [value for value in list(self.values()) if isinstance(value, ConstSymbol)]

    def getAllVar(self):
        return [value for value in list(self.values()) if isinstance(value, VarSymbol)]



