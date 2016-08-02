# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .niSyncConfig import lib_directory, lib_name
from .niSyncTypes import *
import ctypes
import sys

#Load the niSync dll into SyncLib
if sys.platform.startswith('win'):
    SyncLib=ctypes.windll.LoadLibrary(lib_directory + "\\" + lib_name)
elif sys.platform.startswith('cygwin'):
    print(lib_directory + lib_name)
    SyncLib=ctypes.cdll.LoadLibrary(lib_directory + lib_name)

#Create function name for all functions contained in the niSync dll
#The functions are in alphabetical order
CalAdjustClk10PhaseVoltage = SyncLib.niSync_CalAdjustClk10PhaseVoltage
CalAdjustDDSStartPulsePhaseVoltage = SyncLib.niSync_CalAdjustDDSStartPulsePhaseVoltage
CalAdjustOscillatorVoltage = SyncLib.niSync_CalAdjustOscillatorVoltage
CalGetClk10PhaseVoltage = SyncLib.niSync_CalGetClk10PhaseVoltage
CalGetDDSStartPulsePhaseVoltage = SyncLib.niSync_CalGetDDSStartPulsePhaseVoltage
CalGetOscillatorVoltage = SyncLib.niSync_CalGetOscillatorVoltage
ChangeExtCalPassword = SyncLib.niSync_ChangeExtCalPassword
ClearClock = SyncLib.niSync_ClearClock
ClearFutureTimeEvents = SyncLib.niSync_ClearFutureTimeEvents
close = SyncLib.niSync_close
CloseExtCal = SyncLib.niSync_CloseExtCal
ConfigureFPGA = SyncLib.niSync_ConfigureFPGA
ConnectClkTerminals = SyncLib.niSync_ConnectClkTerminals
ConnectSWTrigToTerminal = SyncLib.niSync_ConnectSWTrigToTerminal 
ConnectTrigTerminals = SyncLib.niSync_ConnectTrigTerminals
CreateClock = SyncLib.niSync_CreateClock
CreateFutureTimeEvent = SyncLib.niSync_CreateFutureTimeEvent
DisableGPSTimestamping = SyncLib.niSync_DisableGPSTimestamping
DisableIRIGTimestamping = SyncLib.niSync_DisableIRIGTimestamping
DisableTimeStampTrigger = SyncLib.niSync_DisableTimeStampTrigger
DisconnectClkTerminals = SyncLib.niSync_DisconnectClkTerminals
DisconnectSWTrigFromTerminal = SyncLib.niSync_DisconnectSWTrigFromTerminal
DisconnectTrigTerminals = SyncLib.niSync_DisconnectTrigTerminals
EnableGPSTimestamping = SyncLib.niSync_EnableGPSTimestamping
EnableIRIGTimestamping = SyncLib.niSync_EnableIRIGTimestamping
EnableTimeStampTrigger = SyncLib.niSync_EnableTimeStampTrigger
EnableTimeStampTriggerWithDecimation = SyncLib.niSync_EnableTimeStampTriggerWithDecimation
error_message = SyncLib.niSync_error_message
GetAttributeViBoolean = SyncLib.niSync_GetAttributeViBoolean
GetAttributeViInt32 = SyncLib.niSync_GetAttributeViInt32
GetAttributeViReal64 = SyncLib.niSync_GetAttributeViReal64
GetAttributeViString = SyncLib.niSync_GetAttributeViString
GetExtCalLastDateAndTime = SyncLib.niSync_GetExtCalLastDateAndTime
GetExtCalLastTemp = SyncLib.niSync_GetExtCalLastTemp
GetExtCalRecommendedInterval = SyncLib.niSync_GetExtCalRecommendedInterval
GetLocation = SyncLib.niSync_GetLocation
GetTime = SyncLib.niSync_GetTime
GetVelocity = SyncLib.niSync_GetVelocity
init = SyncLib.niSync_init
InitExtCal = SyncLib.niSync_InitExtCal
MeasureFrequency = SyncLib.niSync_MeasureFrequency
ReadCurrentTemperature = SyncLib.niSync_ReadCurrentTemperature
ReadLastGPSTimestamp = SyncLib.niSync_ReadLastGPSTimestamp
ReadLastIRIGTimestamp = SyncLib.niSync_ReadLastIRIGTimestamp
ReadMultipleTriggerTimeStamp = SyncLib.niSync_ReadMultipleTriggerTimeStamp
ReadTriggerTimeStamp = SyncLib.niSync_ReadTriggerTimeStamp
reset = SyncLib.niSync_reset
ResetFrequency = SyncLib.niSync_ResetFrequency
revision_query = SyncLib.niSync_revision_query
self_test = SyncLib.niSync_self_test
SendSoftwareTrigger = SyncLib.niSync_SendSoftwareTrigger
SetAttributeViBoolean = SyncLib.niSync_SetAttributeViBoolean
SetAttributeViInt32 = SyncLib.niSync_SetAttributeViInt32
SetAttributeViReal64 = SyncLib.niSync_SetAttributeViReal64
SetAttributeViString = SyncLib.niSync_SetAttributeViString
SetTime = SyncLib.niSync_SetTime
SetTimeReference1588OrdinaryClock = SyncLib.niSync_SetTimeReference1588OrdinaryClock
SetTimeReferenceFreeRunning = SyncLib.niSync_SetTimeReferenceFreeRunning
SetTimeReferenceGPS = SyncLib.niSync_SetTimeReferenceGPS
SetTimeReferenceIRIG = SyncLib.niSync_SetTimeReferenceIRIG
SetTimeReferencePPS = SyncLib.niSync_SetTimeReferencePPS
Start1588 = SyncLib.niSync_Start1588
Stop1588 = SyncLib.niSync_Stop1588

#Define the input and output parameters of all functions in the niSync dll
CalAdjustClk10PhaseVoltage.argtypes = [ViSession, ViReal64, ViReal64_P]
CalAdjustClk10PhaseVoltage.restype = ViStatus

CalAdjustDDSStartPulsePhaseVoltage.argtypes = [ViSession, ViReal64, ViReal64_P]
CalAdjustDDSStartPulsePhaseVoltage.restype = ViStatus

CalAdjustOscillatorVoltage.argtypes = [ViSession, ViReal64, ViReal64_P]
CalAdjustOscillatorVoltage.restype = ViStatus

CalGetClk10PhaseVoltage.argtypes = [ViSession, ViReal64_P]
CalGetClk10PhaseVoltage.restype = ViStatus

CalGetDDSStartPulsePhaseVoltage.argtypes = [ViSession, ViReal64_P]
CalGetDDSStartPulsePhaseVoltage.restype = ViStatus

CalGetOscillatorVoltage.argtypes = [ViSession, ViReal64_P]
CalGetOscillatorVoltage.restype = ViStatus

ChangeExtCalPassword.argtypes = [ViSession, ViConstString, ViConstString]
ChangeExtCalPassword.restype = ViStatus

ClearClock.argtypes = [ViSession, ViConstString]
ClearClock.restype = ViStatus

ClearFutureTimeEvents.argtypes = [ViSession, ViConstString]
ClearFutureTimeEvents.restype = ViStatus

close.argtypes = [ViSession]
close.restype = ViStatus

CloseExtCal.argtypes = [ViSession, ViInt32]
CloseExtCal.restype = ViStatus

ConfigureFPGA.argtypes = [ViSession, ViConstString]
ConfigureFPGA.restype = ViStatus

ConnectClkTerminals.argtypes = [ViSession, ViConstString, ViConstString]
ConnectClkTerminals.restype = ViStatus

ConnectSWTrigToTerminal.argtypes = [ViSession, ViConstString, ViConstString, ViConstString, ViInt32, ViInt32, ViReal64]
ConnectSWTrigToTerminal.restype = ViStatus

ConnectTrigTerminals.argtype = [ViSession, ViConstString, ViConstString, ViConstString, ViInt32, ViInt32]
ConnectTrigTerminals.restype = ViStatus

CreateClock.argtypes = [ViSession, ViConstString, ViUInt32, ViUInt32, ViUInt32, ViUInt32, ViUInt16, ViUInt32, ViUInt32, ViUInt16]
CreateClock.restype = ViStatus

CreateFutureTimeEvent.argtypes = [ViSession, ViConstString, ViInt32, ViUInt32, ViUInt32, ViUInt16]
CreateFutureTimeEvent.restype = ViStatus

DisableGPSTimestamping.argtypes = [ViSession]
DisableGPSTimestamping.restype = ViStatus

DisableIRIGTimestamping.argtype = [ViSession, ViInt32, ViConstString]
DisableIRIGTimestamping.restype = ViStatus

DisableTimeStampTrigger.argtype = [ViSession, ViConstString]
DisableTimeStampTrigger.restype = ViStatus

DisconnectClkTerminals.argtype = [ViSession, ViConstString, ViConstString]
DisconnectClkTerminals.restype = ViStatus

DisconnectSWTrigFromTerminal.argtype = [ViSession, ViConstString, ViConstString]
DisconnectSWTrigFromTerminal.restype = ViStatus

DisconnectTrigTerminals.argtype = [ViSession, ViConstString, ViConstString]
DisconnectTrigTerminals.restype = ViStatus

EnableGPSTimestamping.argtype = [ViSession]
EnableGPSTimestamping.restype = ViStatus

EnableIRIGTimestamping.argtype = [ViSession, ViInt32, ViConstString]
EnableIRIGTimestamping.restype = ViStatus

EnableTimeStampTrigger.argtype = [ViSession, ViConstString, ViInt32]
EnableTimeStampTrigger.restype = ViStatus

EnableTimeStampTriggerWithDecimation.argtype = [ViSession, ViConstString, ViInt32, ViUInt32]
EnableTimeStampTriggerWithDecimation.restype = ViStatus

error_message.argtype = [ViSession, ViStatus, ViString]
error_message.restype = ViStatus

GetAttributeViBoolean.argtype = [ViSession, ViConstString, ViAttr, ViBoolean_P]
GetAttributeViBoolean.restype = ViStatus

GetAttributeViInt32.argtype = [ViSession, ViConstString, ViAttr, ViInt32_P]
GetAttributeViInt32.restype = ViStatus

GetAttributeViReal64.argtype = [ViSession, ViConstString, ViAttr, ViReal64_P]
GetAttributeViReal64.restype = ViStatus

GetAttributeViString.argtype = [ViSession, ViConstString, ViAttr, ViString]
GetAttributeViString.restype = ViStatus

GetExtCalLastDateAndTime.argtype = [ViSession, ViInt32_P, ViInt32_P, ViInt32_P, ViInt32_P, ViInt32_P]
GetExtCalLastDateAndTime.restype = ViStatus

GetExtCalLastTemp.argtype = [ViSession, ViReal64_P]
GetExtCalLastTemp.restype = ViStatus

GetExtCalRecommendedInterval.argtype = [ViSession, ViInt32_P]
GetExtCalRecommendedInterval.restype = ViStatus

GetLocation.argtype = [ViSession, ViReal64_P, ViReal64_P, ViReal64_P]
GetLocation.restype = ViStatus

GetTime.argtype = [ViSession, ViUInt32_P, ViUInt32_P, ViUInt16_P]
GetTime.restype = ViStatus

GetVelocity.argtype = [ViSession, ViReal64, ViReal64, ViReal64]
GetVelocity.restype = ViStatus

init.argtypes = [ViRsrc, ViBoolean, ViBoolean, ViSession]
init.restype = ViStatus

InitExtCal.argtype = [ViRsrc, ViConstString, ViSession]
InitExtCal.restype = ViStatus

MeasureFrequency.argtype = [ViSession, ViConstString, ViReal64, ViReal64_P, ViReal64_P]
MeasureFrequency.restype = ViStatus

ReadCurrentTemperature.argtype = [ViSession, ViReal64_P]
ReadCurrentTemperature.restype = ViStatus

ReadLastGPSTimestamp.argtype = [ViSession, ViUInt32_P, ViUInt32_P, ViUInt16_P, ViUInt32_P, ViUInt32_P, ViUInt16_P]
ReadLastGPSTimestamp.restype = ViStatus

ReadLastIRIGTimestamp.argtype = [ViSession, ViConstString, ViUInt32_P, ViUInt32_P, ViUInt16_P, ViUInt32_P, ViUInt32_P, ViUInt16_P]
ReadLastIRIGTimestamp.restype = ViStatus

ReadMultipleTriggerTimeStamp.argtype = [ViSession, ViConstString, ViUInt32, ViReal64, ViUInt32_P, ViUInt32_P, ViUInt16_P, ViInt32_P, ViUInt32_P]
ReadMultipleTriggerTimeStamp.restype = ViStatus

ReadTriggerTimeStamp.argtype = [ViSession, ViConstString, ViReal64, ViUInt32_P, ViUInt32_P, ViUInt16_P, ViInt32_P]
ReadTriggerTimeStamp.restryp = ViStatus

reset.argtype = [ViSession]
reset.restype = ViStatus

ResetFrequency.argtype = [ViSession]
ResetFrequency.restype = ViStatus

revision_query.argtype = [ViSession, ViString, ViString]
revision_query.restype = ViStatus

self_test.argtype = [ViSession, ViInt16_P, ViString]
self_test.restype = ViStatus

SendSoftwareTrigger.argtype = [ViSession, ViConstString]
SendSoftwareTrigger.restype = ViStatus

SetAttributeViBoolean.argtype = [ViSession, ViConstString, ViAttr, ViBoolean]
SetAttributeViBoolean.restype = ViStatus

SetAttributeViInt32.argtype = [ViSession, ViConstString, ViAttr, ViInt32]
SetAttributeViInt32.restype = ViStatus

SetAttributeViReal64.argtype = [ViSession, ViConstString, ViAttr, ViReal64]
SetAttributeViReal64.restype = ViStatus

SetAttributeViString.argtype = [ViSession, ViConstString, ViAttr, ViConstString]
SetAttributeViString.restype = ViStatus

SetTime.argtype = [ViSession, ViInt32, ViUInt32, ViUInt32, ViUInt16]
SetTime.restype = ViStatus

SetTimeReference1588OrdinaryClock.argtype = [ViSession]
SetTimeReference1588OrdinaryClock.restype = ViStatus

SetTimeReferenceFreeRunning.argtype = [ViSession]
SetTimeReferenceFreeRunning.restype = ViStatus

SetTimeReferenceGPS.argtype = [ViSession]
SetTimeReferenceGPS.restype = ViStatus

SetTimeReferenceIRIG.argtype = [ViSession, ViInt32, ViConstString]
SetTimeReferenceIRIG.restpe = ViStatus

SetTimeReferencePPS.argtype = [ViSession, ViConstString, ViBoolean, ViUInt32, ViUInt32, ViUInt16]
SetTimeReferencePPS.restype = ViStatus

Start1588.argtype = [ViSession]
Start1588.restype = ViStatus

Stop1588.argtype = [ViSession]
Stop1588.restype = ViStatus

#This is example code that should be removed later.
Session = 0
Session = c_void_p(Session)
status = init("Dev7", 0, 0, Session)

