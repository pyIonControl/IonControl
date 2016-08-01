# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from externalParameter.OutputChannel import OutputChannel
from modules.quantity import Q


class VoltageOutputChannel(OutputChannel):
    def __init__(self, device, deviceName, channelName, globalDict):
        super(VoltageOutputChannel, self).__init__(device, deviceName, channelName, globalDict)

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
