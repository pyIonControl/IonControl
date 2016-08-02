# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
Parser for magnitude expressions. Can parse arithmetic expressions with values including standard si units.
"""

from functools import lru_cache

from pyparsing import Literal, CaselessLiteral, Word, Combine, Optional, nums, alphas, ParseException, srange

import logging
from modules.quantity import Q

point = Literal(".")
e = CaselessLiteral("E")
plus = Literal("+")
minus = Literal("-")
none = Literal("None")
nan = Literal("nan")
inf = Literal("inf")
ninf = Literal("-inf")


def integerConversion(loc, toks):
    toks['value'] = int(toks[0])
    return toks


def hexConversion(loc, toks):
    toks['value'] = int(toks[1], 16)
    return toks


def floatConversion(loc, toks):
    toks['value'] = float(toks[0])
    return toks


hexnum = (Literal("0x") + Word(srange("[0-9a-fA-F]"))).setResultsName('hex').setParseAction(hexConversion)
integer = Word("+-" + nums, nums).setResultsName('integer').setParseAction(integerConversion)
dotNumber = Combine(Optional(plus | minus) + point + Word(nums) +
                    Optional(e + Word("+-" + nums, nums))).setParseAction(floatConversion)
numfnumber = Combine(Optional(plus | minus) + Word(nums) +
                     point + Optional(Word(nums)) +
                     Optional(e + Word("+-" + nums, nums))).setParseAction(floatConversion)
fnumber = numfnumber | dotNumber
ident = Word(alphas, alphas + nums + "_$")

valueexpr = (nan | ninf | inf | none | (fnumber | hexnum | integer) + Optional(ident))
precisionexpr = (Word("+-" + nums, nums) + Optional(point + Optional(Word(nums, nums))))

specialValues = {"None": None,
                 "nan": float('nan'),
                 "inf": float('inf'),
                 "-inf": float('-inf')}


@lru_cache(maxsize=100)
def parse( string ):
    try:
        val = valueexpr.parseString( string )
        if val[0] in specialValues:
            return specialValues[val[0]]
        precres = precisionexpr.parseString( string )
        prec = len(precres[2]) if len(precres)==3 else 0
        retval = Q(float(val[0]), val[1] if len(val)>1 else None)  # TODO: might need precision
    except ParseException as e:
        logging.getLogger(__name__).error("Error parsing '{0}' using MagnitudeParser".format(string))
        raise
    return retval


@lru_cache(maxsize=100)
def parseDelta(string, deltapos=0, parseAll=True):
    string, deltapos = positionawareTrim(string, deltapos)
    val = valueexpr.parseString(string, parseAll=parseAll)
    precres = precisionexpr.parseString(string)
    prec = len(precres[2]) if len(precres) == 3 else 0
    decimalpos = len(precres[0])
    mydeltapos = max(2 if precres[0][0] == '-' else 1,
                     min(deltapos - (1 if deltapos > decimalpos else 0), decimalpos + prec))
    unit = val[1] if len(val) > 1 else ''
    retval = Q(val.get('value', float(val[0])), unit)
    delta = decimalpos - mydeltapos
    return retval, Q(pow(10, delta), unit), deltapos, decimalpos, prec


@lru_cache(maxsize=100)
def isValueExpression(text):
    try:
        p = valueexpr.parseString(text, parseAll=True)
        return 'hex' not in p.asDict()
    except Exception:
        pass
    return False


@lru_cache(maxsize=100)
def isIdentifier(text):
    try:
        ident.parseString(text, parseAll=True)
        return True
    except Exception:
        pass
    return False


def positionawareTrim(string, position):
    oldlen = len(string)
    string = string.lstrip()
    newlen = len(string)
    return string.rstrip(), min(max(position - oldlen + newlen, 0), newlen)


if __name__=="__main__":
    print(isValueExpression('2kHz'))
    print(parse("None"))
    print(parse("inf"))
    print(parse("nan"))
#     print positionawareTrim('   1234',10)
#     for line in ['12MHz', '12.123456789 MHz','-200.234e3 us','   12.000 MHz','40']:
#         try:
#             print line, "->"
#             for elem in parseDelta(line, 4):
#                 print elem
#             print
#         except ParseException as e:
#             print "not a full match", e
#      
