# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from numpy import float64, append, ndarray, loadtxt
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
    def __init__(self, fileObj = None, filePath = None, **kwargs):
        ## This is the names of the columns for the table header of the
        #  itf file.

        self.tableHeader = []
        ## This is the file path to the electrode map file.
        #
        #  If this variable is populated then this file path
        #  will be used when a eMapReadLine() method is called.
        self._eMapFilePath = ''
        self.eMapDict = {}
        self.eMapFileCached = None

        ## This sepcifies the itf file column header.
        #
        #  The default is '{0:}' which means that the column headers
        #  will be represented by 0 through inf. Setting this to
        #  'e{0:02d}' means that the column headers will be represented
        #  by e00 through e99.
        self.eColHeader= kwargs.get('eColHeader', '{0:d}') #'e{0:02d}'
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
        if self.tableHeader[0][0] == 'e':
            self.eColHeader = 'e{0:02d}'

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
        line = self._readRawLine(lineNum)

        # strip whitespace on both sides of the line read
        dataList = line.strip().split('\t')

        # create a dictionary based on the data contained in the line
        dataDict = dict()
        for i, item in enumerate(dataList):
            if item == '':
                break
            dataDict[self.tableHeader[i]] = float64(item)
        return dataDict

    def _readRawLine(self, lineNum = None):
        # if the internal class data, such as tableHeader is not set,
        # then set the internal class data
        if self.tableHeader == []:
            self.fileObj.seek(0)
            self._parseHeader()
        
        # if lineNum has been passed, go to the begining of the data in
        # the file, and stop on the line requested and read the line.
        # Otherwise, read the next line.
        if lineNum >=0:
            self.fileObj.seek(self._dataOffset)
            for i in range(self.totalLines):
                line = self.fileObj.readline()
                if i==lineNum:
                    break
        else:
            line = self.fileObj.readline()

        return line

    def _getEmapData(self, eMapFilePath=None):
        if not eMapFilePath:
            eMapFilePath = self.eMapFilePath
        if self.eMapFileCached is not None \
            and self.eMapFileCached==eMapFilePath:
            return self.eMapDict
        else:
            from .eMapParser import eMapParser
            eMap = eMapParser()
            eMap.open(eMapFilePath)
            self.eMapDict = eMap.read()
            eMap.close()
            self.eMapFileCached = eMapFilePath
            return self.eMapDict

    ## This function will verify the contents of the itf file, and
    #  will generate an error if a electrode is in the itf file but
    #  not in the emap file.
    def _verifyItfContents(self, **kwargs):
        useENames = kwargs.get('useENames', False)
        elect = self.eMapDict['electrodes']
        if self.tableHeader == []:
            self._parseHeader()
        if useENames:
            pass
        else:
            #build a list of electrode strings from the eMap
            eMapElectList = []
            notFoundList = []
            for e in elect:
                eMapElectList.append(self.eColHeader.format(e))
            #search for electrodes in the itf that are not in eMap
            for itfElect in self.tableHeader:
                try:
                    eMapElectList.index(itfElect)
                except ValueError as e:
                    notFoundList.append(itfElect)
            if len(notFoundList) > 0:
                errString = 'The following electrodes were found in the' + \
                        ' itf file but not in the emap file: {0}'.format( \
                        notFoundList)
                raise itfParserError(1, errString)
                

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
    def eMapReadLine(self, lineNum = None, eMapFilePath=None, **kwargs):
        useENames = kwargs.get('useENames', False)
        eMapDict = self._getEmapData(eMapFilePath) 
        self._verifyItfContents(**kwargs)
        aoNums = eMapDict['aoNums']
        elect = eMapDict['electrodes']
        dNums = eMapDict['dsubNums']
        eNames = eMapDict['eNames']
        data = self.readline(lineNum)
        listData = []
        for i, j in enumerate(aoNums):
            try:
                eIndex = aoNums.index(j)
            except ValueError:
                print(i, j)
                raise
            if useENames:
                eString = eNames[eIndex]
            else:
                e = elect[eIndex] 
                eString = self.eColHeader.format(e)
            eData = data.get(eString, 0)
            # print "aoNum: {0} electrode: {1} data: {2}".format(i, eString,eData) 
            listData.append(eData)
        floatData  = float64(listData) 
        return floatData


    ## This function will read the number of lines specified by the
    #  numLines argument and return the data as a dictionary.
    #  @param self The object pointer.
    #  @param numLines The number of lines to pull from the file.
    def readlines(self, numLines):
        ## Get the tableHeader if it doesn't allready exist
        if self.tableHeader == []:
            self.fileObj.seek(0)
            self._parseHeader()

        ## Create the data dictionary
        dataDict = {}
        for item in self.tableHeader:
            dataDict[item] =  []

        ## Populate the data dictionary
        for i in range(numLines):
            line = self._readRawLine()
            dataList = line.strip().split('\t')
            for i, item in enumerate(dataList):
                if item == '':
                    break
                dataDict[self.tableHeader[i]].append([item])

        for key in dataDict:
            dataDict[key] = float64(dataDict[key])

        return dataDict
        '''
        for i in range(numLines):
            line = self.readline()
            if i > 0:
                for key in self.tableHeader:
                    data[key] = append(data[key], line[key])
            else:
                data = line
        return data
        '''

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
    def eMapReadLines(self, numLines, eMapFilePath = None, **kwargs):
        useENames = kwargs.get('useENames', False)
        eMapDict = self._getEmapData(eMapFilePath) 
        self._verifyItfContents(**kwargs)
        aoNums = eMapDict['aoNums']
        elect = eMapDict['electrodes']
        dNums = eMapDict['dsubNums']
        if useENames:
            eStrings = eMapDict['eNames']
        else:
            eStrings = []
            for e in elect:
                eStrings.append(self.eColHeader.format(e))
        data = self.readlines(numLines)
        defaultList = [0] * numLines
        for i, j in enumerate(aoNums):
            eIndex = aoNums.index(i)
            eString = eStrings[eIndex]
            eData = data.get(eString, 0)
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
        if isinstance(data, ndarray):
            for i in data:
                stringData.append(repr(i))
        elif isinstance(data, list):
            if isinstance(data[0], str):
                stringData = data
            elif isinstance(data[0], float) or isinstance(data[0], int):
                for i in data:
                    stringData.append(repr(i))
            else:
                raise TypeError('The datatype is not supported.')
        elif isinstance(data, dict):
            defaultValue = str(0)
            values = list(data.values())
            keys = list(data.keys())
            if self.tableHeader == []:
                self.tableHeader = keys
                self.tableHeader.sort()
            if isinstance(values[0], str):
                for item in self.tableHeader:
                    if item in data:
                        stringData.append(data[item])
                    else:
                        stringData.append(defaultValue)
            elif isinstance(values[0], float) or isinstance(values[0], int):
                for item in self.tableHeader:
                    if item in data:
                        stringData.append(str(data[item]))
                    else:
                        stringData.append(defaultValue)
            elif isinstance(values[0], ndarray):
                for item in self.tableHeader:
                    if item in data:
                        stringData.append(str(data[item][0]))
                    else:
                        stringData.append(defaultValue)
            elif isinstance(values[0], float64):
                for item in self.tableHeader:
                    if item in data:
                        stringData.append(str(data[item]))
                    else:
                        stringData.append(defaultValue)
            else:
                raise TypeError('The datatype is not supported.')
        else:
            raise TypeError('The datatype is not supported.')

        self._appendline(stringData)

    ## This function will append lines of data to the itf file.
    #  @param self The object reference.
    #  @param data This will take a dictionary of mulitple data types.  Supported types
    #  are numpy 1D float64, a list, and a dictionary.
    def appendlines(self, data):
        stringData = []
        if isinstance(data, dict):
            defaultValue = str(0)
            values = list(data.values())
            keys = list(data.keys())
            if self.tableHeader == []:
                self.tableHeader = keys
                self.tableHeader.sort()
            if isinstance(values[0], str):
                for item in self.tableHeader:
                    if item in data:
                        stringData.append(data[item])
                    else:
                        stringData.append(defaultValue)
                self._appendline(stringData)
            elif isinstance(values[0], float) or isinstance(values[0], int):
                for item in self.tableHeader:
                    if item in data:
                        stringData.append(str(data[item]))
                    else:
                        stringData.append(defaultValue)
                self._appendline(stringData)
            elif isinstance(values[0], ndarray) or isinstance(values[0], list):
                for i in range(len(values[0])):
                    for item in self.tableHeader:
                        if item in data:
                            stringData.append(str(data[item][i]))
                        else:
                            stringData.append(defaultValue)
                    self._appendline(stringData)
                    stringData = []
            else:
                raise TypeError('The data type is not supported.')


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
            #print 'file not empty'
            if self._dataOffset < 0:
                self.fileObj.seek(0)
                self._parseHeader()
            # Move to the end of the file to append.
            self.fileObj.seek(0, 2)

        line = sep.join(data) + '\n'
        self.fileObj.write(line)

    ## This funciotn will close the itf file.
    #  @param self The object reference.
    def close(self):
        self.tableHeader = []
        self.eMapFilePath = ''
        self.eColHeader= 'e{0:02d}'
        super(itfParser, self).close()

class itfParserError(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        string = '\n\tCode: {0} \n\tMessage: {1}'.format(self.code, self.msg)
        return string
'''
class optimizedItfParser(itfParser):
    def __init__(self):
        super(itfParser, self).__init__()
        self._allData = None

    def _readAll(self):
        if self._allData = None:
            self._parseHeaser()
            formats = ['f8'] * len(self.tableHeader)
            dtype = {'names':self.tableHeader, 'formats':formats}
            self._allData = loadtxt(self.fileObj, dtype=dtype)

    def readlines(self):
        pass
'''

if __name__ == '__main__':
    try:
        import numpy
        itf = itfParser()
        itf.open('test.itf')
        testData = {}
        for i in range(10):
            key = 'e%02d' % (i+1)
            testData[key] = numpy.random.rand(10)
        itf.appendlines(testData)
    finally:
        itf.close()
