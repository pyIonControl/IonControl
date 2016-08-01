# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from numpy import ndarray
## This class is the parent class of all file parsers.
class fileParser(object):
    ## This funciton is the constructor of the fileParser class.
    #
    #  It creates class data and opens the file if the filePath
    #  argument is provided.
    #  @param self The object pointer.
    #  @param fileObj The file object that gets returned by the file open()
    #  function.
    #  @param filePath A string that represents the location of the 
    #  file.
    def __init__(self, fileObj = None, filePath = None):
        ## The file object for the file.
        self.fileObj= None

        ## The comments within the file as a list.
        self.comments = []

        ## The meta data of the file as a list.
        #
        #  The dt variable is often within an itf file.  The value of this variable
        #  will be a value within meta.
        self.meta = dict()

        ## A boolean value that is true if the file is empty, and
        #  false otherwise.
        self.empty = True 

        self._dataOffset = -1 

        if not fileObj and not filePath:
            pass
        elif fileObj:
            self.fileObj= fileObj
        elif filePath:
            self.open(filePath)

        
        #file.__init__()

    ## This function opens the file in the filePath argument.
    #  @param self The object pointer.
    #  @param filePath This is the path to the file.
    def open(self, filePath):
        self._clearHeader()   #and clear the old header information
        self.fileObj= open(filePath, 'a+')
        firstChar = self.fileObj.read(1) #read the 1st character
        self.empty = not firstChar #set the empty variable.
        self.fileObj.seek(0) #go back to the begining of the file.

    ## clear old header information.
    # Called by open to reset the object state
    def _clearHeader(self):
        self.comments = list()
        self.meta = dict()
        self._dataOffset = -1
        self.empty = True

    def _parseHeader(self):
        found = False
        while not found:
            tempOffset = self.fileObj.tell()
            line = self.fileObj.readline()

            # find comments
            if line[0] == '#':
                strip = line.rstrip()
                self.comments.append(strip) 

            # find meta data
            elif line.find('=') >= 0:
                split = line.split('=')
                for i in range(len(split)):
                    split[i] = split[i].strip()
                self.meta.update({split[0]:split[1]})

            # empty lines of whitespace
            elif line.isspace():
                pass

            # find data
            else:
                found = True
                self._dataOffset = tempOffset
                self.fileObj.seek(tempOffset)

    ## This function will return the number of lines within the
    #  file.  This function is equivalent to reading the totalLines
    #  variable within the class.
    #  @param self The object pointer.
    def getNumLines(self):
        if self._dataOffset < 0:
            self._parseHeader()
        temp = self.fileObj.tell()
        self.fileObj.seek(self._dataOffset)
        for i, l in enumerate(self.fileObj):
            pass
        self.fileObj.seek(temp)
        return i+1

    ## @var totalLines
    #  This is the total number of lines of data within the
    #  itf file.
    totalLines = property(getNumLines,
               doc = """The total number of lines in the file.""")


    ## This function will close the file.
    #  @param self The object pointer.
    def close(self):
        self.fileObj.close()
        self.comments = []
        self.meta = dict()
        self.empty = True 
        self._dataOffset = -1 

## This is a class that creates a specific exception for the 
#  fileParser class.
#
#  Havinga a specific exception help when trying to explain
#  to the user why a certain function generated an error.
class fileParserError(Exception):
    ## This is the constructor for the fileParserError class.
    #  
    #  This function creates the msg class attribute.
    #  @param self The object pointer.
    #  @param msg The message to display to the user.
    def __init__(self, msg):
        ## The message to display to the user.
        self.msg = msg
    ## This function defines how the class operates when a
    #  the class is asked to represent itself as a string.
    #
    #  This function just returns the value of the msg class
    #  attribute.
    def __str__(self):
        return repr(self.msg)


