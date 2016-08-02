# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy


'''
class digBuffData(object):
    def __init__(self, *args, **kwargs):
        self.dtype = kwargs.get('dtype', numpy.dtype('uint8'))
        return numpy.uint8(args[0])
'''

class digitalBufferManipulation(object):
    def __init__(self, **kwargs):
        self.data = numpy.uint8([])
        self.isU8 = isinstance(self.data, numpy.dtype('uint8'))
        self.isU16 = isinstance(self.data, numpy.dtype('uint16'))
        self.sampleRate = 1E6

    def delayAndWidth(self, dictionary):
        for i, channel in enumerate(dictionary):
            dataType = type(dictionary[channel][0])
            twoDim = dataType == list or dataType == tuple 
            if twoDim:
                for j in range(len(dictionary[channel])):
                    self.channelDelayAndWidth(channel, dictionary[channel][j][0], 
                            dictionary[channel][j][1])
            else:
                self.channelDelayAndWidth(channel, dictionary[channel][0], 
                        dictionary[channel][1])
        return self.data

    def lastValues(self, valuesList):
        for i, value in enumerate(valuesList):
            self.channelLastValue(i, value)
        return self.data

    def channelLastValue(self, channelNum, value):
        if len(self.data) <= 0:
            raise ValueError('No Channel Data. Try using the delayAndWidth method.')

        if value == True or value > 0:
            binChannel = numpy.uint8(2**channelNum)
            self.data[-1] = self.data[-1] | binChannel
        else:
            binChannel = ~numpy.uint8(2**channelNum)
            self.data[-1] = self.data[-1] & binChannel
        return self.data

    def channelDelayAndWidth(self, channelNum, delay, width, invert = False):
        # Initialize variables
        binChannel = 2**channelNum
        channelData = numpy.uint8([])

        # find delaySampleSize, widthSampleSize, and dataSize
        delaySampleSize = int(self.sampleRate*delay)
        widthSampleSize = int(self.sampleRate*width)
        newDataSize = delaySampleSize + widthSampleSize + 1

        # resize data if it is required
        oldDataSize = len(self.data)
        if newDataSize > oldDataSize:
            self.data = numpy.resize(self.data, newDataSize)
            self.data[oldDataSize:newDataSize] = 0
        else:
            newDataSize = oldDataSize
        channelData.resize(newDataSize)

        if invert:
            for i in range(delaySampleSize):
                channelData[i] = binChannel

            channelData[-1] = binChannel

            for i in range(delaySampleSize, delaySampleSize+widthSampleSize):
                channelData[i] = 0
        else:
            for i in range(delaySampleSize):
                channelData[i] = 0

            for i in range(delaySampleSize, delaySampleSize+widthSampleSize):
                channelData[i] = binChannel
        self.data = self.data | channelData
        return self.data

    def clearChannel(self, channelNum):
        binChannel = 2**channelNum
        invChannelData = numpy.uint8([])
        invChannelData.resize(len(self.data))
        invChannelData.fill(~binChannel)
        self.data = self.data & invChannelData

    def clearBufferData(self):
        self.data = numpy.uint8([])

class digitalBufferManipulationU8(digitalBufferManipulation):
    pass

class digitalBufferManipulationU16(digitalBufferManipulation):
    def __init__(self, **kwargs):
        super(digitalBufferManipulationU16, self).__init__()
        self.data = numpy.uint16([])

    def channelLastValue(self, channelNum, value):
        if len(self.data) <= 0:
            raise ValueError('No Channel Data. Try using the delayAndWidth method.')

        if value == True or value > 0:
            binChannel = numpy.uint16(2**channelNum)
            self.data[-1] = self.data[-1] | binChannel
        else:
            binChannel = ~numpy.uint16(2**channelNum)
            self.data[-1] = self.data[-1] & binChannel
        return self.data

    def channelDelayAndWidth(self, channelNum, delay, width, invert = False):
        # Initialize variables
        binChannel = 2**channelNum
        channelData = numpy.uint16([])

        # find delaySampleSize, widthSampleSize, and dataSize
        delaySampleSize = int(self.sampleRate*delay)
        widthSampleSize = int(self.sampleRate*width)
        newDataSize = delaySampleSize + widthSampleSize + 1

        # resize data if it is required
        oldDataSize = len(self.data)
        if newDataSize > oldDataSize:
            self.data = numpy.resize(self.data, newDataSize)
            self.data[oldDataSize:newDataSize] = 0
        else:
            newDataSize = oldDataSize
        channelData.resize(newDataSize)

        if invert:
            for i in range(delaySampleSize):
                channelData[i] = binChannel

            channelData[-1] = binChannel

            for i in range(delaySampleSize, delaySampleSize+widthSampleSize):
                channelData[i] = 0
        else:
            for i in range(delaySampleSize):
                channelData[i] = 0

            for i in range(delaySampleSize, delaySampleSize+widthSampleSize):
                channelData[i] = binChannel
        self.data = self.data | channelData
        return self.data

    def clearChannel(self, channelNum):
        binChannel = 2**channelNum
        invChannelData = numpy.uint16([])
        invChannelData.resize(len(self.data))
        invChannelData.fill(~binChannel)
        self.data = self.data & invChannelData

    def clearBufferData(self):
        self.data = numpy.uint16([])

if __name__ == "__main__":
    buff = digitalBufferManipulation()
    testData = {0: ((10e-6, 10e-6), (1e-6, 5e-6))}
    print(buff.delayAndWidth(testData))
    testData = {0: (10e-6, 10e-6)}
    #buff.clearChannel(0)
    buff.clearBufferData()
    print(buff.delayAndWidth(testData))
    '''
    channel = int(raw_input('Enter a channel number [0-7]: '))
    delay = float(raw_input('Enter a delay time: '))
    width = float(raw_input('Enter a width time: '))
    print buff.channelDelayAndWidth(channel, delay, width)
    '''

