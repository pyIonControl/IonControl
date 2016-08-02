# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
class InputChannel(object):
    def __init__(self, device, deviceName, channelName):
        self.device = device
        self.deviceName = deviceName
        self.channelName = channelName

    @property
    def newData(self):
        return self.device.newData
        
    @property
    def value(self):
        return self.device.getValue(self.channelName)
    
    @property
    def inputData(self):
        return self.device.getInputData(self.channelName)