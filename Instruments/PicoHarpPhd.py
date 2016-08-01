# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from ctypes import Structure, c_float, c_int, c_char, c_longlong, c_ulong, c_uint


displayCurves = 8
resolution = 4e-12
wraparound = 210698240
measureModeInteractive = 0
measureModeT2 = 2
measureModeT3 = 3

class ParamStructure(Structure):
    _fields_ = [
        ("start", c_float),
        ("step", c_float),
        ("end", c_float) ]

    def __str__(self):
        return "\n".join( [ name+" {0}".format(getattr(self, name)) for (name, _) in self._fields_ ] )
        
class CurveMapping(Structure):
    _fields_ = [
        ("mapTo", c_int),
        ("show", c_int) ]

    def __str__(self):
        return "\n".join( [ name+" {0}".format(getattr(self, name)) for (name, _) in self._fields_ ] )
        
class TextHeader(Structure):
    _fields_ = [
        ("ident", c_char * 16),
        ("formatVersion", c_char * 6),
        ("creatorName", c_char * 18),
        ("creatorVersion", c_char * 12),
        ("fileTime", c_char * 18),
        ("crlf", c_char * 2),
        ("comment", c_char * 256)]
        
    def __str__(self):
        return "\n".join( [ name+" {0}".format(getattr(self, name)) for (name, _) in self._fields_.remove(("crlf", c_char * 2)) ] )
                            
class BinaryHeader(Structure):
    _fields_ = [
        ("curves", c_int),
        ("bitsPerRecord", c_int),
        ("routingChannels", c_int),
        ("numberOfBoards", c_int),
        ("activeCurve", c_int),
        ("measMode", c_int),
        ("subMode", c_int),
        ("rangeNo", c_int),
        ("offset", c_int),
        ("tacq", c_int),
        ("stopAt", c_int),
        ("stopOnOvfl", c_int),
        ("restart", c_int),
        ("dispLinLog", c_int),
        ("dispTimeFrom", c_int),
        ("dispTimeTo", c_int),
        ("dispCountsFrom", c_int),
        ("dispCountsTo", c_int),
        ("dispCurves", CurveMapping * displayCurves ),
        ("params", ParamStructure * 3),
        ("repeatMode", c_int),
        ("repeatsPerCurve", c_int),
        ("repeatTime", c_int),
        ("repeatWaitTime", c_int),
        ("scriptName", c_char * 20) ]
        
    def __str__(self):
        return "\n".join( [ name+" {0}".format(getattr(self, name)) for (name, _) in self._fields_ ] )

class BoardHeader(Structure):
    _fields_ = [
        ("hardwareIdent", c_char * 16),
        ("hardwareVersion",  c_char * 8),
        ("hardwareSerial", c_int),
        ("syncDivider", c_int),
        ("cFDZeroCross0", c_int),
        ("cFDLevel0", c_int),
        ("cFDZeroCross1", c_int),
        ("cFDLevel1", c_int),
        ("resolution", c_float),
        ("routerModelCode", c_int),
        ("routerEnabled", c_int),
        ("rtChan1_InputType", c_int),
        ("rtChan1_InputLevel", c_int),
        ("rtChan1_InputEdge", c_int),
        ("rtChan1_CFDPresent", c_int),
        ("rtChan1_CFDLevel", c_int),
        ("rtChan1_CFDZeroCross", c_int),
        ("rtChan2_InputType", c_int),
        ("rtChan2_InputLevel", c_int),
        ("rtChan2_InputEdge", c_int),
        ("rtChan2_CFDPresent", c_int),
        ("rtChan2_CFDLevel", c_int),
        ("rtChan2_CFDZeroCross", c_int),
        ("rtChan3_InputType", c_int),
        ("rtChan3_InputLevel", c_int),
        ("rtChan3_InputEdge", c_int),
        ("rtChan3_CFDPresent", c_int),
        ("rtChan3_CFDLevel", c_int),
        ("rtChan3_CFDZeroCross", c_int),
        ("rtChan4_InputType", c_int),
        ("rtChan4_InputLevel", c_int),
        ("rtChan4_InputEdge", c_int),
        ("rtChan4_CFDPresent", c_int),
        ("rtChan4_CFDLevel", c_int),
        ("rtChan4_CFDZeroCross", c_int)]    

    def __str__(self):
        return "\n".join( [ name+" {0}".format(getattr(self, name)) for (name, _) in self._fields_ ] )
        
class CurveHeader(Structure):
    _pack_ = 4
    _fields_ = [
        ("CurveIndex", c_int),
        ("TimeOfRecording", c_ulong),
        ("HardwareIdent", c_char * 16),
        ("HardwareVersion", c_char * 8),
        ("HardwareSerial", c_int),
        ("SyncDivider", c_int),
        ("CFDZeroCross0", c_int),
        ("CFDLevel0", c_int),
        ("CFDZeroCross1", c_int),
        ("CFDLevel1", c_int),
        ("Offset", c_int),
        ("RoutingChannel", c_int),
        ("ExtDevices", c_int),
        ("MeasMode", c_int),
        ("SubMode", c_int),
        ("P1", c_float),
        ("P2", c_float),
        ("P3", c_float),
        ("RangeNo", c_int),
        ("Resolution", c_float),
        ("Channels", c_int),
        ("Tacq", c_int),
        ("StopAfter", c_int),
        ("StopReason", c_int),
        ("InpRate0", c_int),
        ("InpRate1", c_int),
        ("HistCountRate", c_int),
        ("IntegralCount", c_longlong),
        ("reserved", c_int),
        ("DataOffset", c_int),
        ("RouterModelCode", c_int),
        ("RouterEnabled", c_int),
        ("RtChan_InputType", c_int),
        ("RtChan_InputLevel", c_int),
        ("RtChan_InputEdge", c_int),
        ("RtChan_CFDPresent", c_int),
        ("RtChan_CFDLevel", c_int),
        ("RtChan_CFDZeroCross", c_int) ]

    def __str__(self):
        return "\n".join( [ name+" {0}".format(getattr(self, name)) for (name, _) in self._fields_ ] )

class TTTRHeader(Structure):
    _fields_ = [
        ("ExtDevices", c_int),
        ("Reserved1", c_int),
        ("Reserved2", c_int),
        ("CntRate0", c_int),
        ("CntRate1", c_int),
        ("StopAfter", c_int),
        ("StopReason", c_int),
        ("Records", c_int),
        ("ImgHdrSize", c_int)]
        
        
class PicoHarpPhd(object):
    def __init__(self, filename=None):
        self.textHeader = TextHeader()
        self.binaryHeader = BinaryHeader()
        self.boardHeader = BoardHeader()
        self.curveHeaderList = list()
        self.curveDataList = list()
        if filename:
            self.load(filename)
    
    def load(self, filename):
        with open(filename, 'rb') as f:
            f.readinto(self.textHeader)
            f.readinto(self.binaryHeader)
            f.readinto(self.boardHeader)
            self.curveHeadersList = list()
            self.curveDataList = list()
            for _ in range(self.binaryHeader.curves):
                curveHeader = CurveHeader()
                f.readinto(curveHeader)
                self.curveHeaderList.append( curveHeader )
            for curveHeader in self.curveHeaderList:
                channels = curveHeader.Channels
                curveData = ( c_uint  * channels )()
                f.readinto( curveData )
                self.curveDataList.append( list(curveData) )
                
    def pruned(self):
        '''
        bpt
        prune zero entries, convert to int, remove last bin
        '''
        curveList = []
        for q in self.curveDataList:
            curve = []
            for t in q:
                if t!=0:
                    curve.append(int(t))
            curve.pop()
            curveList.append(curve)
        return curveList
        
        
if __name__=="__main__":

    phd = PicoHarpPhd(r'C:\ex-control\data\ring_94\data\traces.phd')
    
    print(phd.binaryHeader.curves)
    # print phd.curveDataList
    print(phd.pruned())        
        
       

        
    