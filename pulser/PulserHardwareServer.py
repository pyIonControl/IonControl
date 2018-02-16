# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
Encapsulation of the Pulse Programmer Hardware 
"""
import json
import logging
import math
import struct
from _collections import defaultdict
from multiprocessing import Process
from time import time as time_time

import numpy

from modules import enum
from modules.quantity import Q
from mylogging.ServerLogging import configureServerLogging
from pulser.OKBase import OKBase, check
from pulser.PulserConfig import getPulserConfiguration
from pulser.ServerProcess import ServerProcess


class PulserHardwareException(Exception):
    pass

LastTimetickCheck = 0

class Data(object):
    def __init__(self):
        self.count = defaultdict(list)       # list of counts in the counter channel
        self.timestamp = None   
        self.timestampZero = None
        self.scanvalue = None                           # scanvalue
        self.final = False
        self.other = list()
        self.overrun = False
        self.exitcode = 0
        self.dependentValues = list()                   # additional scan values
        self.evaluated = dict()
        self.result = None                              # data received in the result channels dict with channel number as key
        self.externalStatus = None
        self._creationTime = time_time()
        self.timeTick = defaultdict(list)
        self.timingViolations = None
        self.post_time = None

    @property
    def allTimeTick(self):
        all = list()
        for l in self.timeTick.values():
            all.extend(l)
        return all

    @property
    def creationTimeNs(self):
        return int(self._creationTime * 1e9)

    @property
    def creationTime(self):
        return (list(self.timeTick.values())[0]*1e-9) if self.timeTick else self._creationTime
    
    @property
    def timeinterval(self):
        return (((list(self.timeTick.values())[0][0]*1e-9), (list(self.timeTick.values())[0][-1]*1e-9)) if self.timeTick
                 else (self._creationTime, self._creationTime))
        
    def __str__(self):
        return str(len(self.count))+" "+" ".join( [str(self.count[i]) for i in range(16) ])
    
    def defaultTimestampZero(self):
        return 0
    
    def dataString(self):
        return repr(self)

    def checkTimeTick(self):
        global LastTimetickCheck
        if time_time() - LastTimetickCheck > 60:
            ct = time_time()
            for l in self.timeTick.values():
                if l:
                    LastTimetickCheck = ct
                    if abs(1e-9 * l[0] - ct) > 60:
                        logging.getLogger(__name__).warning("Timeticks differ from computer time epoch: {} timestamp: {}", ct, l[0])
                        break

    def __repr__(self):
        return json.dumps([self.count, self.timestamp, self.timestampZero, self.scanvalue, self.final, self.other,
                           self.overrun, self.exitcode, self.dependentValues, self.result, self.externalStatus,
                           self._creationTime, 0, self.timeTick])
        
    @staticmethod
    def fromJson(string):
        data = Data()
        (data.count, data.timestamp, data.timestampZero, data.scanvalue, data.final, data.other, data.overrun,
         data.exitcode, data.dependentValues, data.result, data.externalStatus, data._creationTime, _, data.timeTick) = json.loads(string)


class DedicatedData(object):
    def __init__(self):
        self.data = [None]*34
        self.externalStatus = None
        self._timestamp = time_time()
        self.maxBytesRead = 0
        
    def count(self):
        return self.data[0:15]
        
    def analog(self):
        return self.data[16:31]
        
    def integration(self):
        return self.data[32]
    
    @property
    def timestamp(self):
        return self.data[33]*1e-9 if self.data[33] else self._timestamp
    
    @timestamp.setter
    def timestamp(self, ts):
        self._timestamp = ts


class LogicAnalyzerData:
    def __init__(self):
        self.data = list()
        self.auxData = list()
        self.trigger = list()
        self.gateData = list()
        self.stopMarker = None
        self.countOffset = 0
        self.overrun = False
        self.wordcount = 0
        
    def dataToStr(self, l):
        strlist = list()
        for time, pattern in l:
            strlist.append("({0}, {1:x})".format(time, pattern))
        return "["+", ".join(strlist)+"]"
                  
    def __str__(self):
        return "data: {0} auxdata: {1} trigger: {2} gate: {3} stopMarker: {4} countOffset: {5}".format(self.dataToStr(self.data), self.dataToStr(self.auxData), self.dataToStr(self.trigger), 
                                                                                                       self.dataToStr(self.gateData), self.stopMarker, self.countOffset)


class PulserHardwareServer(ServerProcess, OKBase):
    timestep = Q(5, 'ns')
    integrationTimestep = Q(20, 'ns')
    dedicatedDataClass = DedicatedData
    def __init__(self, dataQueue=None, commandPipe=None, loggingQueue=None, sharedMemoryArray=None):
        ServerProcess.__init__(self, dataQueue, commandPipe, loggingQueue, sharedMemoryArray)
        OKBase.__init__(self)

        # PipeReader stuff
        self.state = self.analyzingState.normal
        self.data = Data()
        self.dedicatedData = self.dedicatedDataClass()
        self.timestampOffset = int(time_time() * 1e9)

        self._shutter = 0
        self._trigger = 0
        self._counterMask = 0
        self._adcMask = 0
        self._integrationTime = Q(100, 'ms')
        
        self.logicAnalyzerEnabled = False
        self.logicAnalyzerStopAtEnd = False
        self.logicAnalyzerData = LogicAnalyzerData()
        
        self.logicAnalyzerBuffer = bytearray()
        self.logicAnalyzerReadStatus = 0      #
        self._pulserConfiguration = None
        self._data_fifo_buffer = bytearray()
        
    def syncTime(self):
        if self.xem:
            self.xem.ActivateTriggerIn(0x40, 15)
            logging.getLogger(__name__).info("Time synchronized at {0}".format(time_time()))
        else:
            logging.getLogger(__name__).error("No time synchronization because FPGA is not available")
        self.timestampOffset = int(time_time() * 1e9)

    def queueData(self):
        self.data.post_time = time_time()
        self.data.checkTimeTick()
        self.dataQueue.put(self.data)
        self.data = Data()

    analyzingState = enum.enum('normal', 'scanparameter', 'dependentscanparameter')
    def readDataFifo(self):
        """ run is responsible for reading the data back from the FPGA
            0xffffffffffffffff end of experiment marker
            0xfffexxxxxxxxxxxx exitcode marker
            0xfffd000000000000 timestamping overflow marker
            0xfffcxxxxxxxxxxxx scan parameter, followed by scanparameter value
            0xfffb00000000xxxx timing was not met, xxxx address of update command whose timing could not be met
            0x01ddnnxxxxxxxxxx count result from channel n id dd
            0x02ddnnxxxxxxxxxx timestamp result channel n id dd
            0x03ddnnxxxxxxxxxx timestamp gate start channel n id dd
            0x04nnxxxxxxxxxxxx other return
            0x05nnxxxxxxxxxxxx ADC return MSB 16 bits count, LSB 32 bits sum
            0x06ddxxxxxxxxxxxx
            0xeennxxxxxxxxxxxx dedicated result
            0x50nn00000000xxxx result n return Hi 16 bits, only being sent if xxxx is not identical to zero
            0x51nnxxxxxxxxxxxx result n return Low 48 bits, guaranteed to come first
        """
        logger = logging.getLogger(__name__)
        if (self.logicAnalyzerEnabled):
            logicAnalyzerData, _ = self.ppReadLogicAnalyzerData(8)
            if self.logicAnalyzerOverrun:
                logger.warning("Logic Analyzer Pipe overrun")
                self.logicAnalyzerClearOverrun()
                self.logicAnalyzerData.overrun = True
            if logicAnalyzerData:
                self.logicAnalyzerBuffer.extend(logicAnalyzerData)
            for s in sliceview(self.logicAnalyzerBuffer, 8):
                if self.logicAnalyzerReadStatus==0:
                    (code, ) = struct.unpack('Q', s)
                    self.logicAnalyzerData.wordcount += 1
                    self.logicAnalyzerTime = (code & 0xffffff) + self.logicAnalyzerData.countOffset
                    pattern = (code >> 24) & 0xffffffff
                    header = (code >> 56 )
                    if header==2:  # overrun marker
                        self.logicAnalyzerData.countOffset += 0x1000000   # overrun of 24 bit counter
                    elif header==1:  # end marker
                        self.logicAnalyzerData.stopMarker = self.logicAnalyzerTime
                        self.dataQueue.put( self.logicAnalyzerData )
                        self.logicAnalyzerData = LogicAnalyzerData()
                    elif header==4: # trigger
                        self.logicAnalyzerReadStatus = 4
                    elif header==3: # standard
                        self.logicAnalyzerReadStatus = 3  
                    elif header==5: # aux data
                        self.logicAnalyzerReadStatus = 5
                    elif header==6:
                        self.logicAnalyzerReadStatus = 6
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Time {0:x} header {1} pattern {2:x} {3:x} {4:x}".format(self.logicAnalyzerTime, header, pattern, code, self.logicAnalyzerData.countOffset))
                elif self.logicAnalyzerReadStatus==3:
                    (pattern, ) = struct.unpack('Q', s) 
                    self.logicAnalyzerData.data.append( (self.logicAnalyzerTime, pattern) )
                    self.logicAnalyzerReadStatus = 0
                elif self.logicAnalyzerReadStatus==4:
                    (pattern, ) = struct.unpack('Q', s) 
                    self.logicAnalyzerData.trigger.append( (self.logicAnalyzerTime, pattern) )
                    self.logicAnalyzerReadStatus = 0
                elif self.logicAnalyzerReadStatus==5:
                    (pattern, ) = struct.unpack('Q', s) 
                    self.logicAnalyzerData.auxData.append( (self.logicAnalyzerTime, pattern))
                    self.logicAnalyzerReadStatus = 0
                elif self.logicAnalyzerReadStatus==6:
                    (pattern, ) = struct.unpack('Q', s) 
                    self.logicAnalyzerData.gateData.append( (self.logicAnalyzerTime, pattern) )
                    self.logicAnalyzerReadStatus = 0
            self.logicAnalyzerBuffer = bytearray( sliceview_remainder(self.logicAnalyzerBuffer, 8) )           

                   
        data, self.data.overrun, self.data.externalStatus = self.ppReadWriteData(8)
        self.dedicatedData.externalStatus = self.data.externalStatus
        self.dedicatedData.maxBytesRead = max(self.dedicatedData.maxBytesRead, len(data) if data else 0)
        if data:
            for s in sliceview(data, 8):
                (token,) = struct.unpack('Q', s)
                #print(hex(token))
                if self.state == self.analyzingState.dependentscanparameter:
                    self.data.dependentValues.append(token)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug( "Dependent value {0} received".format(token) )
                    self.state = self.analyzingState.normal
                elif self.state == self.analyzingState.scanparameter:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug( "Scan value {0} received".format(token) )
                    if self.data.scanvalue is None:
                        self.data.scanvalue = token
                    else:
                        self.queueData()
                        self.data.scanvalue = token
                    self.state = self.analyzingState.normal
                elif token & 0xff00000000000000 == 0xee00000000000000: # dedicated results
                    try:
                        channel = (token >>48) & 0xff
                        if self.dedicatedData.data[channel] is not None:
                            self.dataQueue.put( self.dedicatedData )
                            self.dedicatedData = self.dedicatedDataClass()
                        if channel==33:
                            self.dedicatedData.data[channel] = (token & 0xffffffffff) * 5 + self.timestampOffset
                        else:
                            self.dedicatedData.data[channel] = token & 0xffffffffffff
                    except IndexError:
                        pass
                        #logger.debug("dedicated {0} {1}".format(channel, token & 0xffffffffffff))
                elif token & 0xff00000000000000 == 0xff00000000000000:
                    if token == 0xffffffffffffffff:    # end of run
                        self.data.final = True
                        self.data.exitcode = 0x0000
                        self.queueData()
                        logger.info( "End of Run marker received" )
                    elif token & 0xffff000000000000 == 0xfffe000000000000:  # exitparameter
                        self.data.final = True
                        self.data.exitcode = token & 0x0000ffffffffffff
                        logger.info( "Exitcode {0:x} received".format(self.data.exitcode) )
                        self.queueData()
                    elif token == 0xfffd000000000000:
                        self.timestampOffset += 5 * (1 << 40)
                    elif token & 0xffff000000000000 == 0xfffc000000000000:  # new scan parameter
                        self.state = self.analyzingState.dependentscanparameter if (token & 0x8000 == 0x8000) else self.analyzingState.scanparameter 
                    elif token & 0xffff000000000000 == 0xfffb000000000000:
                        if self.data.timingViolations is None:
                            self.data.timingViolations = list()
                        self.data.timingViolations.append( token & 0xffff )
                else:
                    key = token >> 56 
                    #print("token", hex(token))
                    if key==1:   # count
                        channel = (token >>40) & 0xffff 
                        value = token & 0x000000ffffffffff
                        (self.data.count[ channel ]).append(value)
                    elif key==2:  # timestamp
                        channel = (token >>40) & 0xffff 
                        value = (token & 0x000000ffffffffff) * 5
                        if self.data.timestamp is None:
                            self.data.timestamp = defaultdict(list)
                        try:
                            self.data.timestamp[channel][-1].append(self.timestampOffset + value - self.data.timestampZero[channel][-1])
                        except IndexError:
                            logger.error("channel: {}".format(channel))
                            logger.error("timestampZero: {}".format(self.data.timestampZero))
                            logger.error("timestamp: {}".format(self.data.timestamp))
                            raise
                    elif key==3:  # timestamp gate start
                        channel = (token >>40) & 0xffff 
                        value = (token & 0x000000ffffffffff) * 5
                        if self.data.timestampZero is None:
                            self.data.timestampZero = defaultdict(list)
                        self.data.timestampZero[channel].append(self.timestampOffset + value)
                        if self.data.timestamp is None:
                            self.data.timestamp = defaultdict(list)
                        self.data.timestamp[channel].append(list())
                    elif key==4: # other return value
                        channel = (token >>40) & 0xffff 
                        value = token & 0x000000ffffffffff
                        self.data.other.append(value)
                    elif key==5: # ADC return
                        channel = (token >>40) & 0xffff
                        sumvalue = token & 0xfffffff
                        count = (token >> 28) & 0xfff
                        if count>0:
                            self.data.count[channel + 32].append( sumvalue/float(count)  )
                    elif key==6: # clock timestamp
                        self.data.timeTick[(token>>40) & 0xff].append(self.timestampOffset + (token & 0xffffffffff) * 5)
                    elif key==0x51:
                        channel = (token >>48) & 0xff 
                        value = token & 0x0000ffffffffffff
                        if self.data.result is None:
                            self.data.result = defaultdict(list)
                        self.data.result[channel].append( value  )
                    elif key==0x50:
                        channel = (token >>48) & 0xff 
                        value = (token & 0x000000000000ffff) << 48 | self.data.result[channel][-1]
                        if value & 0x8000000000000000:
                            value -= 0x10000000000000000
                        self.data.result[channel][-1] = value
#                  logger.debug("result key: {0} hi-low: {1} value: {2} length: {3} value: {4}".format(resultkey,channel,value&0xffff,len(self.data.result[resultkey]),self.data.result[resultkey][-1]))
                    else:
                        self.data.other.append(token)
            if self.data.overrun:
                logger.info( "Overrun detected, triggered data queue" )
                self.queueData()
                self.clearOverrun()
                
            
     
    def __getattr__(self, name):
        """delegate not available procedures to xem"""
        if name.startswith('__') and name.endswith('__'):
            return super(PulserHardwareServer, self).__getattr__(name)
        def wrapper(*args):
            if self.xem:
                return getattr( self.xem, name )(*args)
            return None
        setattr(self, name, wrapper)
        return wrapper      
     
    def openBySerial(self, serial ):
        super(PulserHardwareServer, self).openBySerial(serial)
        self.syncTime()
        self.ppClearReadFifo()  # clear all read data to make sure there is no time counter wraparound
     
    def getShutter(self):
        return self._shutter  #
         
    def setShutter(self, value):
        if self.xem:
            data = bytearray(struct.pack('=HQ', 0x10, value))
            self.xem.WriteToPipeIn(0x84, data )
            self._shutter = value
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
        return self._shutter
            
    def setShutterBit(self, bit, value):
        mask = 1 << bit
        newval = (self._shutter & (~mask)) | (mask if value else 0)
        return self.setShutter( newval )
        
    def getTrigger(self):
        return self._trigger
            
    def setExtendedWireIn(self, address, value ):
        if self.xem:
            self.xem.WriteToPipeIn(0x84, bytearray(struct.pack('=HQ' if value>0 else '=Hq', address, value)) )
            logging.getLogger(__name__).debug("Writing Extended wire {0} value {1} {2}".format(address, value, hex(value)))
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")

    def setMultipleExtendedWireIn(self, items):
        if self.xem:
            writebuffer = bytearray()
            for address, value in items:
                writebuffer.extend(bytearray(struct.pack('=HQ' if value>0 else '=Hq', address, value)))
            self.xem.WriteToPipeIn(0x84, writebuffer)
            logging.getLogger(__name__).debug("Writing All Extended wire values")
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")

    def setTrigger(self, value):
        if self.xem:
            self.xem.WriteToPipeIn(0x84, bytearray(struct.pack('=HQ', 0x11, value)) )
            self._trigger = value
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
        return self._trigger
            
    def getCounterMask(self):
        return self._counterMask 
        
    def setCounterMask(self, value):
        if self.xem:
            self._counterMask = (value & 0xffff)
            self.setExtendedWireIn(0x1d, self._counterMask)
            logging.getLogger(__name__).info( "set counterMask {0}".format( hex(self._counterMask) ) )
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
        return self._counterMask 

    def getAdcMask(self):
        return self._adcMask 
        
    def setAdcMask(self, value):
        if self.xem:
            self._adcMask = value & 0xffff
            self.setExtendedWireIn(0x1c, self._adcMask)
            logging.getLogger(__name__).info( "set adc mask {0}".format(hex(self._adcMask)) )
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
        return self._adcMask
        
    def getIntegrationTime(self):
        return self._integrationTime
        
    def setIntegrationTime(self, value):
        self.integrationTimeBinary = int(value / self.integrationTimestep)
        if self.xem:
            logging.getLogger(__name__).info(  "set dedicated integration time {0} {1}".format( value, self.integrationTimeBinary ) )
            self.setExtendedWireIn(0x1b, self.integrationTimeBinary)
            self._integrationTime = value
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
        return self.integrationTimeBinary
            
    def getIntegrationTimeBinary(self, value):
        return int(round(float(value / self.integrationTimestep))) & 0xffffffff
    
    def ppUpload(self, xxx_todo_changeme, codestartaddress=0, datastartaddress=0 ):
        (code, data) = xxx_todo_changeme
        self.ppUploadCode(code, codestartaddress)
        self.ppUploadData(data, datastartaddress)
        
    def ppUploadCode(self,binarycode,startaddress=0):
        if self.xem:
            logger = logging.getLogger(__name__)
            logger.info( "PP Code segment uses {0} / {1} words {2:.0f} %".format(len(binarycode)/4, 4095, len(binarycode)/4/40.95))
            if len(binarycode)/4 > self._pulserConfiguration.commandMemorySize - 1:
                raise PulserHardwareException("Code segment exceeds 4095 words ({0})".format(len(binarycode)/4))
            logger.info(  "starting PP Code upload" )
            check( self.xem.SetWireInValue(0x00, startaddress, 0x0FFF), "ppUpload write start address" )	# start addr at zero
            self.xem.UpdateWireIns()
            check( self.xem.ActivateTriggerIn(0x41, 1), "ppUpload trigger" )
            logger.info(  "{0} bytes".format(len(binarycode)) )
            num = self.xem.WriteToPipeIn(0x83, bytearray(binarycode) )
            check(num, 'Write to program pipe' )
            logger.info(   "uploaded pp file {0} bytes".format(num) )
            num, data = self.ppDownloadCode(0, num)
            logger.info(   "Verified {0} bytes. {1}".format(num, data==binarycode) )
            return True
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return False
            
    def ppDownloadCode(self, startaddress, length):
        if self.xem:
            self.xem.SetWireInValue(0x00, startaddress, 0x0FFF)	# start addr at 3900
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn(0x41, 0)
            self.xem.ActivateTriggerIn(0x41, 1)
            data = bytearray(b'\000'*length)
            num = self.xem.ReadFromPipeOut(0xA4, data)
            return num, data
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return 0, None

    def ppUploadData(self, binarydata,startaddress=0):
        if self.xem:
            logger = logging.getLogger(__name__)
            logger.info( "PP Data segment uses {0} / {1} words ( {2:.0f} % )".format(len(binarydata)/8, 4095, len(binarydata)/8/40.95))
            if len(binarydata)/8 > self._pulserConfiguration.dataMemorySize:
                raise PulserHardwareException("Code segment exceeds 4095 words ({0})".format(len(binarydata)/8))
            logger.info(  "starting PP Datasegment upload" )
            check( self.xem.SetWireInValue(0x00, startaddress, 0x0FFF), "ppUpload write start address" )    # start addr at zero
            self.xem.UpdateWireIns()
            check( self.xem.ActivateTriggerIn(0x41, 10), "ppUpload trigger" )
            logger.info(  "{0} bytes".format(len(binarydata)) )
            num = self.xem.WriteToPipeIn(0x80, bytearray(binarydata) )
            check(num, 'Write to program pipe' )
            logger.info(   "uploaded pp file {0} bytes".format(num) )
            num, data = self.ppDownloadData(0, num)
            logger.info(   "Verified {0} bytes. {1}".format(num, data==binarydata) )
            return True
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return False
        
    def ppDownloadData(self, startaddress, length):
        if self.xem:
            self.xem.SetWireInValue(0x00, startaddress, 0x0FFF)    # start addr at 3900
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn(0x41, 0)
            self.xem.ActivateTriggerIn(0x41, 10)
            data = bytearray(b'\000'*length)
            num = self.xem.ReadFromPipeOut(0xA0, data)
            return num, data
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return 0, None
        
    def ppIsRunning(self):
        if self.xem:
            data = b'\x00'*32
            self.xem.ReadFromPipeOut(0xA1, data)
            if ((data[:2] != b'\xED\xFE') or (data[-2:] != b'\xED\x0F')):
                logging.getLogger(__name__).warning( "Bad data string: {0}".format( list(map(ord, data)) ) )
                return True
            data = list(map(ord, data[2:-2]))
            #Decode
            active =  bool(data[1] & 0x80)
            return active
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return False
            

    def ppReset(self):#, widget = None, data = None):
        if self.xem:
            self.xem.ActivateTriggerIn(0x40, 0)
            self.xem.ActivateTriggerIn(0x41, 0)
            logging.getLogger(__name__).warning( "pp_reset is not working right now... CWC 08302012" )
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")

    def ppStart(self):#, widget = None, data = None):
        if self.xem:
            self.xem.ActivateTriggerIn(0x40, 3)  # pp_stop_trig
            self.xem.ActivateTriggerIn(0x41, 4)  # clear fifo
            self.xem.ActivateTriggerIn(0x41, 9)  # reset overrun
            self.readDataFifo()
            self.readDataFifo()   # after the first time the could still be data in the FIFO not reported by the fifo count
            self.data = Data()    # flush data that might have been accumulated
            logging.getLogger(__name__).debug("Sending start trigger")
            self.xem.ActivateTriggerIn(0x40, 2)  # pp_start_trig
            return True
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return False

    def ppStop(self):#, widget, data= None):
        if self.xem:
            self.xem.ActivateTriggerIn(0x40, 3)  # pp_stop_trig
            return True
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return False

    def ppInterrupt(self):
        """Set a stop flag for the pulse program. The prepare_next_scan_point() function will then exit
        with exitrcode 0xfffe100000000000 to signal an interrupt"""
        self.xem.ActivateTriggerIn( 0x40, 14 )

    def interruptRead(self):
        self.sleepQueue.put(False)

    def ppWriteData(self, data):
        """Write data to the FPGA input fifo"""
        if self.xem:
            if isinstance(data, bytearray):
                return self.xem.WriteToPipeIn(0x81, data)
            else:
                code = bytearray()
                for item in data:
                    code.extend(struct.pack('Q' if item>0 else 'q', item))
                #print "ppWriteData length",len(code)
                return self.xem.WriteToPipeIn(0x81, code)
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return None

    def ppWriteDataBuffered(self, data):
        if self.xem:
            if isinstance(data, bytearray):
                self._data_fifo_buffer.extend(data)
            else:
                code = bytearray()
                for item in data:
                    code.extend(struct.pack('Q' if item>0 else 'q', item))
                self._data_fifo_buffer.extend(code)
            self.readDataFifo()  # This makes sure data is written before we return
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return None

    def _write_buffer(self, min_words=512):
        """Write data from the buffer to the fifo if there is space available"""
        if self._data_fifo_buffer:
            write_count = 2040 - (self.xem.GetWireOutValue(0x26) >> 2)  # number of 64 bit words that can be written to data fifo
            if write_count > min_words:
                do_write_count = min(len(self._data_fifo_buffer), 8*write_count)
                self.xem.WriteToPipeIn(0x81, self._data_fifo_buffer[:do_write_count])
                self._data_fifo_buffer = self._data_fifo_buffer[do_write_count:]
                logger = logging.getLogger(__name__)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("_write_buffer wrote {} bytes {} remaining".format(do_write_count, len(self._data_fifo_buffer)))

    def ppReadWriteData(self, minbytes=8, minwrite=512):
        if self.xem:
            self.xem.UpdateWireOuts()
            self._write_buffer(minwrite)
            wirevalue = self.xem.GetWireOutValue(0x25)   # pipe_out_available
            byteswaiting = (wirevalue & 0x1ffe)*2
            externalStatus = self.xem.GetWireOutValue(0x30) | (self.xem.GetWireOutValue(0x31) << 16)
            if byteswaiting:
                data = bytearray(byteswaiting)
                self.xem.ReadFromPipeOut(0xa2, data)
                overrun = (wirevalue & 0x4000)!=0
                return data, overrun, externalStatus
            return None, False, externalStatus
        return None, False, None
                        
    def ppReadLogicAnalyzerData(self,minbytes=8):
        if self.xem:
            self.xem.UpdateWireOuts()
            wirevalue = self.xem.GetWireOutValue(0x27)   # pipe_out_available
            byteswaiting = (wirevalue & 0x1ffe)*2
            self.logicAnalyzerOverrun = (wirevalue & 0x4000) == 0x4000
            if byteswaiting:
                data = bytearray(byteswaiting)
                self.xem.ReadFromPipeOut(0xa1, data)
                overrun = (wirevalue & 0x4000)!=0
                return data, overrun
        return None, False
                        
    def wordListToBytearray(self, wordlist):
        """ convert list of words to binary bytearray
        """
        return bytearray(numpy.array(wordlist, dtype=numpy.int64).view(dtype=numpy.int8))

    def bytearrayToWordList(self, barray):
        return list(numpy.array( barray, dtype=numpy.int8).view(dtype=numpy.int64 ))
            
    def ppWriteRam(self, data, address):
        if self.xem:
            appendlength = int(math.ceil(len(data)/128.))*128 - len(data)
            data += bytearray([0]*appendlength)
            logging.getLogger(__name__).info( "set write address {0}".format(address) )
            self.xem.SetWireInValue( 0x01, address & 0xffff )
            self.xem.SetWireInValue( 0x02, (address >> 16) & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn( 0x41, 6 ) # ram set wwrite address
            return self.xem.WriteToPipeIn( 0x82, data )
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return None
            
    def ppReadRam(self, data, address):
        if self.xem:
#           print "set read address"
            self.xem.SetWireInValue( 0x01, address & 0xffff )
            self.xem.SetWireInValue( 0x02, (address >> 16) & 0xffff )
            self.xem.UpdateWireIns()
            self.xem.ActivateTriggerIn( 0x41, 7 ) # Ram set read address
            self.xem.ReadFromPipeOut( 0xa3, data )
#           print "read", len(data)
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            
    quantum = 1024*1024
    def ppWriteRamWordList(self, wordlist, address):
        logger = logging.getLogger(__name__)
        data = self.wordListToBytearray(wordlist)
        for start in range(0, len(data), self.quantum ):
            self.ppWriteRam( data[start:start+self.quantum], address+start)
        matches = True
        myslice = bytearray(self.quantum)
        for start in range(0, len(data), self.quantum ):
            self.ppReadRam(myslice, address+start)
            length = min(self.quantum, len(data)-start)
            matches = matches and data[start:start+self.quantum] == myslice[:length]
        logger.info( "ppWriteRamWordList {0}".format( len(data)) )
        if not matches:
            logger.warning( "Write unsuccessful data does not match write length {0} read length {1}".format(len(data), len(data)))
            raise PulserHardwareException("RAM write unsuccessful")

    def ppReadRamWordList(self, wordlist, address):
        data = bytearray(len(wordlist) * 8)
        myslice = bytearray(self.quantum)
        for start in range(0, len(data), self.quantum ):
            length = min(self.quantum, len(data)-start )
            self.ppReadRam(myslice, address+start)
            data[start:start+length] = myslice[:length]
        wordlist[:] = self.bytearrayToWordList(data)
        return wordlist

    def ppWriteRamWordListShared(self, length, address, check=True):
        #self.ppWriteRamWordList(self.sharedMemoryArray[:length], address)
        logger = logging.getLogger(__name__)
        data = self.wordListToBytearray(self.sharedMemoryArray[:length])
        #logger.debug( "write {0}".format([hex(int(d)) for d in data[0:100]]) )
        self.ppWriteRam( data, address)
        if check:
            myslice = bytearray(len(data))
            self.ppReadRam(myslice, address)
            #logger.debug( "read {0}".format([hex(int(d)) for d in myslice[0:100]]) )
            matches = data == myslice
            logger.info( "ppWriteRamWordList {0}".format( len(data)) )
            if not matches:
                logger.warning( "Write unsuccessful data does not match write length {0} read length {1}".format(len(data), len(data)))
                raise PulserHardwareException("RAM write unsuccessful")
                
    def ppReadRamWordListShared(self, length, address):
        data = bytearray([0]*length*8)
        self.ppReadRam(data, address)
        self.sharedMemoryArray[:length] = self.bytearrayToWordList(data)
        return True

    def ppClearWriteFifo(self):
        if self.xem:
            self._data_fifo_buffer = bytearray()
            self.xem.ActivateTriggerIn(0x41, 3)
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            
    def ppFlushData(self):
        if self.xem:
            self.data = Data()
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
        return None

    def ppClearReadFifo(self):
        if self.xem:
            self.xem.ActivateTriggerIn(0x41, 4)
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            
    def ppReadLog(self):
        if self.xem:
            #Commented CWC 04032012
            data = bytearray(32)
            self.xem.ReadFromPipeOut(0xA1, data)
            with open(r'debug\log', 'wb') as f:
                f.write(data)
            return data
        else:
            logging.getLogger(__name__).warning("Pulser Hardware not available")
            return None
        
        
    def enableLogicAnalyzer(self, enable):
        if enable != self.logicAnalyzerEnabled:
            self.logicAnalyzerEnabled = enable
            if enable:
                if self.xem:
                    self.xem.SetWireInValue(0x0d, 1, 0x01)    # set logic analyzer enabled
                    self.xem.UpdateWireIns()
            else:
                if self.xem:
                    self.xem.SetWireInValue(0x0d, 0, 0x01)    # set logic analyzer disabled
                    self.xem.UpdateWireIns()
                    
    def logicAnalyzerTrigger(self):
        self.logicAnalyzerEnabled = True
        self.logicAnalyzerStopAtEnd = True
        if self.xem:
            self.xem.ActivateTriggerIn( 0x40, 12 ) # Ram set read address

    def logicAnalyzerClearOverrun(self):
        if self.xem:
            self.xem.ActivateTriggerIn( 0x40, 10 ) # Ram set read address
            
    def clearOverrun(self):
        if self.xem:
            self.xem.ActivateTriggerIn(0x41, 9)  # reset overrun
            
    def uploadBitfile(self, bitfile):
        OKBase.uploadBitfile(self, bitfile)
        self.syncTime()
        self.ppClearReadFifo()  # clear all read data to make sure there is no time counter wraparound

    def getOpenModule(self):
        return self.openModule

    def pulserConfiguration(self, configfile=None, hardwareId=None):
        if configfile is not None:
            pulserConfigurationList = getPulserConfiguration(configfile)
            hardwareId = self.hardwareConfigurationId() if hardwareId is None else hardwareId
            if hardwareId in pulserConfigurationList:
                self._pulserConfiguration = pulserConfigurationList[hardwareId]
                return self._pulserConfiguration
            else:
                raise PulserHardwareException("No information on configuration 0x{0:x} in configuration file '{1}'".format(hardwareId, configfile))
            return None
        return self._pulserConfiguration


def sliceview(view, length):
    for i in range(0, len(view) - length + 1, length):
        yield memoryview(view)[i:i + length]


def sliceview_remainder(view, length):
    l = len(view)
    full_items = l // length
    appendix = l - length * full_items
    return memoryview(view)[l - appendix:]
