# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

#"""
#3rd generation of Expression, used for parsing arithmetic, units and custom functions in combo boxes
#this version uses PLY and is modeled off of http://www.dabeaz.com/ply/example.html
#"""

import inspect
import math
from collections import ChainMap

import numpy
import ply.lex as lex
import ply.yacc as yacc
import logging
import expressionFunctions.UserFunctions as UserFunctions
from expressionFunctions.ExprFuncDecorator import ExpressionFunctions, userfunc, UserFuncCls
from modules.quantity import Q, is_Q


class ExpressionError(Exception):
    pass


class Parser:
    def __init__(self, variabledict=dict(), functiondict=dict()):
        self.dependencies = set()
        self.val = 0
        self.lexer = lex.lex(module=self)
        self.parser = yacc.yacc(module=self, debug=False,  picklefile='parsetab_expression.pkl')

        self.useFloat = False
        self.epsilon = 1e-12
        self.constLookup = {'PI': math.pi,
                            'pi': math.pi,
                            'E':  math.e,
                            'e':  math.e,
                            'True':  True,
                            'False': False
                            }
        self.localFunctions = {'round':   round,
                               'sqrt':    numpy.sqrt,
                               'trunc':   int,
                               'sin':     self.nounitgen(math.sin),
                               'cos':     self.nounitgen(math.cos),
                               'tan':     self.nounitgen(math.tan),
                               'acos':    self.nounitgen(math.acos),
                               'asin':    self.nounitgen(math.asin),
                               'atan':    self.nounitgen(math.atan),
                               'degrees': self.nounitgen(math.degrees),
                               'radians': self.nounitgen(math.radians),
                               'erf':     self.nounitgen(math.erf),
                               'erfc':    self.nounitgen(math.erfc),
                               'abs':     abs,
                               'exp':     math.exp,
                               'sign':    lambda a: abs(a)>self.epsilon and (1 if a > 0 else -1) or 0,
                               'sgn':     lambda a: abs(a)>self.epsilon and (1 if a > 0 else -1) or 0,
                               'sint16':  lambda a: -0x8000 + (int(a) & 0x7fff) if (int(a) & 0x8000) else (int(a) & 0x7fff),
                               'sint12':  lambda a: -0x800 + (int(a) & 0x7ff) if (int(a) & 0x800) else (int(a) & 0x7ff),
                               'sint32':  lambda a: -0x80000000 + (int(a) & 0x7fffffff) if (int(a) & 0x80000000) else (int(a) & 0x7fffffff),
                               }
        self.defaultVarCM = ChainMap(variabledict, self.constLookup)
        self.defaultFuncCM = ChainMap(ExpressionFunctions, self.localFunctions, functiondict)
        self.variableCM = self.defaultVarCM
        self.functionCM = self.defaultFuncCM

    def nounitgen(self, fun):
        def retfun(x):
            if (not is_Q(x)) or x.dimensionless:
                return fun(x)
            else:
                raise ValueError("Must be dimensionless!")
        return retfun

    # Token rules
    tokens = (
        'NAME','INT','FLOAT','POW', 'MOD', 'GT', 'GTE', 'LT', 'LTE',
        'EQ', 'NEQ', 'PLUS','MINUS','TIMES','DIVIDE','EQUALS',
        'LPAREN','RPAREN','COMMA','RBRACK','LBRACK',
        'RBRACE','LBRACE','COLON', 'STRING'
        )

    t_PLUS    = r'\+'
    t_MINUS   = r'-'
    t_TIMES   = r'\*'
    t_DIVIDE  = r'/'
    t_POW     = r'\^'
    t_MOD     = r'\%'
    t_GT      = r'>'
    t_GTE     = r'>='
    t_LT      = r'<'
    t_LTE     = r'<='
    t_EQ      = r'=='
    t_NEQ     = r'!='
    t_EQUALS  = r'='
    t_LPAREN  = r'\('
    t_RPAREN  = r'\)'
    t_NAME    = r'[a-zA-Z_][a-zA-Z0-9_]*'
    t_COMMA   = r','
    t_LBRACK  = r'\['
    t_RBRACK  = r'\]'
    t_LBRACE  = r'\{'
    t_RBRACE  = r'\}'
    t_COLON   = r':'

    def t_STRING(self, t):
        r'[\'|"]([^\'"]+)[\'|"]'
        t.value = str(t.value[1:-1])
        return t

    def t_FLOAT(self, t):
        r'\d*((\.\d*)([eE][+-]?\d+)?|([eE][+-]?\d+))'
        t.value = float(t.value)
        return t

    def t_INT(self, t):
        r'(0x[0-9a-fA-F]+|0o[0-7]+|\d+)'
        if t.value.startswith('0x'):
            t.value = int(t.value[2:], 16)
        elif t.value.startswith('0o'):
            t.value = int(t.value[2:], 8)
        elif self.useFloat:
            t.value = float(t.value)
        else:
            t.value = int(t.value)
        return t

    t_ignore = " \t"

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    # Parsing rules
    precedence = (
        ('left', 'MOD'),
        ('left','PLUS','MINUS'),
        ('left','TIMES','DIVIDE'),
        ('right','UMINUS'),
        ('right','POW'),
        ('left', 'GT', 'GTE', 'LT', 'LTE', 'EQ', 'NEQ')
    )

    def p_statement_expr(self, p):
        'statement : expression'
        self.val = p[1]
        return p[1]

    def p_expression_binop(self, p):
        '''expression : expression PLUS expression
                      | expression MINUS expression
                      | expression TIMES expression
                      | expression DIVIDE expression
                      | expression POW expression
                      | expression MOD expression
                      | expression GT expression
                      | expression GTE expression
                      | expression LT expression
                      | expression LTE expression
                      | expression EQ expression
                      | expression NEQ expression'''
        if p[2] == '+'  : p[0] = p[1] + p[3]
        elif p[2] == '-': p[0] = p[1] - p[3]
        elif p[2] == '*': p[0] = p[1] * p[3]
        elif p[2] == '/': p[0] = p[1] / p[3]
        elif p[2] == '^': p[0] = p[1] ** p[3]
        elif p[2] == '%': p[0] = p[1] % p[3]
        elif p[2] == '>': p[0] = p[1] > p[3]
        elif p[2] == '>=': p[0] = p[1] >= p[3]
        elif p[2] == '<' : p[0] = p[1] < p[3]
        elif p[2] == '<=': p[0] = p[1] <= p[3]
        elif p[2] == '==': p[0] = p[1] == p[3]
        elif p[2] == '!=': p[0] = p[1] != p[3]

    def p_expression_uminus(self, p):
        'expression : MINUS expression %prec UMINUS'
        p[0] = -p[2]

    def p_expression_mag(self, t):
        '''expression : FLOAT NAME
                      | INT NAME'''
        t[0] = Q(t[1], t[2])

    def p_expression_number(self, t):
        '''expression : FLOAT
                      | INT'''
        t[0] = t[1]

    def p_expression_string(self, p):
        'expression : STRING'
        p[0] = p[1]

    def p_expression_func(self, t):
        '''expression : NAME LPAREN arglist RPAREN
                      | NAME LPAREN kwarglist RPAREN
                      | NAME LPAREN arglist COMMA kwarglist RPAREN'''
        if len(t) == 7:
            t[0] = self.functionCM[t[1]](*t[3], **t[5])
            if t[1] in ExpressionFunctions:
                self.dependencies.add(t[1])
                self.getNTDeps(t[1], *t[3], **t[5])
        elif len(t) == 5:
            if type(t[3]) is dict:
                t[0] = self.functionCM[t[1]](**t[3])
                if t[1] in ExpressionFunctions:
                    self.dependencies.add(t[1])
                    self.getNTDeps(t[1], **t[3])
            else:
                t[0] = self.functionCM[t[1]](*t[3])
                if t[1] in ExpressionFunctions:
                    self.dependencies.add(t[1])
                    self.getNTDeps(t[1], *t[3])

    def getNTDeps(self, key, *args, **kwargs):
        if isinstance(self.functionCM[key], UserFuncCls):
            if self.functionCM[key].deps:
                fn = self.functionCM[key]
                for d in fn.deps:
                    if d[1] == 'str':
                        self.dependencies.add('_NT_'+d[2].split('_')[0])
                    elif d[1] == 'arg':
                        boundSig = fn.sig.bind(*args, **kwargs)
                        boundSig.apply_defaults()
                        self.dependencies.add('_NT_'+boundSig.arguments[d[2]].split('_')[0])

    def p_expression_name(self, t):
        'expression : NAME'
        t[0] = self.variableCM[t[1]]
        if t[1] not in self.constLookup:
            self.dependencies.add(t[1])

    def p_expression_namewunit(self, t):
        'expression : NAME NAME'
        logger = logging.getLogger(__name__)
        logger.warning( "Expression format '{0} {1}' is deprecated!".format(t[1], t[2]))
        var = self.variableCM[t[1]]
        if is_Q(var) and var.u == '':
            var = Q(var.m, t[2])
        else:
            var = Q(var.m_as(t[2]), t[2])
        t[0] = var
        if t[1] not in self.constLookup:
            self.dependencies.add(t[1])

    def p_arglist(self, t):
        '''arglist : expression
                   | arglist COMMA expression'''
        if len(t) == 2:
            t[0] = [t[1]]
        else:
            t[0] = t[1] + [t[3]]

    def p_kwarglist(self, t):
        '''kwarglist : NAME EQUALS expression
                     | kwarglist COMMA NAME EQUALS expression'''
        if len(t) == 4:
            t[0] = {t[1]: t[3]}
        else:
            t[0] = t[1]
            t[0].update({t[3]: t[5]})

    def p_expression_list(self, t):
        'expression : LBRACK listentry RBRACK'
        t[0] = t[2]

    def p_expression_dict(self, t):
        'expression : LBRACE dictentry RBRACE'
        t[0] = t[2]

    def p_listentry(self, t):
        '''listentry : expression
                     | listentry COMMA expression'''
        if len(t) == 2:
            t[0] = [t[1]]
        else:
            t[0] = t[1] + [t[3]]

    def p_dictentry(self, t):
        '''dictentry : expression COLON expression
                     | dictentry COMMA expression COLON expression'''
        if len(t) == 4:
            t[0] = {t[1]: t[3]}
        else:
            t[0] = t[1]
            t[0].update({t[3]: t[5]})

    def p_expression_group(self, p):
        'expression : LPAREN expression RPAREN'
        p[0] = p[2]

    def p_error(self, p):
        raise ExpressionError("Syntax error at '{0}' in '{1}'".format(p.value, p.lexer.lexdata))

    def evaluate(self, s, variabledict=dict(), listDependencies=False, useFloat=False, functiondict=dict()):
        self.dependencies = set()
        self.useFloat = useFloat
        self.variableCM = ChainMap(variabledict, self.defaultVarCM)
        self.functionCM = ChainMap(functiondict, self.defaultFuncCM)
        self.parser.parse(s, lexer=self.lexer)
        if listDependencies:
            return self.val, self.dependencies
        return self.val

    def evaluateAsMagnitude(self, s, variabledict=dict(), listDependencies=False, useFloat=False, functiondict=dict()):
        self.dependencies = set()
        self.useFloat = useFloat
        self.variableCM = ChainMap(variabledict, self.defaultVarCM)
        self.functionCM = ChainMap(functiondict, self.defaultFuncCM)
        self.parser.parse(s, lexer=self.lexer)
        if isinstance(self.val, bool):
            if self.val:
                self.val = Q(1)
            else:
                self.val = Q(0)
        else:
            self.val = Q(self.val)

        if listDependencies:
            return self.val, self.dependencies
        return self.val


class Expression:
    exprParser = Parser()
    def evaluate(self, s, variabledict=dict(), listDependencies=False, useFloat=False, functiondict=dict()):
        return self.exprParser.evaluate(s, variabledict, listDependencies, useFloat, functiondict)

    def evaluateAsMagnitude(self, s, variabledict=dict(), listDependencies=False, useFloat=False, functiondict=dict()):
        return self.exprParser.evaluateAsMagnitude(s, variabledict, listDependencies, useFloat, functiondict)

if __name__ == "__main__":
    from time import time
    start_time = time()
    tests = """2*2
          { 'A':1, 'B':2, 'C': {'a': 1.2, 'b': 3.4} }
           16.8 MHz
           3.14159
           42
           1E6
           -.43
           6.02E23
           6.02e+023
           1.0e-7
           1+2
           9+3+6
           3^2+4*-3+5+6+7+9/5/4/3*3*(4*4+4*5)
           PI
           round(3.21)
           round(PI)
           (sqrt(1 s / 2 s))
           0x0000000000000001
           sin(pi/2)
           [1,2,3,4]
           1>2
           3>1
           5==2
           5==5
           4!=2
           4!=4
           'a quoted string'""".split("\n")

    ExprEvalOld = Expression()
    for teststr in tests:
        print("Test:", teststr.strip())
        result = ExprEvalOld.evaluate(teststr, useFloat=False)
        print("Result:", result)
        try:
            for dd in result:
                if isinstance(dd,dict): print(dd.items())
        except TypeError as te:
            pass
        print()

    ExprEval = Expression()
    def test( s, expVal, variabledict=dict(), listDependencies=False):
        try:
            if listDependencies:
                vall,deps = ExprEval.evaluate( s, variabledict, listDependencies, useFloat=True )
            else:
                vall = ExprEval.evaluate( s, variabledict, listDependencies, useFloat=False )
            if vall == expVal:
                print(s, "=", expVal)
            else:
                print(s+"!!!", vall, "!=", expVal)
        except Exception as e:
            print("failed")

    if True:
        test( "9", 9 )
        test( "-9", -9 )
        test( "-E", -math.e )
        test( "9 + 3 + 6", 9 + 3 + 6 )
        test( "9 + 3 / 11", 9 + 3.0 / 11 )
        test( "(9 + 3)", (9 + 3) )
        test( "(9+3) / 11", (9+3.0) / 11 )
        test( "9 - 12 - 6", 9 - 12 - 6 )
        test( "9 - (12 - 6)", 9 - (12 - 6) )
        test( "2*3.14159", 2*3.14159 )
        test( "3.1415926535*3.1415926535 / 10", 3.1415926535*3.1415926535 / 10 )
        test( "PI * PI / 10", math.pi * math.pi / 10 )
        test( "PI*PI/10", math.pi*math.pi/10 )
        test( "PI^2", math.pi**2 )
        test( "round(PI^2)", round(math.pi**2) )
        test( "6.02E23 * 8.048", 6.02E23 * 8.048 )
        test( "e / 3", math.e / 3 )
        test( "sin(pi/2)", math.sin(math.pi/2) )
        test( "trunc(E)", int(math.e) )
        test( "trunc(-E)", int(-math.e) )
        test( "round(E)", round(math.e) )
        test( "round(-E)", round(-math.e) )
        test( "E^PI", math.e**math.pi )
        test( "2^3^2", 2**3**2 )
        test( "2^3+2", 2**3+2 )
        test( "2^9", 2**9 )
        test( ".5", 0.5)
        test( "-.7", -0.7)
        test( "-.7ms", Q(-0.7, "ms"))
        test( "sgn(-2)", -1 )
        test( "sgn(0)", 0 )
        test( "sgn(0.1)", 1 )
        test( "2*(3+5)", 16 )
        test( "2*(alpha+beta)", 14, {'alpha':5,'beta':2} )
        #test("kwfun(tempfun(4),2,3,f=10,d=9)", UserFunctions.kwfun(UserFunctions.tempfun(4),2,3,f=10,d=9))
        #test("kwfun(tempfun(4),2,3,f=10,d=myvar,verbose=1)", UserFunctions.kwfun(UserFunctions.tempfun(4),2,3,f=10,d=124),{'myvar':124},listDependencies=True)
        test( "-4 MHz", Q(-4, 'MHz') )
        test( "2*4 MHz", Q(8, 'MHz') )
        test( "2 * sqrt( 4 s / 1 s)", 4 )
        test("[1,2,3,4]",[1,2,3,4])
        test( "sqrt( 4s*4s )", Q(4, 's'))
        test( "piTime", Q(10, 'ms'), {'piTime':Q(10, 'ms')},listDependencies=True)

    print("elapsed time:",time()-start_time)

