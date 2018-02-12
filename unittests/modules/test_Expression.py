# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import unittest
from modules.Expression import Expression
import math
from modules.quantity import Q
ExprEval = Expression()
import pytest

def e(expr, vars=dict(), useFloat=False):
    return ExprEval.evaluate(expr, vars, useFloat=useFloat)

class TestExpression(unittest.TestCase):
    def test_sint16(self):
        self.assertEqual(e("sint16(y)", {'y': 150}), 150)
        self.assertEqual(e("sint16(y)", {'y': 0x7123}), 0x7123)
        self.assertEqual(e("sint16(y)", {'y': 0x8000}), -32768)
        self.assertEqual(e("sint16(y)", {'y': 0xffff}), -1)
        self.assertEqual(e("sint16(y)", {'y': 15.0}), 15)

    def test_sint12(self):
        self.assertEqual(e("sint12(y)", {'y': 150}), 150)
        self.assertEqual(e("sint12(y)", {'y': 0x712}), 0x712)
        self.assertEqual(e("sint12(y)", {'y': 0x800}), -2048)
        self.assertEqual(e("sint12(y)", {'y': 0xfff}), -1)

    def test_sint32(self):
        self.assertEqual(e("sint32(y)", {'y': 150}), 150)
        self.assertEqual(e("sint32(y)", {'y': 0x71234567}), 0x71234567)
        self.assertEqual(e("sint32(y)", {'y': 0x80000000}), -2147483648)
        self.assertEqual(e("sint32(y)", {'y': 0xffffffff}), -1)

    def test_literals(self):
        self.assertEqual(e("9"), 9)
        self.assertEqual(e('-9'), -9)
        self.assertEqual(e('--9'), 9)
        self.assertEqual(e('-E'), -math.e)
        self.assertEqual(e('9 + 3 + 6 + 25'), 9 + 3 + 6 + 25)
        self.assertEqual(e("9 + 3 / 11"), 9 + 3 / 11)
        self.assertEqual(e('9 * (7 + 28) / 12'), 9 * (7 + 28) / 12)
        self.assertEqual(e("9 - 12 - 6"), 9 - 12 - 6)
        self.assertEqual(e("9 - (12 - 6)"), 9 - (12 - 6))
        self.assertEqual(e("2 * 3.14159"), 2 * 3.14159)
        self.assertEqual(e("3.1415926535 * 3.1415926535 / 10"), 3.1415926535 * 3.1415926535 / 10)
        self.assertEqual(e("PI * PI / 10"), math.pi * math.pi / 10)
        self.assertEqual(e("PI^2"), math.pi**2)
        self.assertEqual(e("round(PI^2)"), round(math.pi**2))
        self.assertEqual(e("6.02E23 * 8.048"), 6.02E23 * 8.048)
        self.assertEqual(e("e / 3"), math.e / 3)
        self.assertEqual(e("sin(pi/2)"), math.sin(math.pi/2))
        self.assertEqual(e("trunc(E)"), int(math.e) )
        self.assertEqual(e("trunc(-E)"), int(-math.e) )
        self.assertEqual(e("round(E)"), round(math.e) )
        self.assertEqual(e("round(-E)"), round(-math.e) )
        self.assertEqual(e("E^PI"), math.e**math.pi )
        self.assertEqual(e("2^3^2"), 2**3**2 )
        self.assertEqual(e("2^3+2"), 2**3+2 )
        self.assertEqual(e("2^9"), 2**9 )
        self.assertEqual(e(".5"), 0.5)
        self.assertEqual(e("-.7"), -0.7)
        self.assertEqual(e("-.7ms"), Q(-0.7, "ms"))
        self.assertEqual(e("sgn(-2)"), -1 )
        self.assertEqual(e("sgn(0)"), 0 )
        self.assertEqual(e("sgn(0.1)"), 1 )
        self.assertEqual(e("2*(3+5)"), 16 )
        self.assertEqual(e("2*(alpha+beta)", {'alpha':5,'beta':2}), 14)
        self.assertEqual(e("-4 MHz"), Q(-4, 'MHz') )
        self.assertEqual(e("2*4 MHz"), Q(8, 'MHz') )
        self.assertEqual(e("2 * sqrt( 4s / 1 s)"), 4 )
        self.assertEqual(e("sqrt ( 4 s*4 s )"), Q(4, 's'))
        self.assertEqual(e("piTime", {'piTime':Q(10, 'ms')}), Q(10, 'ms'))
        self.assertEqual(e("0xff"), Q(255))
        self.assertEqual(e("(4s)^2"), Q(16, 's*s'))
        self.assertEqual(e("x0+sqrt(s^2*(A/(12-O)-1))",
                           {'x0': Q(0), 's': 1, 'A': Q(20), 'O': Q(0)}),
                         math.sqrt(20 / 12 - 1))
        self.assertEqual(e("sqrt(sin(round(pi)^2/17)^2+1)*1 MHz"),math.sqrt(math.sin(round(math.pi)**2/17)**2+1)*Q(1,'MHz'))
