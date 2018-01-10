
# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import OrderedDict
import inspect
from . import Builtins
from .CompileException import SymbolException

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

class FunctionSymbol(Symbol):
    def __init__(self, name, block=None):
        super(FunctionSymbol, self).__init__(name)
        self.block = block

    def codegen(self, symboltable, arg=list(), kwarg=dict()):
        if len(arg)>1:
            raise SymbolException( "defined functions cannot have arguments" )
        return self.block

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
        if name not in self or not isinstance( self[name], FunctionSymbol):
            raise SymbolException("Function '{0}' is not defined".format(name))
        return self[name]

    def checkAvailable(self, name):
        if name in self:
            raise SymbolException("symbol {0} already exists.".format(name))

    def getAllConst(self):
        return [value for value in list(self.values()) if isinstance(value, ConstSymbol)]

    def getAllVar(self):
        return [value for value in list(self.values()) if isinstance(value, VarSymbol)]



