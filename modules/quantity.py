# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from pint import UnitRegistry, set_application_registry
from functools import lru_cache
from pint.util import UnitsContainer, infer_base_unit

ureg = UnitRegistry()
ureg.default_format = "~"
ureg.define('samples = count / second')
ureg.define('sample = count / second')
set_application_registry(ureg)
Q = ureg.Quantity


# define a hash function for quantity
def quantityHash(self):
    return hash(self.to_tuple())

Q.__hash__ = quantityHash


def is_Q(q):
    return isinstance(q, Q)


def to_Q(value, unit):
    try:
        return (Q(v, unit) for v in value)
    except TypeError:  # not iterable
        return Q(value, unit)


def value(q, unit=""):
    if is_Q(q):
        return q.m_as(unit)
    if not unit or not q:
        return q
    raise ValueError("no defined value for {0} in units '{1}'".format(q, unit))


def chop(q, unit=None):
    if not is_Q(q):
        return q
    try:
        return q.m_as(unit)
    except Exception:
        return q.m


def mag_unit(q):
    return q.m, "{:~}".format(q.units)


class QuantityError(Exception):
    pass

simplifications = (UnitsContainer({'joule': 1, 'newton': -1, 'meter': -1}),
                   UnitsContainer({'newton': 1, 'gram': -1, 'meter': -1, 'second': 2}),
                   UnitsContainer({'watt': 1, 'joule': -1, 'second': 1}),
                   UnitsContainer({'pascal': 1, 'newton': -1, 'meter': 2}),
                   UnitsContainer({'farad': 1, 'coulomb': -1, 'volt': 1}),
                   UnitsContainer({'ohm': 1, 'volt': -1, 'ampere': 1}),
                   UnitsContainer({'volt': 1, 'joule': -1, 'coulomb': 1}),
                   UnitsContainer({'tesla': 1, 'volt': -1, 'second': -1, 'meter': 2}))


def units_weight(units_container):
    return sum(abs(u) for u in units_container._d.values())


@lru_cache(maxsize=128)
def _simplify_units(units):
    units = infer_base_unit(units)
    weight = units_weight(units)
    found_simplification = True
    while weight > 1 and found_simplification:
        found_simplification = False
        for s in simplifications:
            test_units = units * s
            test_weight = units_weight(test_units)
            if test_weight < weight:
                units, weight, found_simplification = test_units, test_weight, True
            else:
                test_units = units / s
                test_weight = units_weight(test_units)
                if test_weight < weight:
                    units, weight, found_simplification = test_units, test_weight, True
    return units


def simplify_units(quantity):
    return _simplify_units(quantity.units)


def simplify(quantity):
    return quantity.to_compact(simplify_units(quantity))


Q.simplify = simplify

