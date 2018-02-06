from lxml import etree

def isXmlFile(filename):
    with open(filename) as f:
        first_line = f.readline()
    return first_line.strip().startswith("<?xml")

