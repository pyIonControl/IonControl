# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
from multiprocessing import Process
import struct

import ok

from mylogging.ServerLogging import configureServerLogging
from modules import enum
from modules.quantity import Q
from pulser.bitfileHeader import BitfileInfo
from pulser.PulserHardwareServer import sliceview, sliceview_remainder

ModelStrings = {
        0: 'Unknown',
        1: 'XEM3001v1',
        2: 'XEM3001v2',
        3: 'XEM3010',
        4: 'XEM3005',
        5: 'XEM3001CL',
        6: 'XEM3020',
        7: 'XEM3050',
        8: 'XEM9002',
        9: 'XEM3001RB',
        10: 'XEM5010',
        11: 'XEM6110LX45',
        15: 'XEM6110LX150',
        12: 'XEM6001',
        13: 'XEM6010LX45',
        14: 'XEM6010LX150',
        16: 'XEM6006LX9',
        17: 'XEM6006LX16',
        18: 'XEM6006LX25',
        19: 'XEM5010LX110',
        20: 'ZEM4310',
        21: 'XEM6310LX45',
        22: 'XEM6310LX150',
        23: 'XEM6110v2LX45',
        24: 'XEM6110v2LX150'
}

ErrorMessages = {
     0: 'NoError',
    -1: 'Failed',
    -2: 'Timeout',
    -3: 'DoneNotHigh',
    -4: 'TransferError',
    -5: 'CommunicationError',
    -6: 'InvalidBitstream',
    -7: 'FileError',
    -8: 'DeviceNotOpen',
    -9: 'InvalidEndpoint',
    -10: 'InvalidBlockSize',
    -11: 'I2CRestrictedAddress',
    -12: 'I2CBitError',
    -13: 'I2CNack',
    -14: 'I2CUnknownStatus',
    -15: 'UnsupportedFeature',
    -16: 'FIFOUnderflow',
    -17: 'FIFOOverflow',
    -18: 'DataAlignmentError',
    -19: 'InvalidResetProfile',
    -20: 'InvalidParameter'
}


class DeviceDescription:
    pass

class FPGAException(Exception):
    pass
        
def check(number, command):
    if number is not None and number<0:
        raise FPGAException("OpalKelly exception '{0}' in command {1}".format(ErrorMessages.get(number, number), command))

def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if( (val&(1<<(bits-1))) != 0 ):
        val -= 1 << bits
    return val

class PulserHardwareException(Exception):
    pass

class StreamDataItem:
    def __init__(self):
        self.samples = 0
        self.errorSigSum = 0
        self.errorSigMin = 0
        self.errorSigMax = 0
        self.errorSigSumSq = 0;
        self.freqSum = 0
        self.freqMin = 0
        self.freqMax = 0

class StreamData(list):
    def __init__(self):
        super(StreamData, self).__init__(self)
        self.overrun = False   

class ScopeData:
    def __init__(self):
        self.errorSig = list()
        self.frequency = list()
        
class FinishException(Exception):
    pass

class AlignmentException( Exception):
    def __init__(self, length):
        super(AlignmentException, self).__init__()
        self.length = length

class DigitalLockControllerServer(Process):
    timestep = Q(5, 'ns')
    def __init__(self, dataQueue, commandPipe, loggingQueue):
        super(DigitalLockControllerServer, self).__init__()
        self.dataQueue = dataQueue
        self.commandPipe = commandPipe
        self.running = True
        self.openModule = None
        self.xem = None
        self.loggingQueue = loggingQueue
        
        # PipeReader stuff
        self.state = self.analyzingState.normal
        self.scopeData = ScopeData()
        self.streamData = StreamData()
        self.timestampOffset = 0
        
        self.streamBuffer = bytearray()

        self._integrationTime = Q(100, 'ms')
        
        self.scopeEnabled = False
        self.scopeStopAtEnd = False
        self.scopeData = ScopeData()
        
    def run(self):
        configureServerLogging(self.loggingQueue)
        logger = logging.getLogger(__name__)
        while (self.running):
            if self.commandPipe.poll(0.02):
                try:
                    commandstring, argument, kwargs = self.commandPipe.recv()
                    command = getattr(self, commandstring)
                    logger.debug( "DigitalLockControllerServer {0} {1}".format(commandstring, argument) )
                    self.commandPipe.send(command(*argument, **kwargs))
                except Exception as e:
                    self.commandPipe.send(e)
            self.readDataFifo()
        self.dataQueue.put(FinishException())
        logger.info( "Pulser Hardware Server Process finished." )
        self.dataQueue.close()
        self.loggingQueue.put(None)
        self.loggingQueue.close()
#         self.loggingQueue.join_thread()
            
    def finish(self):
        self.running = False
        return True

    analyzingState = enum.enum('normal', 'scanparameter')
    def readDataFifo(self):
        logger = logging.getLogger(__name__)
        if (self.scopeEnabled):
            scopeData, _ = self.readScopeData(8)
            if scopeData is not None:
                for s in sliceview(scopeData, 8):
                    (code, ) = struct.unpack('Q', s)
                    if code==0xffffffffffffffff:
                        self.dataQueue.put( self.scopeData )
                        logger.debug("sent data {0}".format(len(self.scopeData.errorSig)))
                        self.scopeData = ScopeData()
                        self.scopeEnabled = False
                    else:
                        self.scopeData.errorSig.append( twos_comp(code >> 48, 16) )
                        self.scopeData.frequency.append( twos_comp(code & 0x7fffffffffff, 47) )
                   
        data, self.streamData.overrun = self.readStreamData(48)
        if data:
            self.streamBuffer.extend( data )
            while len(self.streamBuffer)>=64:
                try:
                    for itembuffer in sliceview(self.streamBuffer, 64):
                        self.unpackStreamRecord(itembuffer)
                    if len(self.streamData)>0:
                        self.dataQueue.put( self.streamData )
                        self.streamData = StreamData()     

                    self.streamBuffer = bytearray( sliceview_remainder(self.streamBuffer, 64) )           
                except AlignmentException as e:
                    logger.info("data not aligned skipping 2 bytes")
                    self.streamBuffer = bytearray( self.streamBuffer[e.length*48+2:] )  # e.length holds the number of successfully read records
     
    def unpackStreamRecord(self, itembuffer ):
        item = StreamDataItem()
        (errorsig, item.errorSigMax, item.errorSigMin, item.samples, freq0, freq1, freq2, item.errorSigSumSq, 
         item.externalMax, item.externalMin, item.externalCount, externalSum) = struct.unpack('QhhIQQQQHHIQ', itembuffer)
        item.lockStatus = (externalSum >> 46) & 0x3
        item.externalMax &= 0xffff
        item.externalMin &= 0xffff
        if errorsig & 0xffff000000000000 != 0xfefe000000000000 or freq2 &  0xffff000000000000 != 0xefef000000000000:
            raise AlignmentException(len(self.streamData))
        if item.samples>0:
            item.errorSigSum = twos_comp( (errorsig&0xffffffffffff), 48) 
            item.freqMin = twos_comp( freq1 & 0xffffffffffff, 48 )
            item.freqMax = twos_comp( freq2 & 0xffffffffffff, 48 )
            item.freqSum = twos_comp( (freq0 <<8) | (freq1 >> 56), 72 ) 
            item.externalSum = externalSum & 0xfffffffffff
            self.streamData.append(item)
            
     
    def __getattr__(self, name):
        """delegate not available procedures to xem"""
        if name.startswith('__') and name.endswith('__'):
            return super(DigitalLockControllerServer, self).__getattr__(name)
        def wrapper(*args):
            if self.xem:
                return getattr( self.xem, name )(*args)
            return None
        setattr(self, name, wrapper)
        return wrapper      
     
    def SetWireInValue(self, address, data):
        if self.xem:
            self.xem.SetWireInValue(address, data)

    def armScope(self):
        self.scopeEnabled = True
        if self.xem:
            self.xem.ActivateTriggerIn( 0x40, 13 )
            
    def clearIntegrator(self):
        if self.xem:
            self.xem.ActivateTriggerIn( 0x40, 5 )
        
    def setDCThreshold(self, value):
        if self.xem:
            self.xem.SetWireInValue(0x1d, value & 0xffff )
            self.xem.UpdateWireIns()
            
    def setStreamEnabled(self, enabled ):
        if self.xem:
            if enabled:
                check( self.xem.ActivateTriggerIn( 0x41, 0 ), "setStreamEnabled" )
            else:
                check( self.xem.ActivateTriggerIn( 0x41, 1 ), "setStreamEnabled" )
            logging.getLogger(__name__).warning("setStreamEnabled {0}".format(enabled))
        else:
            logging.getLogger(__name__).warning("Controller Hardware not available")
                

    def setReferenceFrequency(self, binvalue ):
        if self.xem:
            self.xem.SetWireInValue(0x00, binvalue & 0xffff )
            self.xem.SetWireInValue(0x01, (binvalue>>16) & 0xffff )
            self.xem.SetWireInValue(0x02, (binvalue>>32) & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn( 0x40, 7 )

    def setOutputFrequency(self, binvalue ):
        if self.xem:
            self.xem.SetWireInValue(0x03, binvalue & 0xffff )
            self.xem.SetWireInValue(0x04, (binvalue>>16) & 0xffff )
            self.xem.SetWireInValue(0x05, (binvalue>>32) & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn( 0x40, 8 )
    
    def setReferenceAmplitude(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x0c, binvalue & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn(0x40, 2)

    def setOutputAmplitude(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x0d, binvalue & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn(0x40, 3)
    
    def setpCoeff(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x0e, binvalue & 0xffff )
            self.xem.SetWireInValue(0x0f, (binvalue >> 16) & 0xffff )
            self.xem.UpdateWireIns()
            
    def setiCoeff(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x10, binvalue & 0xffff )
            self.xem.SetWireInValue(0x11, (binvalue>>16) & 0xffff )
            self.xem.UpdateWireIns()
    
    def setMode(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x12, binvalue & 0xffff )
            self.xem.UpdateWireIns()

    def setFilter(self, filterMode):        
        if self.xem:
            self.xem.SetWireInValue(0x1C, filterMode & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn( 0x41, 2 )            
            
    def setInputOffset(self, binvalue ):
        if self.xem:
            self.xem.SetWireInValue(0x13, binvalue & 0xffff )
            self.xem.UpdateWireIns()
        
    def setHarmonic(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x14, binvalue & 0xffff )
            self.xem.UpdateWireIns()
            
    def setFixedPointHarmonic(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x06, binvalue & 0xffff )
            binvalue >>= 16
            self.xem.SetWireInValue(0x07, binvalue & 0xffff )
            binvalue >>= 16
            self.xem.SetWireInValue(0x08, binvalue & 0xffff )
            binvalue >>= 16
            self.xem.SetWireInValue(0x09, binvalue & 0xffff )
            self.xem.UpdateWireIns()
            
    def setCoreMode(self, mode):
        if self.xem:
            self.xem.SetWireInValue(0x0a, mode & 0xffff )
            self.xem.UpdateWireIns()           
            
    def setStreamAccum(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x15, binvalue & 0xffff )
            self.xem.SetWireInValue(0x16, (binvalue>>16) & 0xffff )
            self.xem.UpdateWireIns()
    
    def setSamples(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x17, binvalue & 0xffff )
            self.xem.SetWireInValue(0x18, (binvalue>>16) & 0xffff )
            self.xem.UpdateWireIns()
    
    def setSubSample(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x19, binvalue & 0xffff )
            self.xem.UpdateWireIns()

    def setTriggerLevel(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x1a, binvalue & 0xffff )
            self.xem.UpdateWireIns()
 
    def setTriggerMode(self, binvalue):
        if self.xem:
            self.xem.SetWireInValue(0x1b, binvalue & 0xffff )
            self.xem.UpdateWireIns()

    def readStreamData(self,minbytes=4):
        if self.xem:
            self.xem.UpdateWireOuts()
            wirevalue = self.xem.GetWireOutValue(0x20)   # pipe_out_available
            byteswaiting = (wirevalue & 0x0ffe)*2
            if byteswaiting and wirevalue & 0x7000 == 0x2000:
                data = bytearray(byteswaiting)
                self.xem.ReadFromPipeOut(0xa0, data)
                overrun = (wirevalue & 0x8000)!=0
                return data, overrun
        return None, False
                        
    def readScopeData(self,minbytes=4):
        if self.xem:
            self.xem.UpdateWireOuts()
            wirevalue = self.xem.GetWireOutValue(0x21)   # pipe_out_available
            byteswaiting = (wirevalue & 0x7ffe)*2
            if byteswaiting:
                data = bytearray(byteswaiting)
                self.xem.ReadFromPipeOut(0xa1, data)
                overrun = (wirevalue & 0x8000)!=0
                return data, overrun
        return None, False
                                        
    def listBoards(self):
        xem = ok.FrontPanel()
        self.moduleCount = xem.GetDeviceCount()
        self.modules = dict()
        for i in range(self.moduleCount):
            serial = xem.GetDeviceListSerial(i)
            tmp = ok.FrontPanel()
            check( tmp.OpenBySerial( serial ), "OpenBySerial" )
            desc = self.getDeviceDescription(tmp)
            tmp = None
            self.modules[desc.identifier] = desc
        del(xem)
        if self.openModule is not None:
            self.modules[self.openModule.identifier] = self.openModule
        return self.modules
    
    def getDeviceDescription(self, xem):
        """Get informaion from an open device
        """
        desc = DeviceDescription()
        desc.serial = xem.GetSerialNumber()
        desc.identifier = xem.GetDeviceID()
        desc.major = xem.GetDeviceMajorVersion()
        desc.minor = xem.GetDeviceMinorVersion()
        desc.model = xem.GetBoardModel()
        desc.modelName = ModelStrings.get(desc.model, 'Unknown')
        return desc
        
    def renameBoard(self, serial, newname):
        tmp = ok.FrontPanel()
        tmp.OpenBySerial(serial)
        oldname = tmp.GetDeviceID()
        tmp.SetDeviceId( newname )
        tmp.OpenBySerial(serial)
        newname = tmp.GetDeviceID()
        if newname!=oldname:
            self.modules[newname] = self.modules.pop(oldname)
            
    def uploadBitfile(self, bitfile):
        logger = logging.getLogger(__name__)
        if self.xem is not None and self.xem.IsOpen():
            check( self.xem.ConfigureFPGA(bitfile), "Configure bitfile {0}".format(bitfile))
            self.xem.ActivateTriggerIn(0x41, 9)  # reset overrun
            logger.info("upload bitfile '{0}'".format(bitfile))
            logger.info(str(BitfileInfo(bitfile)))

    def openByName(self, name):
        self.xem = ok.FrontPanel()
        check( self.xem.OpenBySerial( self.modules[name].serial ), "OpenByName {0}".format(name) )
        return self.xem

    def openBySerial(self, serial):
        logger = logging.getLogger(__name__)
        if self.xem is None or not self.xem.IsOpen() or self.xem.GetSerialNumber()!=serial:
            logger.debug("Open Serial {0}".format(serial) )
            self.xem = ok.FrontPanel()
            check( self.xem.OpenBySerial( serial ), "OpenBySerial '{0}'".format(serial) )
            self.openModule = self.getDeviceDescription(self.xem)
        else:
            logger.debug("Serial {0} is already open".format(serial) )         
        return None
        
