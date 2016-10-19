# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ast

class UserFuncAnalyzer(ast.NodeTransformer):
    def __init__(self):
        self.upd_funcs = set()
        self.varnames = set()
        self.ntvar = set()

    def visit_FunctionDef(self, node):
        if len(node.decorator_list):
            try:
                if 'userfunc' in map(lambda x: x.id, node.decorator_list):
                    self.upd_funcs.add(node.name)
            except:
                pass

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.varnames.add(node.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        if node.func.id == 'NamedTrace':
            if len(node.args) == 3:
                if isinstance(node.args[0], ast.Str):
                    self.ntvar.add(node.args[0].s+'_'+node.args[1].s)
                else:
                    self.ntvar.add((node.args[0].id, node.args[1].id))
            elif len(node.args) == 2:
                if isinstance(node.args[0], ast.Str):
                    self.ntvar.add(node.args[0].s)
                else:
                    self.ntvar.add(node.args[0].id)

    def walkNode(self, tree):
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and len(node.decorator_list) and
                        'userfunc' in map(lambda x: x.id, node.decorator_list)):
                self.upd_funcs.add(node.name)
                for item in node.body:
                    if hasattr(item, 'value') and isinstance(item.value, ast.Call) and item.value.func.id == 'NamedTrace':
                        if len(item.value.args) == 3:
                            if isinstance(item.value.args[0], ast.Str):
                                self.ntvar.add((node.name, 'str', item.value.args[0].s+'_'+item.value.args[1].s))
                            else:
                                self.ntvar.add((node.name, 'arg', (item.value.args[0].id, item.value.args[1].id)))
                        elif len(item.value.args) == 2:
                            if isinstance(item.value.args[0], ast.Str):
                                self.ntvar.add((node.name, 'str', item.value.args[0].s))
                            else:
                                self.ntvar.add((node.name, 'arg', item.value.args[0].id))

class FitFuncAnalyzer(ast.NodeTransformer):
    def __init__(self):
        self.retlines = set()
        self.declist = list()

    def visit_Return(self, node):
        self.retlines.add(node.lineno)

    def visit_FunctionDef(self, node):
        if len(node.decorator_list):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Attribute):
                    self.declist.append(dec.value.id)
                if isinstance(dec, ast.Call):
                    if hasattr(dec, 'func'):
                        if hasattr(dec.func, 'value'):
                            self.declist.append(dec.func.value.id)
        self.generic_visit(node)


