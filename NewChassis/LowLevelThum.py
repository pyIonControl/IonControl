# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ctypes
from os.path import dirname, abspath

dllDir = abspath(dirname(__file__))

ThumLib = ctypes.windll.LoadLibrary(dllDir + '\\THUM.dll')

#Create function names for all functions contained in the THUMB dll
Read = ThumLib.Read
GetTempUnit = ThumLib.GetTempUnit
SetTempUnit = ThumLib.SetTempUnit
GetTemp = ThumLib.GetTemp
GetRH = ThumLib.GetRH
GetDewPt = ThumLib.GetDewPt
Reset = ThumLib.Reset
SetDevID = ThumLib.SetDevID
GetDevID = ThumLib.GetDevID
ReadIRprox = ThumLib.ReadIRprox
GetIRprox = ThumLib.GetIRprox
ReadTempOnly = ThumLib.ReadTempOnly
GetTempOnly = ThumLib.GetTempOnly
ReadSwitch = ThumLib.ReadSwitch
GetSwitch = ThumLib.GetSwitch
ReadUltrasonic = ThumLib.ReadUltrasonic
GetUltrasonic = ThumLib.GetUltrasonic
ReadExternalTempOnly = ThumLib.ReadExternalTempOnly
GetExternalTempOnly = ThumLib.GetExternalTempOnly
ReadSwitch2 = ThumLib.ReadSwitch2
GetSwitch2 = ThumLib.GetSwitch2
ReadSwitch3 = ThumLib.ReadSwitch3
GetSwitch3 = ThumLib.GetSwitch3

#Define the input and output parameters of all functions in the THUMB dll
Read.restype = ctypes.c_long

GetTempUnit.restype = ctypes.c_long

SetTempUnit.argtypes = [ctypes.c_double]
SetTempUnit.restype = ctypes.c_long

GetTemp.restype = ctypes.c_double

GetRH.restype = ctypes.c_double

GetDewPt.restype = ctypes.c_double

Reset.restype = ctypes.c_long

SetDevID.argtypes = [ctypes.c_uint8]

GetDevID.restype = ctypes.c_uint8

ReadIRprox.restype = ctypes.c_long

GetIRprox.restype = ctypes.c_double

ReadTempOnly.restype = ctypes.c_long

GetTempOnly.restype = ctypes.c_double

ReadSwitch.restype = ctypes.c_long

GetSwitch.restype = ctypes.c_double

ReadUltrasonic.restype = ctypes.c_long

GetUltrasonic.restype = ctypes.c_double

ReadExternalTempOnly = ctypes.c_long

GetExternalTempOnly = ctypes.c_double

ReadSwitch2.restype = ctypes.c_long

GetSwitch2.restype = ctypes.c_double

ReadSwitch3.restype = ctypes.c_long

GetSwitch3.restype = ctypes.c_double
