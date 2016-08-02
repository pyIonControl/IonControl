# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import math


def roundToNDigits(value, n):
    """round value to n significant digits
    """
    if value is None or math.isnan(value) or math.isinf(value) or value == 0:
        return value
    if not n:
        n = 0
    return round(value, -int(math.floor(math.log10(abs(value)))) + (n - 1))


def digitsToPrecision(value, n):
    """convert the number of significant digits into the precision (number of digits after the period"""
    if value is None or math.isnan(value) or math.isinf(value) or value == 0:
        return 0
    return max(0, -int(math.floor(math.log10(abs(value)))) + (n - 1))


def roundToStdDev(value, stddev, extradigits=0):
    """round value to the significant digits determined by the stddev
    and add extradigits nonsignificant digits
    """
    if value is None or math.isnan(value) or math.isinf(value) or value == 0:
        return value
    if not stddev:
        stddev = 0
    return roundToNDigits(value,
                          int(math.log10(math.ceil(abs(value) / stddev) - 0.5) + 2 + extradigits) if stddev > 0 else 3)


if __name__ == "__main__":
    print(roundToNDigits(-123.45, 2))
    print(roundToNDigits(12.45, 2))
    print(roundToNDigits(-1.45, 2))
    print(roundToNDigits(0.45, 2))
    print(roundToNDigits(0.045, 2))
    print(roundToNDigits(0.0045, 2))

    print(roundToStdDev(5.123445, 2))
    print(roundToStdDev(5.123445, 1))
    print(roundToStdDev(5.123445, 0.1))
    print(roundToStdDev(5.123445, 0.01))
    print(roundToStdDev(5.123445, 0.001))

    value = 500.123445
    print(roundToNDigits(value, 1))
    print(digitsToPrecision(value, 1))
    print(roundToNDigits(value, 2))
    print(digitsToPrecision(value, 2))
    print(roundToNDigits(value, 3))
    print(digitsToPrecision(value, 3))
    print(roundToNDigits(value, 4))
    print(digitsToPrecision(value, 4))
    print(roundToNDigits(value, 5))
    print(digitsToPrecision(value, 5))
    print(roundToNDigits(value, 6))
    print(digitsToPrecision(value, 6))

    print(roundToNDigits(None, 1))
    print(roundToNDigits(None, None))
    print(roundToNDigits(1, None))
