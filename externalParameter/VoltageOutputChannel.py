# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from externalParameter.OutputChannel import OutputChannel
from modules.quantity import Q


class VoltageOutputChannel:
    def __init__(self, device, deviceName, channelName, globalDict):
        self.device = device
        self.deviceName = deviceName
        self.channelName = channelName
        #super(VoltageOutputChannel, self).__init__(device, deviceName, channelName, globalDict)

    @property
    def name(self):
        return self.channelName

    @property
    def value(self):
        return self.device.getValue(self.channelName)

    @property
    def externalValue(self):
        return self.device.currentValue(self.channelName)
    
    @property
    def strValue(self):
        return self.device.strValue(self.channelName)
    
    @strValue.setter
    def strValue(self, sval):
        self.device.setStrValue(self.channelName, sval)
        
    @property
    def dimension(self):
        return Q(1)
    
    @property
    def delay(self):
        return 0
    
    @property
    def observable(self):
        return self.device.displayValueObservable[self.channelName]
    
    @property
    def useExternalValue(self):
        return False

    def saveValue(self, overwrite=True):
        self.device.saveValue(self.channelName)

    def restoreValue(self):
        """
        restore the value saved previously, this routine only goes stepsize towards this value
        if the stored value is reached returns True, otherwise False. Needs to be called repeatedly
        until it returns True in order to restore the saved value.
        """
        return self.device.restoreValue(self.channelName)

    def setValue(self, targetValue):
        """
        go stepsize towards the value. This function returns True if the value is reached. Otherwise
        it should return False. The user should call repeatedly until the intended value is reached
        and True is returned.
        """
        self.device.setValue(self.channelName, targetValue)
        return True