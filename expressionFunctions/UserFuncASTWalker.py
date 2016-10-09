import ast

class CodeAnalyzer(ast.NodeTransformer):
    def __init__(self):
        self.upd_funcs = set()

    def visit_FunctionDef(self, node):
        if len(node.decorator_list):
            if 'userfunc' in map(lambda x: x.id, node.decorator_list):
                self.upd_funcs.add(node.name)
        self.generic_visit(node)

