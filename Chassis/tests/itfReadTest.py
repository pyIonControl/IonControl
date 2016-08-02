
from Chassis.itfParser import itfParser

sinPath ='../config/SineWave.itf'
testPath = '../config/voltage_test.itf'

itf = itfParser()
itf.eMapFilePath = '../config/thunderbird_map.txt'
itf.open(testPath)
for i in range(itf.getNumLines()):
    data= itf.eMapReadLine()
    print(data)

itf.close()

# Test the ability to read a specified line.
itf= None

itf = itfParser()
itf.eMapFilePath = '../config/thunderbird_map.txt'
itf.open(sinPath)
data = itf.eMapReadLine(0)
print(data)
data = itf.eMapReadLine(5)
print(data)
data = itf.eMapReadLine(0)
print(data)
itf.close()

# Test ReadLines
itf = None

itf = itfParser()
itf.eMapFilePath =  '../config/thunderbird_map.txt'
itf.open(testPath)
data = itf.eMapReadLines(2)
print(data)
itf.close()

# Test Read

itf = None
itf = itfParser()
itf.eMapFilePath =  '../config/thunderbird_map.txt'
itf.open(testPath)
data = itf.eMapRead()
print(data)
itf.close()

