# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .LowLevelThum import *

class THUM(object):
    def __init__(self):
        self.temp = 0.0
        self.dewPt = 0.0
        self.rH = 0.0

    def Read(self):
        err = Read()
        if err > 0:
            raise ThumError(code = err)
        self.temp = GetTemp()
        self.rH = GetRH()
        self.dewPt = GetDewPt()
        data = {'temp': self.temp, 'rH':self.rH, 'dewPt':self.dewPt}
        return data

    def Reset(self):
        return Reset()

    def _getTempUnit(self):
        unit = GetTempUnit()
        if unit == 1:
            unit = 'C'
        elif unit == 2:
            unit = 'F'
        else:
            raise ValueError('The THUM dll returned an invalid unit value: {0}'.format(unit))
        return unit

    def _setTempUnit(self, value):
        if isinstance(value, int):
            err = SetTempUnit(value)
        elif isinstance(value, str):
            validUnits = ('C', 'F', 'notValid')
            for i, unit in enumerate(validUnits):
                if unit == value:
                    break
            if validUnits[i] == 'notValid':
                errStr = "Expected 'C' or 'F' Got '{}'".format(value)
                raise ValueError(errStr)
            intValue = i + 1
            print(intValue)
            err = SetTempUnit(intValue)
        if err > 0:
            raise ThumError(code = err)

    tempUnit = property(_getTempUnit, _setTempUnit)

class ThumError(Exception):
    def __init__(self, **kwargs):
        self.code = kwargs.get('code', 0)
        errorMsgs = ('SUCCESS', 'Bad Temperature Unit', 'THUM Not Found',
                'Read Timeout', 'Write Failed', 'Read Failed',
                'Result Out Of Range')
        self.msg =  errorMsgs[self.code]

    def __str__(self):
        ret = '\n\tCode: {0} \n\tMessage: {1}'.format(self.code, self.msg)
        return ret


if __name__ == '__main__':
    myThum = THUM()
    myThum.tempUnit = 2
    myThum.tempUnit
    print(myThum.Read())
