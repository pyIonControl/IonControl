# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .fileParser import fileParser


## This class will parse the electrode mape file.
class eMapParser(fileParser):

    ## This function will read all of the data from the eMap
    #  file and return a list of electrodes, ao numbers, and
    #  dsub numbers.
    def read(self):
        electrodes = []
        aoNums = []
        dsubNums = []
        if self._dataOffset < 0:
            self._parseHeader()
        else:
            self.fileObj.seek(self._dataOffset)

        for i in range(self.totalLines):
            line = self.fileObj.readline()
            dataList = line.strip().split('\t')
            electrodes.append(dataList[0])
            aoNums.append(dataList[1])
            dsubNums.append(dataList[2])
        return electrodes, aoNums, dsubNums
