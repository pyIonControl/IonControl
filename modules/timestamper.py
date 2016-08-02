# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import queue
import copy
import logging
import math
import struct
import sys

from PyQt5.QtCore import QMutex
from PyQt5.QtCore import QMutexLocker
from PyQt5.QtCore import QThread
from PyQt5.QtGui import QApplication
import crcmod   #@UnresolvedImport @UnusedImport
import crcmod.predefined #@UnresolvedImport @UnusedImport
import ftd2xx #@UnresolvedImport
import numpy


MessageQueue = queue.Queue()
clockfrequency = 50000000.0
clockcycle = 1000./clockfrequency

class Status():
    def __init__(self):
        self.goodcrc = 0
        self.badcrc = 0
        self.triggercount = 0
        self.photoncount = 0
        self.triggerrate = 0
        self.photonrate = 0
        self.lastratetime = 0
        self.lasttriggercount = 0
        self.lastphotoncount = 0
        
    def updateRate(self, now):
        self.photonrate = (self.photoncount - self.lastphotoncount)*clockfrequency/(now-self.lastratetime)
        self.triggerrate = (self.triggercount - self.lasttriggercount)*clockfrequency/(now-self.lastratetime)
        self.lastphotoncount = self.photoncount
        self.lasttriggercount = self.triggercount
        self.lastratetime = now


class TimestampWorker(QThread):
   
    def __init__(self, countchannel, triggerchannel, binwidth, roistart, roistop, filename=None, parent = None, FPGASerial="A6VTOYBO"):
        QThread.__init__(self, parent)
        self.channel = countchannel
        self.triggerchannel = triggerchannel
        self.binwidth = binwidth
        self.roistart = roistart
        self.roistop = roistop
        self.numberOfBins = (roistop-roistart)/binwidth+1
        self.histogram = numpy.zeros(self.numberOfBins)
        self.exiting = False
        self.crc8 = crcmod.mkCrcFun(poly=0x107, initCrc=0xff, xorOut=0x00, rev=False)
        self.Connection = ftd2xx.openEx(FPGASerial);
        self.Connection.setBaudRate(3000000)
        self.Connection.setDataCharacteristics(8, 0, 0)
        self.Connection.setFlowControl(0, 0, 0)
        self.Connection.setTimeouts(500, 500)
        self.Connection.resetDevice()
        self.Connection.purge()
        self.integration_time = 100.0;
        command = struct.pack('>BBBI', 0x10, 0, 0x11, int(500*50000 )  )
        self.Connection.write(command)    
        command = struct.pack('>BB', 0x12, 0x0  )
        self.Connection.write(command)    
        self.Mutex = QMutex()
        self.filename = filename
        self.binfile = None
        if self.filename is not None:
            self.binfile = open(self.filename, 'wb')
        self.clearStatus()
        self.maxPretriggerPhotons = 1000000
            
    def sendCommand(self, command):
        with QMutexLocker(self.Mutex):
            self.Connection.write(command)
            
    def clearStatus(self):            
        # status information
        self.status = Status()
        
    def readHistogram(self):
        with QMutexLocker(self.Mutex):
            histcopy = numpy.copy(self.histogram)
        return histcopy
        
    def readStatus(self):
        with QMutexLocker(self.Mutex):
            statuscopy = copy.deepcopy( self.status )
        return statuscopy
        
    def quitThread(self):
        with QMutexLocker(self.Mutex):
            self.exiting = True

    def startRecording(self):
        logger = logging.getLogger(__name__)
        with QMutexLocker(self.Mutex):
            logger.info( "command {0:x}".format(0xff & ( 1<<self.channel | 1<<self.triggerchannel)) )
            command = struct.pack('>BB', 0x12, 0xff & ( 1<<self.channel | 1<<self.triggerchannel)  )
            self.Connection.write(command)    

    def startNewRecording(self, countchannel, triggerchannel, binwidth, roistart, roistop, filename=None):
        logger = logging.getLogger(__name__)
        with QMutexLocker(self.Mutex):
            command = struct.pack('>BB', 0x12, 0  )
            self.Connection.write(command)    
            self.channel = countchannel
            self.triggerchannel = triggerchannel
            self.binwidth = binwidth
            self.roistart = roistart
            self.roistop = roistop
            self.numberOfBins = (roistop-roistart)/binwidth+1
            self.histogram = numpy.zeros(self.numberOfBins)
            logger.info( "command {0:x}".format(0xff & ( 1<<self.channel | 1<<self.triggerchannel)) )
            self.clearStatus()
            command = struct.pack('>BB', 0x12, 0xff & ( 1<<self.channel | 1<<self.triggerchannel)  )
            self.Connection.write(command)
            if self.filename!=filename:
                if self.binfile is not None:
                    self.binfile.close()
                if filename is not None:
                    self.binfile = open(filename, 'wb')
                else:
                    self.binfile = None
            self.filename =  filename
            
        
    def stopRecording(self):
        with QMutexLocker(self.Mutex):
            command = struct.pack('>BB', 0x12, 0  )
            self.Connection.write(command)   
            if self.binfile is not None:
                self.binfile.close()
                self.binfile = None

        
    def clear(self):
        with QMutexLocker(self.Mutex):
            self.histogram = numpy.zeros(self.numberOfBins)
            self.clearStatus()

    def __del__(self):    
        self.exiting = True
        self.Connection.close()
        self.wait()
        
    def histadd(self, delta):
        logger = logging.getLogger(__name__)
        try:
            self.histogram[(delta-self.roistart)/self.binwidth] += 1
        except:
            logger.debug( "out of range" )

    def run(self):
        try:
            triggertime = None            
            data = str()
            pretriggerphotons = list()
            timeoffset = 0
            while not self.exiting:
                status = self.Connection.getStatus()
                newdata = self.Connection.read( max(status[0], 500) )
                if self.binfile is not None:
                    self.binfile.write(newdata)
                data += newdata
                with QMutexLocker(self.Mutex):
                    while len(data)>=5:
                        result, thisdata, data = struct.unpack(">LB", data[:5]), data[:4], data[5:]
                        if (self.crc8(thisdata)==result[1]):
                            self.status.goodcrc += 1
                            counter = (result[0]>>24)
                            newtime = (result[0]& 0xffffff ) + timeoffset
                            if (counter==0xff):
                                timeoffset += 0x1000000
                                newtime = (result[0]& 0xffffff ) + timeoffset
                            elif (counter==(0x80 | self.triggerchannel)):
                                triggertime = newtime
                                self.status.triggercount += 1
                                for oldtime in pretriggerphotons:
                                    if (oldtime-triggertime>self.roistart):
                                        self.histadd(oldtime-triggertime)
                                pretriggerphotons = list()
                            elif (counter==(0x80 |self.channel)):
                                self.status.photoncount += 1
                                if (triggertime is not None) and (newtime<triggertime+self.roistop):
                                    if newtime>triggertime+self.roistart:
                                        self.histadd(newtime-triggertime)
                                else:
                                    if (len(pretriggerphotons)<self.maxPretriggerPhotons):
                                        pretriggerphotons.append(newtime)
                            if newtime > self.status.lastratetime + clockfrequency:
                                self.status.updateRate(newtime)
                        else:  # badcrc
                            self.status.badcrc += 1
                            data = data[1:]
            logging.getLogger(__name__).info( "Worker Thread done." )
        except Exception as err:
            logging.getLogger(__name__).exception( "Worker Thread", err )



class timestamper:
    def __init__(self, countchannel, triggerchannel, binwidth, roistart, roistop, filename=None, parent = None, FPGASerial="A6VTOYBO" ):
        logger = logging.getLogger(__name__)
        self.clockstep = 0.000020    # 1/50MHz in ms
        self.channel = countchannel
        self.triggerchannel = triggerchannel
        self.binwidth = binwidth
        self.qbinwidth = math.ceil(binwidth/self.clockstep)
        self.roistart = roistart
        self.qroistart = math.ceil(roistart/self.clockstep)
        self.roistop = roistop
        self.qroistop = math.ceil(roistop/self.clockstep)
        self.worker = TimestampWorker(countchannel, triggerchannel, self.qbinwidth, self.qroistart, self.qroistop, 
                                      filename=filename, parent=parent, FPGASerial=FPGASerial )
        self.worker.start()
        logger.info( "Worker start called." )
        
    def readXValues(self):
        return numpy.arange(self.qroistart*self.clockstep, self.qroistop*self.clockstep, self.qbinwidth*self.clockstep)        
        
    def readStatus(self):
        return self.worker.readStatus()
        
    def readHistogram(self):
        return self.worker.readHistogram()
        
    def startRecording(self):
        self.worker.startRecording()
        
    def stopRecording(self):
        self.worker.stopRecording()
        
    def sendCommand(self, command):
        self.worker.sendCommand(command)
        
    def startNewRecording(self, countchannel, triggerchannel, binwidth, roistart, roistop, filename=None ):
        self.channel = countchannel
        self.triggerchannel = triggerchannel
        self.binwidth = binwidth
        self.qbinwidth = math.ceil(binwidth/self.clockstep)
        self.roistart = roistart
        self.qroistart = math.ceil(roistart/self.clockstep)
        self.roistop = roistop
        self.qroistop = math.ceil(roistop/self.clockstep)
        self.worker.startNewRecording(countchannel, triggerchannel, self.qbinwidth, self.qroistart, self.qroistop, 
                                      filename=filename)
        
    def clear(self):
        self.worker.clear()
        
    def stop(self):
        self.worker.quitThread()
        
    def wait(self,time=0xFFFFFFFF):
        return self.worker.wait(time)
        
    def __del__(self):
        self.worker.quitThread()
                
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ts = timestamper(1, 4, 0.05, -2, 5)
    app.exec_()

    