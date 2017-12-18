# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import lxml.etree as ElementTree
from modules.MagnitudeParser import parse


supportedTypes = { 'str': (lambda v: v, lambda s: stringToStringOrNone(s)),
                   'int': ( lambda v: repr(v), lambda s: int(s, 0) ),
                   'bool': ( lambda v: repr(v), lambda s: True if s in ['True', 'true'] else False),
                   'NoneType': (lambda v: repr(None), lambda s: None),
                   'float': (lambda v: repr(v), lambda s: float(s)),
                   'Magnitude': (lambda v: repr(v), lambda s: parse(s)) }

def typeName( obj ):
    tname = type(obj).__name__
    if tname=='instance':
        tname = obj.__class__.__name__
    return tname

def prettify(elem, commentchar=None):
    """Return a pretty-printed XML string for the Element.
    """
    text = ElementTree.tostring(elem, encoding='unicode', pretty_print=True)
    if not commentchar:
        return text
    return ''.join(['# <?xml version="1.0" ?>\n']+['# {0}\n'.format(line) for line in text.splitlines()])

def stringToStringOrNone(string):
    if string is None:
        return ""
    else:
        return None if string == "None" else string


def xmlEncodeDictionary( dictionary, element, tagName ):
    for name, attr in sorted(dictionary.items()):
        if typeName(attr) in supportedTypes:
            e = ElementTree.SubElement(element, tagName, attrib={'type': typeName(attr), 'name':name } )
            e.text = supportedTypes[typeName(attr)][0](attr)


def xmlEncodeAttributes( dictionary, element ):
    return xmlEncodeDictionary(dictionary, element, "attribute")


def xmlParseDictionary( element, tagName ):
    result = dict()
    for e in element.findall(tagName):
        parser = supportedTypes.get( e.attrib['type'], None )
        if parser:
            result[e.attrib['name']] = parser[1](e.text)
    return result

def xmlParseAttributes( element ):
    return xmlParseDictionary(element, "attribute")


