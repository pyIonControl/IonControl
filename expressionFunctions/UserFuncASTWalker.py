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

    def visit_FunctionDef(self, node):
        if len(node.decorator_list):
            if 'userfunc' in map(lambda x: x.id, node.decorator_list):
                self.upd_funcs.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.varnames.add(node.id)
        self.generic_visit(node)

