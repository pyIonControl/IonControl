# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
Open the default data directory
<DataDirectoryBase>\<project>\2013\01\37
missing directories below the project directory are created.
It is also used to generate file serials. For serial determination, the directory is read every time.

@author: plmaunz
"""
import datetime
import functools
import os.path
import re
from ProjectConfig.Project import getProject


class DataDirectoryException(Exception):
    pass


class DataDirectory:
    def path(self, current=None, extradir=''):
        """ Return a string path to data location for the given date.
        @type current: datetime.date
        @type extradir: str  
        """
        if not current:
            current = datetime.date.today()
        basedir = getProject().projectDir
        yeardir = os.path.join(basedir, str(current.year))
        monthdir = os.path.join(yeardir, "{0}_{1:02d}".format(current.year, current.month))
        daydir = os.path.join(monthdir, "{0}_{1:02d}_{2:02d}".format(current.year, current.month, current.day))
        fulldir = os.path.join(daydir, extradir)
        if not os.path.exists(basedir):
            raise DataDirectoryException("Data directory '{0}' does not exist.".format(basedir))
        if not os.path.exists(daydir):
            os.makedirs(daydir)
        if extradir and not os.path.exists(fulldir):
            os.makedirs(fulldir)
        return daydir if not extradir else fulldir
        
    def sequencefile(self,name,  current=None):
        """
        return the sequenced filename in the current data directory.
        _000 serial is inserted before the file extension or at the end of the name if the filename has no extension.
        The directory is reread every time.
        """
        if not current:
            current = datetime.date.today()
        extradir, leaf = os.path.split(name)
        directory = self.path(current, extradir=extradir)
        fileName, fileExtension = os.path.splitext(leaf)
        pattern = re.compile(re.escape(fileName)+"_(?P<num>\\d+)"+re.escape(fileExtension))
        maxNumber = 0
        for name in os.listdir(directory):
            m = pattern.match(name)
            if m is not None:
                maxNumber = max(int(m.group('num')), maxNumber)
        return os.path.join(directory, "{0}_{1:03d}{2}".format(fileName, maxNumber+1, fileExtension)), ( directory, "{0}_{1:03d}".format(fileName, maxNumber+1), fileExtension )
        
    def datafilelist(self, name, date):
        """ return a list of files in the results directory of date "date" order by serial number """
        directory = self.path(date)
        fileName, fileExtension = os.path.splitext(name)
        pattern = re.compile(re.escape(fileName)+"_(?P<num>\\d+)"+re.escape(fileExtension))
        fileList = list()
        numberList = list()
        for name in os.listdir(directory):
            m = pattern.match(name)
            if m is not None:
                fileList.append(name)
                numberList.append(int(m.group('num')))
        return list(map( functools.partial( os.path.join, directory), fileList )), numberList
         
        
if __name__ == "__main__":
    d = DataDirectory("HOA")    
    print(d.path())
    print(d.sequencefile("test.txt"))