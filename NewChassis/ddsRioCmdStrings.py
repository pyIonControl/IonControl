# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
class ddsAD9959CmdStrings(object):
    def __init__(self):
        self.registerNamesAD9959 = {
                0x00: 'CSR',
                0x01: 'FR1',
                0x02: 'FR2',
                0x03: 'CFR',
                0x04: 'CFTW0',
                0x05: 'CPOW0',
                0x06: 'ACR',
                0x07: 'LSRR',
                0x08: 'RDW',
                0x09: 'FDW',
                0x0A: 'CW1',
                0x0B: 'CW2',
                0x0C: 'CW3',
                0x0D: 'CW4',
                0x0E: 'CW5',
                0x0F: 'CW6',
                0x10: 'CW7',
                0x11: 'CW8',
                0x12: 'CW9',
                0x13: 'CW10',
                0x14: 'CW11',
                0x15: 'CW12',
                0x16: 'CW13',
                0x17: 'CW14',
                0x18: 'CW15'
                }

    def writeDDSRegAD9959(self, register, value):
        cmdName = 'dds:setreg '
        cmdParams = '{0},{1}'
        if isinstance(register, int):
            command = cmdName + cmdParams.format(register,
                    self._hexStr(value))
        elif isinstance(register, str):
            regNum = list(self.registerNamesAD9959.values()).index(register)
            command = cmdName + cmdParams.format(regNum, self._hexStr(value))
        return command

    def readDDSRegAD9959(self, register):
        cmdName = 'dds:getreg '
        cmdParams = '{0}'
        if isinstance(register, int):
            command = cmdName + cmdParams.format(register)
        elif isinstance(register, str):
            command = cmdName + register
        return command

class ddsRioCmdStrings(ddsAD9959CmdStrings):
    def __init__(self):
        super(ddsRioCmdStrings, self).__init__()
        self.registerNames = {
                0x00: 'PHASEADJ1',
                0X01: 'PHASEADJ2', 
                0x02: 'FREQTUNING1',
                0X03: 'FREQTUNING2',
                0x04: 'DELTAFREQ',
                0x05: 'UPDATECLK',
                0x06: 'RAMPRATECLK',
                0x07: 'CNTRLREG',
                0x08: 'OSKMULT',
                0x09: 'DCARE',
                0x0A: 'OSKRAMPRATE',
                0x0B: 'CNTRLDAC'
                }

    def _hexStr(self, data):
        return '%X' % data

    def writeDDSReg(self, register, value):
        cmdName = 'dds:setreg '
        cmdParams = '{0},{1}'
        if isinstance(register, int):
            command = cmdName + cmdParams.format(self.registerNames[register],
                    self._hexStr(value))
        elif isinstance(register, str):
            command = cmdName + cmdParams.format(register, self._hexStr(value))
        return command

    def readDDSReg(self, register):
        cmdName = 'dds:getreg '
        cmdParams = '{0}'
        if isinstance(register, int):
            command = cmdName + cmdParams.format(self.registerNames[register])
        elif isinstance(register, str):
            command = cmdName + register
        return command

    def setDDSAutoUpdateClk(self, autoUpdateClk):
        if isinstance(autoUpdateClk, bool):
            autoUpdateClk = int(autoUpdateClk)
        elif isinstance(autoUpdateClk, int):
            pass
        cmdName = 'dds:autoupdateclk '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(autoUpdateClk)
        return command

    def getDDSAutoUpdateClk(self):
        command = 'dds:autoupdateclk?'
        return command

    def masterReset(self):
        return 'dds:mstrst'

    def getDDSActiveBoard(self):
        command = 'dds:activechnl?'
        return command

    def setDDSActiveBoard(self, value):
        cmdName = 'dds:activechnl '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(value)
        return command

    def setDDSBoardType(self, value):
        cmdName = 'dds:boardtype '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(value)
        return command

    def getDDSBoardType(self):
        command = 'dds:boardtype?'
        return command
        
    def writePTGConfig(self, index, delay, width):
        cmdName = 'ptg:pulseconfig '
        cmdParams = '{0},{1},{2}'
        command = cmdName + cmdParams.format(index, delay, width)
        return command

    def readPTGConfig(self, index):
        cmdName = 'ptg:pulseconfig? '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(index)
        return command

    def writePTGInvert(self, invert):
        cmdName = 'ptg:invert '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(int(invert))
        return command

    def readPTGInvert(self):
        return 'ptg:invert?'

    def writePTGCount(self, count):
        cmdName = 'ptg:pulsecount '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(count)
        return command

    def readPTGCount(self):
        return 'ptg:pulsecount?'

    def writePTGSoftTrig(self):
        return 'ptg:softtrig'

    def writeDoSoftTrig(self):
        return 'digout:softtrig'

    def writeDoSampleRate(self, sampleRate):
        cmdName = 'digout:samprate '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(sampleRate)
        return command

    def readDoSampleRate(self):
        return 'digout:samprate?'

    def writeDoRepeats(self, repeats):
        cmdName = 'digout:reps '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(repeats)
        return command

    def readDoRepeats(self):
        return 'digout:reps?'

    def writeDoBuffer(self, buff):
        cmdName = 'digout:buffer '
        delim = ','
        buffString = []
        for b in buff:
            buffString.append(str(b))
        cmdParams = delim.join(buffString)
        command = cmdName + cmdParams
        return command

    def writeCntActiveChnl(self, channel):
        cmdName = 'cnt:activechnl '
        cmdParams = '{0}'
        command = cmdName + cmdParams.format(channel)
        return command

    def readCntActiveChnl(self):
        return 'cnt:activechnl?'

    def readCntSamplesAvail(self):
        return 'cnt:samplesavail?'

    def readCntBuffer(self):
        return 'cnt:buffer?'

    def clearCntBuffer(self):
        return 'cnt:clearbuffer'

    def get20MHzState(self):
        return '20MHz:state?'

    def set20MHzState(self, state):
        if isinstance(state, bool):
            state = int(state)
        elif isinstance(state, int):
            pass
        else:
            errorString = 'Type {0} not supported.'
            errorString.format(type(state))
            raise TypeError(errorString)
        return '20MHz:state {0}'.format(state)


