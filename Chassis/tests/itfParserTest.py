import os

import numpy

from Chassis.itfParser import itfParser

def deleteIfExists(filePath):
    directory = os.getcwd()
    for item in os.listdir(directory):
        if item == filepath:
            os.remove(filepath)
            break



filepath = 'example.itf'
deleteIfExists(filepath)
test = itfParser()
for j in range(9):
    test.open(filepath)
    for i in range(9):
        data = 'test{0}{1}'
        test.appendline([data.format(j, i), data.format(j, i+1)])
    test.close()

filepath = 'numpyExample.itf'
deleteIfExists(filepath)
test = itfParser()
data = numpy.linspace(1, 10, 10)
test.open(filepath)
for i in range(9):
    test.appendline(data)
test.close()

filepath = 'dictExample.itf'
deleteIfExists(filepath)
test = itfParser()
data = {'e1' : 1.0, 'e2' : 2.0}
test.open(filepath)
test.appendline(data)
test.close()
