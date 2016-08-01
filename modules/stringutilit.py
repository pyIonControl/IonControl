## *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


def commentarize(text):
    return "# "+"\n# ".join(text.splitlines())


def stringToBool(s):
    return False if s in ['0', 'False', 'None'] else bool(s)


def ensureAsciiBytes(strOrbytes):
    return strOrbytes if type(strOrbytes) == bytes else strOrbytes.encode('ascii')


def ensureStrFromAscii(strOrbytes):
    return strOrbytes if type(strOrbytes) == str else strOrbytes.decode('ascii')
