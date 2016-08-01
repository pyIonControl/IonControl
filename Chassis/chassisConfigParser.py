# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from configparser import SafeConfigParser
from modules.stringutilit import ensureAsciiBytes

## This class can read and write a WaveformChassis configuration file.
class chassisConfigParser(SafeConfigParser):
    def _createTestData(self):
        slots = list(range(2, 19))
        [slots.remove(x) for x in [8, 9, 10, 14]]
        aoDevsAndChnls = ['PXI1Slot{0}/ao0:7'.format(x) for x in slots]
        doDevsAndChnls = ['PXI1Slot{0}/port0/line0:7'.format(x)
                for x in slots]
        niSyncDev = 'PXI1Slot' + str(14) 
        values = []
        for i in range(len(slots)):
            values.append([aoDevsAndChnls[i], doDevsAndChnls[i]])

        data = dict(list(zip(list(range(len(slots))), values)))
        return data, niSyncDev

    ## The function writes and creates a configuration file based on the
    #  input parameters.
    #  @param self The object pointer.
    #  @param filePath The location of the file to be created
    #  @param data A dictionary containing the analog output
    #  and digital output channel names.
    #  @param niSyncDev The name of the NI-Sync card.
    def write(self, filePath, data, niSyncDev):
        section = 'WaveformChassis'
        self.add_section(section)
        self.set(section, 'sync card', niSyncDev)
        for key, value in data.items():
            section = 'WaveformGenerator{0}'.format(key)
            self.add_section(section)
            self.set(section, 'ao channel', value[0])
            self.set(section, 'do channel', value[1])
        f = open(filePath, 'wb')
        SafeConfigParser.write(self, f)
        f.close()

    ## This function will create a default file with default values
    #  at the location specified by the filePath parameter.
    #  @param filePath The location of the file to be created.
    def createDefaultFile(self, filePath):
        data, niCard = self._createTestData()
        self.write(filePath, data, niCard)
    
    ## This function will return the information read from the
    #  configuration file.
    def read(self, filePath):
        SafeConfigParser.read(self, filePath)

        # Initialize variables for reading from the Waveform
        # Chassis section.
        section = 'WaveformChassis'
        option = 'sync card'
        niSyncDev = ''
        if self.has_section(section):
            if self.has_option(section, option):
                niSyncDev = self.get(section, 'sync card')

        # Initialize variables prior to running the loop.
        i= 0
        aoChannels = []
        doChannels = []
        while True:
            section = 'WaveformGenerator{0}'.format(i)
            if not self.has_section(section):
                break
            options = ['ao channel', 'do channel']
            optionInfo = []
            for option in options:
                if self.has_option(section, option): 
                    optionInfo.append(self.get(section, option))
                else:
                    optionInfo.append('')
            aoChannels.append(optionInfo[0])
            doChannels.append(optionInfo[1])
            i += 1
        return [ensureAsciiBytes(ch) for ch in aoChannels], [ensureAsciiBytes(ch) for ch in doChannels], ensureAsciiBytes(niSyncDev)

if __name__ == '__main__':
    config = chassisConfigParser()
    ao, do, sync = config.read('example.cfg')
    print(ao)
    print('\n')
    print(do)
    print('\n')
    print(sync)
