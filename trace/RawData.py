# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from array import array
import hashlib
import shutil

from modules import DataDirectory


class RawData(object):
    def __init__(self):
        self.open = False
        self.hash = hashlib.sha256()
        self.datafile = None
        self.datafilename = None
        self.filenametemplate = None
    
    def _add(self, data, datatype):
        if not self.datafile:
            self.datafilename, _ = DataDirectory.DataDirectory().sequencefile( "RawData.bin" )
            self.datafile = open( self.datafilename, 'wb' )
        data_array = array(datatype, data)
        self.hash.update(data_array)
        data_array.tofile(self.datafile)
    
    def addFloat(self, data):
        self._add(data, 'd')

    def addInt(self, data):
        self._add(data, 'L')
    
    def save(self,name=None):
        if name and not self.filenametemplate:   # we are currently on a temp file
            self.datafile.close()
            newdatafilename, _ = DataDirectory.DataDirectory().sequencefile( name )
            shutil.move( self.datafilename, newdatafilename )
            self.datafilename = newdatafilename
            self.datafile = open( self.datafilename, 'wb+' )
            self.filenametemplate = name
        return self.datafilename, self.hash.hexdigest()
        
    def delete(self):
        pass
    
    def hexdigest(self):
        return self.hash.hexdigest()
    
    def close(self):
        if self.datafile:
            self.datafile.close()
        return self.hash.hexdigest()
    
    
if __name__=="__main__":
    DataDirectory.DefaultProject = "testproject"
    rd = RawData()
    rd.addFloat( list(range(200)) )
    print(rd.save("Peter.txt"))
    print(rd.close())
    
    filename, components = DataDirectory.DataDirectory().sequencefile( "TestTrace.txt" )    
    
    from trace import TraceCollection
    tr = TraceCollection.TraceCollection()
    tr.x = list(range(200))
    tr.y = list(range(200))
    tr.rawdata = RawData()
    tr.rawdata.addInt( list(range(200)) )
    tr.saveTrace(filename)
    
    