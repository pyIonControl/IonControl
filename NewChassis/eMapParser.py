# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .fileParser import fileParser
import collections

## This class will parse the electrode mape file.
class eMapParser(fileParser):
    def __init__(self):
        super(eMapParser, self).__init__()
        self.eMapDict = {}

    def _checkForDuplicates(self, testlist ):
        dups = [x for x, y in list(collections.Counter(testlist).items())
                if y > 1]   
        return dups

    ## This function will read all of the data from the eMap
    #  file and return a list of electrodes, ao numbers, and
    #  dsub numbers.
    def read(self):
        electrodes = []
        aoNums = []
        dsubNums = []
        eNames = []
        if self._dataOffset < 0:
            self._parseHeader()
        else:
            self.fileObj.seek(self._dataOffset)

        for i in range(self.totalLines):
            line = self.fileObj.readline()
            dataList = line.strip().split('\t')
            electrodes.append(int(dataList[0]))
            aoNums.append(int(dataList[1]))
            dsubNums.append(int(dataList[2]))
            if len(dataList) >= 4:
                eNames.append(dataList[3].upper())

        # we need to have the lists sorted by increasing aoNumber
        # we do not want to have to expect the map file is in this order

        #zipped = zip(aoNums, electrodes, dsubNums, eNames)
        zipped = sorted(zip(aoNums, electrodes, dsubNums))
        #aoNums, electrodes, dsubNums, eNames= zip(*zipped)
        aoNums, electrodes, dsubNums = list(zip(*zipped))
        #check for duplicate ao Numbers
        duplicates = self._checkForDuplicates(aoNums)
        if len(duplicates)>0:
            print("The following Analog Out Channels are \
                    assigned twice:", duplicates)

        self.eMapDict = {'electrodes':electrodes, 'aoNums':aoNums,
                'dsubNums':dsubNums, 'eNames' : eNames}
        return self.eMapDict

    ## This function will close the eMap file and reset internal
    #  variables.
    def close(self):
        super(eMapParser, self).close()
        self.eMapDict = {}

if __name__ == '__main__':
    emap = eMapParser()
    emap.open('c:/Users/Public/Documents/experiments/test/config/VoltageControl/test_map2.txt')
    data = emap.read()
    emap.close()
