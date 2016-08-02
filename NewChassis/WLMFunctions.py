# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import ctypes
from os.path import dirname, abspath

#dllDir = abspath(dirname(__file__))
#All applicaitons must reference the same dll, which is installed
#in the c:\Windows\system32 directory for 32-bit systems.
#this may be different for 64-bit systems.
dllDir = 'c:\\Windows\\System32\\'
WlmLib = ctypes.windll.LoadLibrary(dllDir + '\\wlmData.dll')

## Functions for general usage
Instantiate = WlmLib.Instantiate
#CallbackProc = WlmLib.CallbackProc
#CallbackProcEx = WlmLib.CallbackProcEx
WaitForWLMEvent = WlmLib.WaitForWLMEvent
WaitForWLMEventEx = WlmLib.WaitForWLMEventEx
ControlWLM = WlmLib.ControlWLM
ControlWLMEx = WlmLib.ControlWLMEx
SetMeasurementDelayMethod = WlmLib.SetMeasurementDelayMethod
SetWLMPriority = WlmLib.SetWLMPriority
PresetWLMIndex = WlmLib.PresetWLMIndex
GetWLMVersion = WlmLib.GetWLMVersion
GetWLMIndex = WlmLib.GetWLMIndex
GetWLMCount = WlmLib.GetWLMCount

## General Get & Set Functions
GetWavelength = WlmLib.GetWavelength
GetWavelength2 = WlmLib.GetWavelength2
GetWavelengthNum = WlmLib.GetWavelengthNum
GetCalWavelength = WlmLib.GetCalWavelength
GetFrequency = WlmLib.GetFrequency
GetFrequency2 = WlmLib.GetFrequency2
GetFrequencyNum = WlmLib.GetFrequencyNum
GetAnalogIn = WlmLib.GetAnalogIn
GetTemperature = WlmLib.GetTemperature
SetTemperature = WlmLib.SetTemperature
GetPressure = WlmLib.GetPressure
SetPressure = WlmLib.SetPressure
GetExternalInput = WlmLib.GetExternalInput
SetExternalInput = WlmLib.SetExternalInput

GetExposure = WlmLib.GetExposure
SetExposure = WlmLib.SetExposure
GetExposure2 = WlmLib.GetExposure2
SetExposure2 = WlmLib.SetExposure2
GetExposureNum = WlmLib.GetExposureNum
SetExposureNum = WlmLib.SetExposureNum
GetExposureMode = WlmLib.GetExposureMode
SetExposureMode = WlmLib.SetExposureMode
GetExposureModeNum = WlmLib.GetExposureModeNum
SetExposureModeNum = WlmLib.SetExposureModeNum
GetExposureRange = WlmLib.GetExposureRange

GetResultMode = WlmLib.GetResultMode
SetResultMode = WlmLib.SetResultMode
GetRange = WlmLib.GetRange
SetRange = WlmLib.SetRange
GetPulseMode = WlmLib.GetPulseMode
SetPulseMode = WlmLib.SetPulseMode
GetWideMode = WlmLib.GetWideMode
SetWideMode = WlmLib.SetWideMode

GetDisplayMode = WlmLib.GetDisplayMode
SetDisplayMode = WlmLib.SetDisplayMode
GetFastMode = WlmLib.GetFastMode
SetFastMode = WlmLib.SetFastMode

GetSwitcherMode = WlmLib.GetSwitcherMode
SetSwitcherMode = WlmLib.SetSwitcherMode
GetSwitcherChannel = WlmLib.GetSwitcherChannel
SetSwitcherChannel = WlmLib.SetSwitcherChannel
GetSwitcherSignalStates = WlmLib.GetSwitcherSignalStates
SetSwitcherSignalStates = WlmLib.SetSwitcherSignalStates
SetSwitcherSignal = WlmLib.SetSwitcherSignal

GetAutoCalMode = WlmLib.GetAutoCalMode
SetAutoCalMode = WlmLib.SetAutoCalMode
GetAutoCalSetting = WlmLib.GetAutoCalSetting
SetAutoCalSetting = WlmLib.SetAutoCalSetting

GetActiveChannel = WlmLib.GetActiveChannel
SetActiveChannel = WlmLib.SetActiveChannel
GetChannelsCount = WlmLib.GetChannelsCount

GetOperationState = WlmLib.GetOperationState
Operation = WlmLib.Operation
SetOperationFile = WlmLib.SetOperationFile
Calibration = WlmLib.Calibration
RaiseMeasurementEvent = WlmLib.RaiseMeasurementEvent
TriggerMeasurement = WlmLib.TriggerMeasurement
GetInterval = WlmLib.GetInterval
SetInterval = WlmLib.SetInterval
GetIntervalMode = WlmLib.GetIntervalMode
SetIntervalMode = WlmLib.SetIntervalMode
GetBackground = WlmLib.GetBackground
SetBackground = WlmLib.SetBackground

GetLinkState = WlmLib.GetLinkState
SetLinkState = WlmLib.SetLinkState
LinkSettingsDlg = WlmLib.LinkSettingsDlg

GetPatternItemSize = WlmLib.GetPatternItemSize
GetPatternItemCount = WlmLib.GetPatternItemCount
GetPattern = WlmLib.GetPattern
GetPatternNum = WlmLib.GetPatternNum
GetPatternData = WlmLib.GetPatternData
GetPatternDataNum = WlmLib.GetPatternDataNum
SetPattern = WlmLib.SetPattern
SetPatternData = WlmLib.SetPatternData

GetAnalysisMode = WlmLib.GetAnalysisMode
SetAnalysisMode = WlmLib.SetAnalysisMode
GetAnalysisItemSize = WlmLib.GetAnalysisItemSize
GetAnalysisItemCount = WlmLib.GetAnalysisItemCount
GetAnalysis = WlmLib.GetAnalysis
GetAnalysisData = WlmLib.GetAnalysisData
SetAnalysis = WlmLib.SetAnalysis

GetLinewidthMode = WlmLib.GetLinewidthMode
SetLinewidthMode = WlmLib.SetLinewidthMode
GetLinewidth = WlmLib.GetLinewidth

GetDistanceMode = WlmLib.GetDistanceMode
SetDistanceMode = WlmLib.SetDistanceMode
GetDistance = WlmLib.GetDistance

GetMinPeak = WlmLib.GetMinPeak
GetMinPeak2 = WlmLib.GetMinPeak2
GetMaxPeak = WlmLib.GetMaxPeak
GetMaxPeak2 = WlmLib.GetMaxPeak2
GetAvgPeak = WlmLib.GetAvgPeak
GetAvgPeak2 = WlmLib.GetAvgPeak2
SetAvgPeak = WlmLib.SetAvgPeak

GetAmplitudeNum = WlmLib.GetAmplitudeNum
GetIntensityNum = WlmLib.GetIntensityNum
GetPowerNum = WlmLib.GetPowerNum

GetDelay = WlmLib.GetDelay
SetDelay = WlmLib.SetDelay
GetShift = WlmLib.GetShift
SetShift = WlmLib.SetShift
GetShift2 = WlmLib.GetShift2
SetShift2 = WlmLib.SetShift2

#Define input and output parameters for all functions
# Functions for general usage
Instantiate.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long, ctypes.c_long]
Instantiate.restype = ctypes.c_long

#CallbackProc.argtypes = [ctypes.c_long, ctypes.c_long,
#        ctypes.c_double]
#
#CallbackProcEx.argtypes = [ctypes.c_long, ctypes.c_long,
#        ctypes.c_long, ctypes.c_double, ctypes.c_long]

WaitForWLMEvent.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_double]
WaitForWLMEvent.restype = ctypes.c_long

WaitForWLMEventEx.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long, ctypes.c_double, ctypes.c_long]
WaitForWLMEventEx.restype = ctypes.c_long

ControlWLM.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long]
ControlWLM.restype = ctypes.c_long

ControlWLMEx.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long, ctypes.c_long, ctypes.c_long]
ControlWLMEx.restype = ctypes.c_long

SetMeasurementDelayMethod.argtypes = [ctypes.c_long, ctypes.c_long]
SetMeasurementDelayMethod.restype = ctypes.c_long

SetWLMPriority.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long]
SetWLMPriority.restypes = ctypes.c_long

PresetWLMIndex.argtypes = [ctypes.c_long]
PresetWLMIndex.restype = ctypes.c_long

GetWLMVersion.argtypes = [ctypes.c_long]
GetWLMVersion.restype = ctypes.c_long

GetWLMIndex.argtypes = [ctypes.c_long]
GetWLMIndex.restype = ctypes.c_long

GetWLMCount.argtypes = [ctypes.c_long]
GetWLMCount.restype = ctypes.c_long

GetWavelength.argtypes = [ctypes.c_double]
GetWavelength.restype = ctypes.c_double

GetWavelength2.argtypes = [ctypes.c_double]
GetWavelength2.restype = ctypes.c_double

GetWavelengthNum.argtypes = [ctypes.c_long, ctypes.c_double]
GetWavelengthNum.restype = ctypes.c_double

GetCalWavelength.argtypes = [ctypes.c_long, ctypes.c_double]
GetCalWavelength.restype = ctypes.c_double

GetFrequency.argtypes = [ctypes.c_double]
GetFrequency.restype = ctypes.c_double

GetFrequency2.argtypes = [ctypes.c_double]
GetFrequency2.restype = ctypes.c_double

GetFrequencyNum.argtypes = [ctypes.c_long, ctypes.c_double]
GetFrequencyNum.restype = ctypes.c_double

GetAnalogIn.argtypes = [ctypes.c_double]
GetAnalogIn.restype = ctypes.c_double

GetTemperature.argtypes = [ctypes.c_double]
GetTemperature.restype = ctypes.c_double

SetTemperature.argtypes = [ctypes.c_double]
SetTemperature.restype = ctypes.c_long

GetPressure.argtypes = [ctypes.c_double]
GetPressure.restypes = ctypes.c_double

SetPressure.argtypes = [ctypes.c_long, ctypes.c_double]
SetPressure.restypes = ctypes.c_long

GetExternalInput.argtypes = [ctypes.c_long, ctypes.c_double]
GetExternalInput.restype = ctypes.c_double

SetExternalInput.argtypes = [ctypes.c_long, ctypes.c_double]
SetExternalInput.restype = ctypes.c_long

GetExposure.argtypes = [ctypes.c_ushort]
GetExposure.restype = ctypes.c_ushort

SetExposure.argtypes = [ctypes.c_ushort]
SetExposure.restype = ctypes.c_long

GetExposure2.argtypes = [ctypes.c_ushort]
GetExposure2.restype = ctypes.c_ushort

SetExposure2.argtypes = [ctypes.c_ushort]
SetExposure2.restype = ctypes.c_long

GetExposureNum.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_ushort]
GetExposureNum.restype = ctypes.c_long

SetExposure.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_ushort]
SetExposure.restype = ctypes.c_long

GetExposureModeNum.argtypes = [ctypes.c_long, ctypes.c_bool]
GetExposureModeNum.restype = ctypes.c_long

SetExposureModeNum.argtypes = [ctypes.c_long, ctypes.c_bool]
SetExposureModeNum.restype = ctypes.c_long

GetExposureRange.argtypes = [ctypes.c_long]
GetExposureRange.restype = ctypes.c_long

GetResultMode.argtypes = [ctypes.c_ushort]
GetResultMode.restype = ctypes.c_ushort

SetResultMode.argtypes = [ctypes.c_ushort]
SetResultMode.restype = ctypes.c_long

GetRange.argtypes = [ctypes.c_ushort]
GetRange.restype = ctypes.c_ushort

SetRange.argtypes = [ctypes.c_ushort]
SetRange.restype = ctypes.c_long

GetPulseMode.argtypes = [ctypes.c_ushort]
GetPulseMode.restype = ctypes.c_ushort

SetPulseMode.argtypes = [ctypes.c_ushort]
SetPulseMode.restype = ctypes.c_long

GetWideMode.argtpes = [ctypes.c_ushort]
GetWideMode.restype = ctypes.c_ushort

SetWideMode.argtypes = [ctypes.c_ushort]
SetWideMode.restype = ctypes.c_long

GetDisplayMode.argtypes = [ctypes.c_long]
GetDisplayMode.restype = ctypes.c_long

SetDisplayMode.argtypes = [ctypes.c_long]
SetDisplayMode.restype = ctypes.c_long

GetFastMode.argtypes = [ctypes.c_bool]
GetFastMode.restype = ctypes.c_bool

SetFastMode.argtypes = [ctypes.c_bool]
SetFastMode.restype = ctypes.c_long

GetSwitcherMode.argtypes = [ctypes.c_long]
GetSwitcherMode.restype = ctypes.c_long

SetSwitcherMode.argtypes = [ctypes.c_long]
SetSwitcherMode.restype = ctypes.c_long

GetSwitcherChannel.argtypes = [ctypes.c_long]
GetSwitcherChannel.restype = ctypes.c_long

SetSwitcherChannel.argtypes = [ctypes.c_long]
SetSwitcherChannel.restype = ctypes.c_long

GetSwitcherSignalStates.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
GetSwitcherSignalStates.restype = ctypes.c_long

SetSwitcherSignalStates.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
SetSwitcherSignalStates.restype = ctypes.c_long

SetSwitcherSignal.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
SetSwitcherSignal.restype = ctypes.c_long

GetAutoCalMode.argtypes = [ctypes.c_long]
GetAutoCalMode.restype = ctypes.c_long

SetAutoCalMode.argtypes = [ctypes.c_long]
SetAutoCalMode.restype = ctypes.c_long

GetAutoCalSetting.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long, ctypes.c_long]
GetAutoCalSetting.restype = ctypes.c_long

SetAutoCalSetting.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long, ctypes.c_long]
SetAutoCalSetting.restype = ctypes.c_long

GetActiveChannel.argtypes = [ctypes.c_long, ctypes.c_long, ctypes.c_long]
GetActiveChannel.restype = ctypes.c_long

SetActiveChannel.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_long, ctypes.c_long]
SetActiveChannel.restype = ctypes.c_long

GetChannelsCount.argtypes = [ctypes.c_long]
GetChannelsCount.restype = ctypes.c_long

GetOperationState.argtypes = [ctypes.c_ushort]
GetOperationState.restype = ctypes.c_ushort

Operation.argtypes = [ctypes.c_ushort]
Operation.restype = ctypes.c_long

SetOperationFile.argtypes = [ctypes.c_char_p]
SetOperationFile.restype = ctypes.c_long

Calibration.argtypes = [ctypes.c_long, ctypes.c_long,
        ctypes.c_double, ctypes.c_long]
Calibration.restype = ctypes.c_long

RaiseMeasurementEvent.argtypes = [ctypes.c_long]
RaiseMeasurementEvent.restype = ctypes.c_long

TriggerMeasurement.argtypes = [ctypes.c_long]
TriggerMeasurement.restype = ctypes.c_long

GetInterval.argtypes = [ctypes.c_long]
GetInterval.restype = ctypes.c_long

SetInterval.argtypes = [ctypes.c_long]
SetInterval.restype = ctypes.c_long

GetIntervalMode.argtypes = [ctypes.c_bool]
GetIntervalMode.restype = ctypes.c_bool

SetIntervalMode.argtypes = [ctypes.c_bool]
SetIntervalMode.restype = ctypes.c_long

GetBackground.argtypes = [ctypes.c_long]
GetBackground.restype = ctypes.c_long

SetBackground.argtypes = [ctypes.c_long]
SetBackground.restype = ctypes.c_long
