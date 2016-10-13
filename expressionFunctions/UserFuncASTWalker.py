# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ast

class CodeAnalyzer(ast.NodeTransformer):
    def __init__(self):
        self.upd_funcs = set()
        self.varnames = set()
        self.ntvar = set()

    def visit_FunctionDef(self, node):
        if len(node.decorator_list):
            if 'userfunc' in map(lambda x: x.id, node.decorator_list):
                self.upd_funcs.add(node.name)

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

