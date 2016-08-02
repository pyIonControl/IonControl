# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from . import WLMFunctions as WLMFunc
from . import WLMConstants as WLMConst

class WLM(object):
    #def __init__(self):
    #    pass

    def Instantiate(self, RFC, Mode, P1, P2):
        err = WLMFunc.Instantiate(RFC, Mode, P1, P2)
        if err.value < 1:
            raise WLMError(code = err.value)

    def GetWavelength(self):
        data = WLMFunc.GetWavelength(0.0)
        if data < 1:
            raise WLMError(code = data)
        return data

    def GetWavelength2(self):
        data = WLMFunc.GetWavelength2(0.0)
        if data < 1:
            raise WLMError(code = data)
        return data

class WLMError(Exception):
    def __init__(self, **kwargs):
        self.code = kwargs.get('code', None)
        errorMsgs = {
                WLMConst.ErrNoValue:'No Value',
                WLMConst.ErrNoSignal:'No Signal',
                WLMConst.ErrBadSignal:'Bad Signal',
                WLMConst.ErrLowSignal:'Low Signal',
                WLMConst.ErrBigSignal:'Big Signal',
                WLMConst.ErrWlmMissing: 'WLM Missing',
                WLMConst.ErrNotAvailable: 'Not Available',
                WLMConst.InfNothingChanged: 'Nothing Changed',
                WLMConst.ErrNoPulse: 'No Pulse',
                WLMConst.ErrDiv0: 'Divided By Zero',
                WLMConst.ErrOutOfRange: 'Out of Range',
                WLMConst.ErrUnitNotAvailable: 'Unit Not Available',
                WLMConst.ErrTemperature: 'Temperature Error',
                WLMConst.ErrTempNotMeasured: 'Temperature Not Measured',
                WLMConst.ErrTempNotAvailable: 'Temperature Not Available',
                WLMConst.ErrTempWlmMissing: 'Temperature WLM Missing',
                WLMConst.ErrDistance: 'Distance Error',
                WLMConst.ErrDistanceNotAvailable: 'Distance Not Available',
                WLMConst.ErrDistanceWlmMissing: 'Distance WLM Missing'}
        if self.code is not None:
            self.msg = errorMsgs[self.code]

    def __str__(self):
        ret = '\n\tCode: {0} \n\tMessage: {1}'.format(self.code, self.msg)
        return ret
