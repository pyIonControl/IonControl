# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from .ddsRioClient import ddsRioClientFactory

class ddsRio(object):

    _instance = None
    initialized = False
    _iCount = 0

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ddsRio, cls).__new__(
                    cls, *args, **kwargs)
        cls._iCount += 1
        return cls._instance

    ## This is the constructor of the ddsRio class.
    #  @param clientType The ddsRio class supports multiple methods of
    #  communications - 'serial' and 'tcp'.  If 'serial' is used, then
    #  pass a device parameter as well for the com port such as 'COM0'.
    #  If 'tcp' is used, then pass an address parameter such as
    #  '192.168.10.1'
    #  Example Calls:
    #  ddsRio('serial', device = 'COM0')
    #  ddsRio('tcp', address = '192.168.10.1'
    def __init__(self, clientType, **kwargs):
        ## This is the value of the system clock, which is the external
        #  clock * frequency multiplier.
        if self.initialized == False:
            device = kwargs.get('device', 'COM0')
            baudrate = kwargs.get('baudrate', 115200)
            timeout = kwargs.get('timeout', 0.25)
            address = kwargs.get('address', '192.168.33.113')
            port = kwargs.get('port', 6431)
            verbosity = kwargs.get('verbosity', 0)
            
            if clientType.lower()  == 'serial':
                self.client = ddsRioClientFactory().newClient(0,
                        verbosity = verbosity)
                self.client.connect(device = device, baudrate = baudrate,
                        timeout = timeout)
            elif clientType.lower() == 'tcp':
                self.client = ddsRioClientFactory().newClient(1,
                        verbosity = verbosity)
                self.client.connect(address = address, port = port)

            self.verbosity = kwargs.get('verbosity', 0)
            self.CNT = ddsRioCounter(self.client)
            self.DOPort = ddsRioDigOutPort(self.client)
            #self.PulseGen = ddsRioPulseGen(self.client)
            self.DDS = ddsCollection(self.client)
            self.DDS.append(0)
            self.DDS.append(1)
            self.initialized = True

    def _getVerbosity(self):
        return self.client.verbosity

    def _setVerbosity(self, value):
        self.client.verbosity = value

    ## This is used primarily for debugging purposes. Setting the
    #  value to anything greater than 0 will cause information to
    #  be sent to the console.
    verbosity = property(_getVerbosity,
            _setVerbosity)

    ## This method will close the connection to the ddsRio device.
    #  @param self The object reference.
    def close(self):
        self.initialized = False
        if self.client:
            self.client.close()
            self.client = None
        '''
        else:
            self._iCount -= 1
        '''

    ## This is the destructor of the ddsRio class.
    #  @param self The object reference.
    def __del__(self):
        self.close()

class ddsType(object):
    AD9854 = 0
    AD9959 = 1
    def __init__(self):
        self.value = 0
        self.types = ('AD9854', 'AD9959')

    def __str__(self):
        return self.types[self.value]

class ddsFactory(object):
    @staticmethod
    def newDDS(DDSType, client):
        if isinstance(DDSType, str):
            if DDSType == 'AD9854':
                return ddsRioAD9854DDS(client)
            elif DDSType == 'AD9969':
                return ddsRioAD9959DDS(client)
            else:
                errorString = '"{0}" is not a valid DDSType.'.format(
                        DDSType)
                raise ValueError(errorString)
        elif isinstance(DDSType, int):
            if DDSType == 0:
                return ddsRioAD9854DDS(client)
            elif DDSType == 1:
                return ddsRioAD9959DDS(client)
            else:
                errorString = 'Value: {} is not a supported value'.format(
                        DDSType)
                raise ValueError(errorString)
        else:
            errorString = 'Type: {0} is not a supported type.'.format(
                    type(DDSType))
            raise TypeError(errorString)

class ddsParent(object):
    def __init__(self):
        raise NotImplementedError('This method is not implemented')

    def _getRegDict(self):
        raise NotImplementedError('This method is not implemented')

    ## This value is read-only and returns a dictionary of all the
    #  configuration registers on the dds.
    ddsRegDict = property(_getRegDict)

    def _getActiveBoard(self):
        activeBoard = self.client.getActiveBoard()
        return activeBoard

    def _setActiveBoard(self, activeBoard):
        self.client.setActiveBoard(activeBoard)

    activeBoard = property(_getActiveBoard, _setActiveBoard)

    def _getActiveChannel(self):
        raise NotImplementedError('This method is not implemented')

    def _setActiveChannel(self, activeChannel):
        raise NotImplementedError('This method is not implemented')

    activeChannel = property(_getActiveChannel, _setActiveChannel)

    def PrintAll(self):
        raise NotImplementedError('This method is not implemented')

    def SingleTone(self):
        raise NotImplementedError('This method is not implemented')

    def FSK(self):
        raise NotImplementedError('This method is not implemented')

    def ASK(self):
        raise NotImplementedError('This method is not implemented')

    def RampedFSK(self):
        raise NotImplementedError('This method is not implemented')

    def Chirp(self):
        raise NotImplementedError('This method is not implemented')

    def BPSK(self):
        raise NotImplementedError('This method is not implemented')

    def masterReset(self):
        self.client.masterReset()

class ddsCollection(ddsParent):
    def __init__(self, client):
        self._boardIndex = 0
        self.ddsList = []
        self.client = client

    #def _getBoardType(self):
    #    return self.ddsList[self._boardIndex].boardType

    #def _setBoardType(self, boardType):
    #    self.ddsList[self._boardIndex].boardType = boardType

    #boardType = property(_getBoardType, _setBoardType)
    def _getActiveBoard(self):
        return self._boardIndex

    def _setActiveBoard(self, activeBoard):
        self._boardIndex = activeBoard

    activeBoard = property(_getActiveBoard, _setActiveBoard)

    def _getActiveChannel(self):
        activeChannel = self.ddsList[self._boardIndex].activeChannel
        return activeChannel

    def _setActiveChannel(self, activeChannel):
        self.ddsList[self._boardIndex].activeChannel = activeChannel

    activeChannel = property(_getActiveChannel, _setActiveChannel)

    def _getFreqMultiplier(self):
        return self.ddsList[self._boardIndex].freqMultiplier

    def _setFreqMultiplier(self, freqMultiplier):
        self.ddsList[self._boardIndex].freqMultiplier = freqMultiplier

    freqMultiplier = property(_getFreqMultiplier, _setFreqMultiplier)

    def _getSysClk(self):
        sysclk = self.ddsList[self._boardIndex].sysclk
        return sysclk

    def _setSysClk(self, sysclk):
        self.ddsList[self._boardIndex].sysclk = sysclk

    sysclk = property(_getSysClk, _setSysClk)

    def append(self, DDSType):
        self.ddsList.append(ddsFactory.newDDS(DDSType, self.client))

    def PrintAll(self):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].PrintAll()

    def SingleTone(self, freq, amp, **kwargs):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].SingleTone(freq, amp, **kwargs)

    def FSK(self, freq1, freq2, amp):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].FSK(freq1, freq2, amp)

    def RampedFSK(self, freq1, freq2, rampTime, deltaFreq, amp):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].RampedFSK(freq1, freq2, rampTime,
            deltaFreq, amp)

    def BPSK(self, freq, phase1, phase2, amp):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].BPSK(freq, phase1, phase2, amp)

    def ASK(self, freq, amp1, amp2):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].ASK(freq, amp1, amp2)

    def masterReset(self):
        self.client.setBoardType(self._boardIndex)
        self.ddsList[self._boardIndex].masterReset()


class ddsRioAD9854DDS(ddsParent):
    def __init__(self, client):
        self.client = client
        self.sysclk = 300e6

    def _getRegDict(self):
        regDict = self.client.readAll()
        return regDict

    ## This value is read-only and returns a dictionary of all the
    #  configuration registers on the dds.
    ddsRegDict = property(_getRegDict)

    def _setActiveChannel(self, value):
        self.client.setActiveChannel(value)

    def _getActiveChannel(self):
        return self.client.getActiveChannel()

    activeChannel = property(_getActiveChannel, _setActiveChannel)

    def _setMode(self, mode):
        mode <<= 9
        cntrlReg = self.client.readCntrlReg()
        cntrlReg = (cntrlReg & 0xFFFFF1FF) | mode
        self.client.writeCntrlReg(cntrlReg)
        self._checkCntrlReg(cntrlReg)

    def _getFreqMultiplier(self):
        if self._bypassPLL:
            multiplier = 1
        else:
            cntrlReg = self.client.readCntrlReg()
            multiplier = (cntrlReg & 0x001F0000) >> 16
        return multiplier

    def _setFreqMultiplier(self, multiplier):
        maxMultiplier = 20
        minMultiplier = 1
        if multiplier > maxMultiplier:
            message = '\nThe frequency multiplier is too high.\n\tmaximum value: {0}'
            message = message.format(maxMultiplier)
            raise ValueError(message)
        elif multiplier < minMultiplier:
            message = '\nThe frequency multiplier is too low.\n\tminimum value: {0}'
            message = message.format(minMultiplier)
            raise ValueError(message)
        elif multiplier == 1:
            self._bypassPLL = True
        elif multiplier > 1:
            multiplier <<= 16
            cntrlReg = self.client.readCntrlReg()
            cntrlReg = (cntrlReg & 0xFFE0FFFF) | multiplier
            self.client.writeCntrlReg(cntrlReg)
            self._checkCntrlReg(cntrlReg)
            self._bypassPLL = False

    ## This will multipy the input clock to create a faster internal
    #  system clock.  Valid values range from 1 to 20.
    freqMultiplier = property(_getFreqMultiplier,
            _setFreqMultiplier)

    def _getBypassPLL(self):
        cntrlReg = self.client.readCntrlReg()
        bypassPLL = (cntrlReg & 0x00200000) >> 21
        return bool(bypassPLL)

    def _setBypassPLL(self, bypassPLL):
        bypassPLL = int(bypassPLL)
        bypassPLL <<= 21
        cntrlReg = self.client.readCntrlReg()
        cntrlReg = (cntrlReg & 0xFFDFFFFF) | bypassPLL
        self.client.writeCntrlReg(cntrlReg)
        self._checkCntrlReg(cntrlReg)

    _bypassPLL = property(_getBypassPLL, _setBypassPLL)

    def _getClearAccumulator1(self):
        cntrlReg = self.client.readCntrlReg()
        bypassPLL = (cntrlReg & 0x00008000) >> 15
        return bool(bypassPLL)

    def _setClearAccumulator1(self, value):
        value = int(value)
        value <<= 15
        cntrlReg = self.client.readCntrlReg()
        cntrlReg = (cntrlReg & 0xFFFF7FFF) | value
        self.client.writeCntrlReg(cntrlReg)
        self._checkCntrlReg(cntrlReg)

    _ClearAccumulator1 = property(_getClearAccumulator1,
            _setClearAccumulator1)

    def _getClearAccumulator2(self):
        cntrlReg = self.client.readCntrlReg()
        bypassPLL = (cntrlReg & 0x00004000) >> 14
        return bool(bypassPLL)

    def _setClearAccumulator2(self, value):
        value = int(value)
        value <<= 14
        cntrlReg = self.client.readCntrlReg()
        cntrlReg = (cntrlReg & 0xFFFFBFFF) | value
        self.client.writeCntrlReg(cntrlReg)
        self._checkCntrlReg(cntrlReg)

    _ClearAccumulator2 = property(_getClearAccumulator2,
            _setClearAccumulator2)

    def _getTriangleBit(self):
        cntrlReg = self.client.readCntrlReg()
        triangleBit = (cntrlReg & 0x00002000) >> 13
        return bool(triangleBit)

    def _setTriangleBit(self, value):
        value = int(value)
        value <<= 13
        cntrlReg = self.client.readCntrlReg()
        cntrlReg = (cntrlReg & 0xFFFFDFFF) | value
        self.client.writeCntrlReg(cntrlReg)
        self._checkCntrlReg(cntrlReg)

    ## Setting this bit to True will cause the dds to automatically
    #  perform a frequency shift when the dds in is Ramped FSK mode.
    triangleBit = property(_getTriangleBit, _setTriangleBit)

    def _getExtUDClk(self):
        cntrlReg = self.client.readCntrlReg()
        extUDClk = (cntrlReg & 0x00000100)
        return not bool(extUDClk)

    def _setExtUDClk(self, value):
        self.client.setAutoUpdateClk(bool(value))
        value = int(not value)
        cntrlReg = self.client.readCntrlReg()
        cntrlReg = (cntrlReg & 0xFFFFFEFF) | value
        self.client.writeCntrlReg(cntrlReg)
        self._checkCntrlReg(cntrlReg)

    extUDClk = property(_getExtUDClk, _setExtUDClk)

    def _checkCntrlReg(self, initialValue):
        cntrlReg = self.client.readCntrlReg()
        if initialValue != cntrlReg:
            print('The control register did no change value.')
            print('Make sure that the DDS had a RefClk, and')
            print('the Rio is properly connected to the DDS.')


    def _calcFTW(self, freq):
        mult = self.freqMultiplier
        ftw = int((freq * 2**48)/(self.sysclk*mult))
        return ftw

    def _calcPOW(self, phaseOffset):
        poWrd = int((phaseOffset * 2**14)/360)
        return poWrd

    ## This method will print all of the dds registers to the console.
    #  @param self The object reference.
    def PrintAll(self):
        ddsRegDict = self.ddsRegDict
        for key in list(ddsRegDict.keys()):
            print('register:{} value:{}'.format(hex(key),
                    hex(ddsRegDict[key])))


    ## This method will put the dds into a single tone mode.
    #  Single Tone Mode is a mode on the dds where a single frequency
    #  at a specified amplitude is output.
    #  @param self The object reference.
    #  @param freq The frequency of the output signal in Hz.
    #  @param amp A numeric value representing the amplitude of the
    #  output signal.
    def SingleTone(self, freq, amp, **kwargs):
        mode = 0
        self._setMode(mode)
        ftw = self._calcFTW(freq)
        self.client.writeFreqTuning1(ftw)
        self.client.writeOskMult(amp)

    ## This method will put the dds into Frequency Shift Keying (FSK)
    #  mode.
    #  FSK Mode is a mode on the dds where the output signal can be
    #  shifted from one frequency to another.  This is a hard shift
    #  where the dds will either output one frequecy or another.  It will
    #  not ramp between frequencies.  The dds will ramp frequencies in
    #  ramped FSK Mode.
    #  @param self The object reference.
    #  @param freq1 The value of one of the frequencies in Hz.
    #  @param freq2 The value of the second frequency in Hz.
    #  @param amp A numeric value representing the amplitude of the
    #  output signal.
    def FSK(self, freq1, freq2, amp):
        mode = 1
        self._setMode(mode)
        ftw1 = self._calcFTW(freq1)
        self.client.writeFreqTuning1(ftw1)
        ftw2 = self._calcFTW(freq2)
        self.client.writeFreqTuning2(ftw2)
        self.client.writeOskMult(amp)

    ## This method will put the dds into Ramped Frequency Shift Keying
    #  mode.  
    #  RampedFSK mode is a mode on the dds where the output signal can
    #  be ramped from one frequency to another at a ramp rate.
    #  @param self The object reference.
    #  @param freq1 The value of one of the frequencies in Hz.
    #  @param freq2 The value of the second frequency in Hz.
    #  @param rampTime The rate at which the frequencies will be ramped
    #  in seconds.
    #  @param deltaFreq The change in frequency that occurs after the
    #  time period specified by the rampTime. The frequency value is
    #  in Hz.
    #  @param amp A numeric value representing the amplitude of the
    #  output signal.
    def RampedFSK(self, freq1, freq2, rampTime, deltaFreq, amp):
        # swap freq1 and 2 if freq2 is less than freq1
        if freq2 < freq1:
            tempFreq = freq1
            freq1 = freq2
            freq2 = tempFreq
        maxRampTime = 2**20 / self.sysclk
        minRampTime = 1 / self.sysclk
        if rampTime > maxRampTime:
            message = '\nThe ramp time is too high for a system clock of {0} Hz.\n\tmax ramp Time: {1} seconds'
            message = message.format(self.sysclk, maxRampTime)
            raise ValueError(message)
        elif rampTime < minRampTime:
            message = '\nThe ramp time is too low for a system clock of {0} Hz.\n\tmin ramp Time: {1} seconds'
            message = message.format(self.sysclk, minRampTime)
            raise ValueError(message)
        mode = 2
        self._setMode(mode)
        ftw1 = self._calcFTW(freq1)
        self.client.writeFreqTuning1(ftw1)
        ftw2 = self._calcFTW(freq2)
        self.client.writeFreqTuning2(ftw2)
        self.client.writeOskMult(amp)
        rampTime = int((rampTime*self.sysclk) - 1)
        self.client.writeRampRateClk(rampTime)
        deltaFreq = self._calcFTW(deltaFreq)
        self.client.writeDeltaFreq(deltaFreq)

    def Chirp(self):
        mode = 3
        self._setMode(mode)
        # Need to add more register setting here

    ## This method will put the dds into Binary Phase Shift Keying
    #  mode.  In this mode the dds can switch between two phases.
    #  @param freq The value of the frequency in Hz.
    #  @param phase1 The initial phase in degrees.
    #  @param pahse2 The second phase in degrees.
    #  @param amp A numeric value representing the amplitude of the
    #  output signal.
    def BPSK(self, freq, phase1, phase2, amp):
        mode = 4
        self._setMode(mode)
        ftw = self._calcFTW(freq)
        pow1 = self._calcPOW(phase1)
        pow2 = self._calcPOW(phase2)
        self.client.writeFreqTuning1(ftw)
        #phase1 = int(phase1 * 2**14 / 360)
        self.client.writePhaseAdj1(pow1)
        #phase2 = int(phase2 * 2**14 / 360)
        self.client.writePhaseAdj2(pow2)
        self.client.writeOskMult(amp)

    def ASK(self, freq, amp1, amp2):
        super(ddsRioAD9854DDS, self).ASK()

class ddsRioAD9959DDS(ddsParent):
    def __init__(self, client):
        self.sysclk = 300e6
        self.client = client
        self.client.setBoardType(1)
        self.activeBoard = 1
        self.client.setAutoUpdateClk(True)
        self.activeChannel = 0
        self.boardNumber = 1

    def _getActiveChannel(self):
        tChannel = (0x1, 0x2, 0x4, 0x8) 
        data = self.client.readRegisterAD9959(0x00)
        data >>= 4
        try:
            activeChannel = tChannel.index(data)
        except ValueError:
            eString = 'Channel {0} not valid'
            raise ValueError(eString.format(data))
        return activeChannel

    def _setActiveChannel(self, activeChannel):
        tChannel = (0x1, 0x2, 0x4, 0x8) 
        activeChannel = tChannel[activeChannel]
        regData = self.client.readRegisterAD9959(0x00)
        regData &= 0x0F
        regData |= (activeChannel << 4)
        self.client.writeRegisterAD9959(0x00, regData)

    activeChannel = property(_getActiveChannel, _setActiveChannel)

    def _getFreqMultiplier(self):
        reg1 = self.client.readRegisterAD9959(0x01)
        freqMultiplier = (reg1 & 0x7c0000) >> 18
        if freqMultiplier < 4:
            freqMultiplier = 1
        return freqMultiplier

    def _setFreqMultiplier(self, mult):
        if mult < 4:
            mult = 0
        elif mult > 20:
            raise ValueError('Invalid Multiplier: Multiplier is greater than 20.')
        reg1 = self.client.readRegisterAD9959(0x01)
        reg1 &= 0x83FFFF
        reg1 |= mult << 18
        self.client.writeRegisterAD9959(0x01, reg1)

    freqMultiplier = property(_getFreqMultiplier, _setFreqMultiplier)

    # 0:No Mod, 1:Amplitude Mod, 2:Freq Mod, 3:Phase Mod
    def _getAFPSelect(self):
        reg3 = self.client.readRegisterAD9959(0x03)
        AFPSelect = reg3 >> 22
        return AFPSelect

    def _setAFPSelect(self, value):
        reg3 = self.client.readRegisterAD9959(0x03)
        reg3 =  (reg3 & 0x3FFFFF) | (value << 22)
        self.client.writeRegisterAD9959(0x03, reg3)

    def _getLinearSweepEnable(self):
        reg3 = self.client.readRegisterAD9959(0x03)
        LinearSweepEnable = (reg3 & 0x004000) >> 14
        return LinearSweepEnable

    def _setLinearSweepEnable(self, value):
        reg3 = self.client.readRegisterAD9959(0x03)
        reg3 = (reg3 & 0xFFBFFF) | (value << 14)
        self.client.writeRegisterAD9959(0x03, reg3)

    def _getModLevel(self):
        reg1 = self.client.readRegisterAD9959(0x01)
        ModLevel = (reg1 & 0x000300) >> 8
        return ModLevel

    def _setModLevel(self, value):
        reg1 = self.client.readRegisterAD9959(0x01)
        reg1 = (reg1 & 0xFFFCFF) | (value << 8)
        self.client.writeRegisterAD9959(0x1, reg1)

    def _setDACCurrent(self, value):
        DACValue = (0x0, 0x2, 0x1, 0x3)
        value = DACValue[value]
        reg3 = self.client.readRegisterAD9959(0x03)
        amp = value << 8
        reg3 = (reg3 & 0xFFFCFF) | amp
        self.client.writeRegisterAD9959(0x03, reg3)

    def _getAmpScaleFactor(self):
        reg6 = self.client.readRegisterAD9959(0x06)
        AmpScaleFactor = reg6 & 0x0003FF
        return AmpScaleFactor

    def _setAmpScaleFactor(self, value):
        reg6 = self.client.readRegisterAD9959(0x06)
        reg6 = (reg6 & 0xFFFC00) | value
        self.client.writeRegisterAD9959(0x06, reg6)

    def _getAmpMultEnable(self):
        reg6 = self.client.readRegisterAD9959(0x06)
        AmpMultEnable = (reg6 & 0x001000) >> 12
        return AmpMultEnable

    def _setAmpMultEnable(self, value):
        reg6 = self.client.readRegisterAD9959(0x06)
        reg6 = (reg6 & 0xFFEFFF) | (value << 12)
        self.client.writeRegisterAD9959(0x06, reg6)

    def _calcFTW(self, freq):
        mult = self.freqMultiplier
        ftw = int((freq * 2**32)/(self.sysclk*mult))
        return ftw

    def _calcPOW(self, phaseOffset):
        poWrd = int((phaseOffset * 2**14)/360)
        return poWrd

    def _getRegDict(self):
        return self.client.readAllAD9959()

    ## This value is read-only and returns a dictionary of all the
    #  configuration registers on the dds.
    ddsRegDict = property(_getRegDict)

    def PrintAll(self):
        self.client.setActiveBoard(self.boardNumber)
        ddsRegDict = self.ddsRegDict
        for key in list(ddsRegDict.keys()):
            print('register:{0} value:{1}'.format(hex(key),
                    hex(ddsRegDict[key])))

    def SingleTone(self, freq, amp, **kwargs):
        self.client.setActiveBoard(self.boardNumber)
        if 'channel' in kwargs:
            self.activeChannel = kwargs['channel']
        self._setAFPSelect(0)
        FTW = self._calcFTW(freq)
        self.client.writeRegisterAD9959(0x04, FTW)
        self._setDACCurrent(amp)

    def FSK(self, freq1, freq2, amp):
        self.client.setActiveBoard(self.boardNumber)
        self._setLinearSweepEnable(0)
        self._setModLevel(0)
        self._setAFPSelect(2)
        FTW1 = self._calcFTW(freq1)
        FTW2 = self._calcFTW(freq2)
        self.client.writeRegisterAD9959(0x04, FTW1)
        self.client.writeRegisterAD9959(0x0A, FTW2)
        self._setDACCurrent(3)

    def ASK(self, freq, amp1, amp2):
        self.client.setActiveBoard(self.boardNumber)
        self._setLinearSweepEnable(0)
        self._setModLevel(0)
        self._setAFPSelect(1)
        FTW = self._calcFTW(freq)
        self.client.writeRegisterAD9959(0x04, FTW)
        self._setAmpScaleFactor(amp1)
        self.client.writeRegisterAD9959(0x0A, amp2<<22)

    def BPSK(self, freq, phase1, phase2, amp):
        self.client.setActiveBoard(self.boardNumber)
        self._setLinearSweepEnable(0)
        self._setModLevel(0)
        self._setAFPSelect(3)
        FTW = self._calcFTW(freq)
        self.client.writeRegisterAD9959(0x04, FTW)
        POW1 = self._calcPOW(phase1)
        POW2 = self._calcPOW(phase2)
        self.client.writeRegisterAD9959(0x05, POW1)
        self.client.writeRegisterAD9959(0x0A, POW2<<18)

    def FreqModulation(self, freqList, amp):
        raise NotImplementedError('FreqModulation is not Implemented')

    def AmpModulation(self, ampList):
        raise NotImplementedError('AmpModulation is not Implemented')

    def PhaseModulation(self, phaseList, amp):
        raise NotImplementedError('PhaseModulation is not Implemented')

    def masterReset(self):
        super(ddsRioAD9959DDS, self).masterReset()
        self.activeChannel = 0

class ddsRioPulseGen(object):
    def __init__(self, client):
        self.client = client

    ## This method configure the pulse generator.
    #  @param self The object reference.
    #  @param configDict A dictionary containing delays and pulse widths.
    #  <br /><b>Example:</b>
    #  <br />&nbsp;&nbsp;&nbsp;&nbsp;{0: (10e-3, 100e-3), 1:(20e-3, 50e-3)}
    #  <br />
    #  This will create two pulses with the first pulse delayed 10ms from
    #  the trigger and a pulse width of 100ms, and the second pulse
    #  delayed 20ms from the falling edge of the last pulse and a pulse
    #  width of 50ms.
    def config(self, configDict):
        for key in configDict:
            delay = int(configDict[key][0]/25e-9)
            width = int(configDict[key][1]/25e-9)
            print(delay, width)
            self.client.writePulseConfig(key, delay,
                    width)
        self.client.writePulseCount(len(configDict))

    ## This method will initiate a trigger for the pulse generator.
    #  This is useful for debuging purposes. If a hardware trigger is
    #  not available, then running this method will perform a trigger.
    #  @param self The object reference.
    def swTrig(self):
        self.client.sendPulseSWTrigger()

class ddsRioDigOutPort(object):
    def __init__(self, client):
        self.client = client

    def swTrig(self):
        self.client.sendDoSWTrigger()

    def writeBuffer(self, buff):
        self.client.writeDoBuffer(buff)

    def _getDoSampleRate(self):
        sampleRate = self.client.readDoSampleRate()
        return sampleRate

    def _setDoSampleRate(self, sampleRate):
        self.client.writeDoSampleRate(sampleRate)

    sampleRate = property(_getDoSampleRate, _setDoSampleRate)

    def _getDoRepeats(self):
        repeats = self.client.readDoRepeats()
        return repeats

    def _setDoRepeats(self, repeats):
        self.client.writeDoRepeats(repeats)

    repeats = property(_getDoRepeats, _setDoRepeats)


class ddsRioCounter(object):
    def __init__(self, client):
        self.client = client
        self.clearBuffer()

    def _getSamplesAvail(self):
        return self.client.readCntSamplesAvail()

    samplesAvail = property(_getSamplesAvail)

    def _getActiveChannel(self):
        return self.client.readCntActiveChnl()

    def _setActiveChannel(self, channel):
        self.client.writeCntActiveChnl(channel)
        
    activeChannel = property(_getActiveChannel, _setActiveChannel)

    def Read(self):
        buff = self.client.readCntBuffer()
        self.clearBuffer()
        return buff

    def clearBuffer(self):
        self.client.clearCntBuffer()


if __name__ == '__main__':
    import sys
    clientType = sys.argv[1].lower() 
    if clientType == 'tcp':
        ddsRio = ddsRio(clientType, address = '192.168.10.10', port = 6431)
    elif clientType == 'serial':
        ddsRio = ddsRio(clientType, device = 'COM1')

    configDict = {0: (0, 2.5e-6), 1: (2.5e-6, 2.5e-6), 2: (2.5e-6, 2.5e-6)}
    ddsRio.pulseConfig(configDict)
    ddsRio.pulseSwTrig()

    regDict = ddsRio.ddsRegDict
    ddsRio.PrintAll()
    ddsRio.sysclk = 10e6

    input('Press return to run single mode.')
    ddsRio.SingleTone(100e3, 0x250)
    ddsRio.PrintAll()

    input('Press return to run FSK mode.')
    ddsRio.FSK(200e3, 300e3, 0x250)
    ddsRio.PrintAll()
    input('Press return to run Ramped FSK mode.')
    ddsRio.RampedFSK(200e3, 300e3, 100e-3, 1e3, 0x250)
    ddsRio.PrintAll()
    input('Press return to run BPSK mode.')
    ddsRio.BPSK(100e3, 0, 180, 0x250)
    ddsRio.PrintAll()
