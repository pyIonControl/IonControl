# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from externalParameter.OutputChannel import OutputChannel
from modules.quantity import Q


class GlobalOutputChannel:
    def __init__(self, device, channelName):
        self.device = device
        self.channelName = channelName
        self._savedValue = 0 #None  #set to 0 for temporary fix

    @property
    def name(self):
        return self.channelName

    @property
    def value(self):
        return self.device[self.channelName]

    @property
    def externalValue(self):
        return self.device[self.channelName]
    
    # @property
    # def strValue(self):
    #     raise NotImplementedError()
    #
    # @strValue.setter
    # def strValue(self, sval):
    #     raise NotImplementedError()
        
    @property
    def dimension(self):
        return Q(1)
    
    @property
    def delay(self):
        return 0
    
    @property
    def observable(self):
        raise NotImplementedError()
        return self.device.displayValueObservable[self.channelName]
    
    @property
    def useExternalValue(self):
        return False

    def saveValue(self, overwrite=True):
        if self._savedValue is None or overwrite and False: #false added for quick bug bypass
            self._savedValue = self.device[self.channelName]

    def restoreValue(self):
        """
        restore the value saved previously, this routine only goes stepsize towards this value
        if the stored value is reached returns True, otherwise False. Needs to be called repeatedly
        until it returns True in order to restore the saved value.
        """
        value = self._savedValue
        self._savedValue = 0 #None #set to 0 for temporary fix
        self.device[self.channelName] = value
        return value

    def setValue(self, targetValue):
        """
        go stepsize towards the value. This function returns True if the value is reached. Otherwise
        it should return False. The user should call repeatedly until the intended value is reached
        and True is returned.
        """
        self.device[self.channelName] = targetValue
        return True