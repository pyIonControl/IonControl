# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import collections

from numpy import float64, append

from .fileParser import fileParser


## This class will parse through an itf file.
class itfParser(fileParser):
    ## This function is the constructor of the itfParser class.
    #
    #  It initializes class attributes.
    #  @param self The object pointer.
    #  @param fileObj A file object pointer for a file that has already
    #  been opened.
    #  @param filePath A path to the itf file that hasn't already been
    #  opened.
    def __init__(self, fileObj = None, filePath = None):
        ## This is the names of the columns for the table header of the
        #  itf file.
        self.tableHeader = []
        ## This is the file patht to the electrode map file.
        #
        #  If this variable is populated then this file path
        #  will be used when a eMapReadLine() method is called.
        self.eMapFilePath = ''
        self.elect = []
        self.aoNums = []
        self.dNums = []
        self.eMapFileCached = None
        super(itfParser, self).__init__(fileObj, filePath)
        
    @property
    def eMapFilePath(self):
        return self._eMapFilePath
        
    @eMapFilePath.setter
    def eMapFilePath(self, path):
        self._eMapFilePath = path
        self.eMapFileCached = None

    def _parseHeader(self):
        super(itfParser, self)._parseHeader()
        while True:
            line = self.fileObj.readline()

            if line.isspace():
                pass
            else:
                strip = line.strip()
                self.tableHeader = strip.split('\t')
                self._dataOffset = self.fileObj.tell()
                break
            
    ## clear old header information.
    # Called by open to reset the object state
    def _clearHeader(self):
        super(itfParser, self)._clearHeader()
        self.tableHeader = list()  
        
    ## This function will read a line from the itf file and returns
    #  the data as a dictionary.
    #  @param self The object pointer.
    #  @param lineNum If this argument is provided then the line number
    #  refered to by this argument is returned.  Otherwise the next
    #  line is returned. (This argument is zero-based. Meaning that
    #  passing a value of zero will return the first line in the file.)
    def readline(self, lineNum = None):
        # if the internal class data, such as tableHeader is not set,
        # then set the internal class data
        if self.tableHeader == []:
            self.fileObj.seek(0)
            self._parseHeader()
        
        # if lineNum has been passed, go to the begining of the data in the file,
        # and stop on the line requested and read the line.  Otherwise, read
        # the next line.
        if lineNum and lineNum >=0:
            self.fileObj.seek(self._dataOffset)
            for i in range(self.totalLines):
                line = self.fileObj.readline()
                if i==lineNum:
                    break
        else:
            line = self.fileObj.readline()

        # strip whitespace on both sides of the line read
        dataList = line.strip().split('\t')

        # create a dictionary based on the data contained in the line
        dataDict = dict()
        for i, item in enumerate(dataList):
            if item == '':
                break
            if i<len(self.tableHeader):
                dataDict.update({self.tableHeader[i]:float64(item)})
        return dataDict

    def _checkForDuplicates(self, testlist ):
        return [x for x, y in list(collections.Counter(testlist).items()) if y > 1]   

    def _getEmapData(self, eMapFilePath=None):
        if not eMapFilePath:
            eMapFilePath = self.eMapFilePath
        if self.eMapFileCached is not None and self.eMapFileCached==eMapFilePath:
            return self.elect, self.aoNums, self.dNums
        from .eMapParser import eMapParser
        #print eMapFilePath
        eMap = eMapParser()
        eMap.open(eMapFilePath)
        self.elect, self.aoNums, self.dNums = eMap.read()
        #for i, d in enumerate(elect):
        #    elect[i]=int(d)
        for i, d in enumerate(self.aoNums):
            self.aoNums[i]=int(d)
        eMap.close()
        # we need to have the lists sorted by increasing aoNumber
        # we do not want to have to expect the map file is in this order
        zipped = sorted(zip(self.aoNums, self.elect, self.dNums))

        duplicates = self._checkForDuplicates(self.aoNums)
        if len(duplicates)>0:
            print("The following Analog Out Channels are assigned twice:", duplicates)
            
        
        self.aoNums, self.elect, self.dNums = list(zip(*zipped))
        self.eMapFileCached = eMapFilePath
        return self.elect, self.aoNums, self.dNums

    ## This function reads a line from the itf file and uses an 
    #  electrode map file to sort the data by the electrode order
    #  within the file.
    #
    #  This function returns a numpy float64 array, which is
    #  compatible with the array fromat accepted by the WaveformChassis
    #  class.
    #  @param self The object pointer.
    #  @param lineNum If this argument is provided then the line number
    #  refered to by this argument is returned.  Otherwise the next
    #  line is returned. (This argument is zero-based. Meaning that
    #  passing a value of zero will return the first line in the file.)
    #  @param eMapFilePath The file path to the eletrode map.
    def eMapReadLine(self, lineNum = None, eMapFilePath=None):
        elect, aoNums, dNums = self._getEmapData(eMapFilePath) 
        data = self.readline(lineNum)
        listData = []
        for i, j in enumerate(aoNums):
            try:
                eIndex = aoNums.index(j)
            except ValueError:
                print(i, j)
                raise
            e = elect[eIndex] 
            eString = e #'e{0:02d}'.format(e)
            eData = data.get(eString)
            # print "aoNum: {0} electrode: {1} data: {2}".format(i, eString,eData)
            listData.append(eData)
        floatData  = float64(listData) 
        return floatData


    ## This function will read the number of lines specified by the
    #  numLines argument and return the data as a dictionary.
    #  @param self The object pointer.
    #  @param numLines The number of lines to pull from the file.
    def readlines(self, numLines):
        for i in range(numLines):
            line = self.readline()
            if i > 0:
                for key in self.tableHeader:
                    data[key] = append(data[key], line[key])
            else:
                data = line
        return data

    ## This function reads lines from the itf file and uses an 
    #  electrode map file to sort the data by the electrode order
    #  within the file.
    #
    #  This function returns a numpy float64 array, which is
    #  compatible with the array fromat accepted by the WaveformChassis
    #  class.
    #  @param self The object pointer.
    #  @param numLines The number of lines to return from the itf file.
    #  @param eMapFilePath The file path to the eletrode map.
    def eMapReadLines(self, numLines, eMapFilePath = None):
        elect, aoNums, dNums = self._getEmapData(eMapFilePath) 
        data = self.readlines(numLines)
        for i, j in enumerate(aoNums):
            eIndex = aoNums.index(i)
            e = elect[eIndex]
            eString = e #'e{0:02d}'.format(e)
            eData = data.get(eString)
            if i>0:
                appendData = append(appendData, eData)
            else:
                appendData = eData
            #print "aoNum: {0} electrode: {1} data: {2}".format(i, eString,eData 
        return appendData
    
    ## This function will read all of the lines within the file and
    #  returns the data as a dictionary.
    #  @param self The object pointer.
    def read(self):
        if self._dataOffset < 0:
            self._parseHeader()
        else:
            self.fileObj.seek(self._dataOffset)
        return self.readlines(self.totalLines)
    
    ## This function reads all lines from the itf file and uses an 
    #  electrode map file to sort the data by the electrode order
    #  within the file.
    #
    #  This function returns a numpy float64 array, which is
    #  compatible with the array fromat accepted by the WaveformChassis
    #  class.
    #  @param self The object pointer.
    #  @param eMapFilePath The file path to the eletrode map.
    def eMapRead(self, eMapFilePath=None):
        numLines = self.getNumLines()
        data = self.eMapReadLines(numLines, eMapFilePath)
        return data

    ## This function will append a line of data to the itf file.
    #  @param self The object reference.
    #  @param data This will take mulitple data types.  Supported types
    #  are numpy 1D float64, a list, and a dictionary.
    def appendline(self, data):
        stringData = []
        if isinstance(data, numpy.ndarray):
            for i in data:
                stringData.append(repr(i))
        elif isinstance(data, list):
            if isinstance(data[0], str):
                stringData = data
            elif isinstance(data[0], float):
                for i in data:
                    stringData.append(repr(i))
        elif isinstance(data, dict):
            values = list(data.values())
            keys = list(data.keys())
            self.tableHeader = keys
            if isinstance(values[0], str):
                stringData = values
            elif isinstance(values[0], float):
                for i in values:
                    stringData.append(repr(i))

        self._appendline(stringData)

    def _appendline(self, data):
        # don't parse the header if the file is empty
        sep = '\t'
        if self.empty:
            if self.comments == []:
                ## The comments within the file as a list.
                self.comments = ['# A space for comments']
            if self.meta == {}:
                ## The meta data of the file as a dictionary.
                self.meta = {'dt':10}
            if self.tableHeader == []:
                for i, item in enumerate(data):
                    self.tableHeader.append('e{0}'.format(i+1))
            for comment in self.comments:
                self.fileObj.write(comment + '\n')
            for name, value in self.meta.items():
                self.fileObj.write(name + '='+ str(value) + '\n')
            for item in self.tableHeader:
                self.fileObj.write(item + sep)
            self.fileObj.write('\n')
            self._dataOffset = self.fileObj.tell()
            ## A boolean file that is true if the file is empty,
            #  and false otherwise.
            self.empty = False
        else:
            print('file not empty')
            if self._dataOffset < 0:
                self.fileObj.seek(0)
                self._parseHeader()

        line = sep.join(data) + '\n'
        self.fileObj.write(line)

    #def write(self, data):
        #pass


