#!/usr/bin/python
#-*- coding: latin-1 -*-
"""High level interface to Andor iXon+ emCCD camera."""

import numpy
from ctypes import *
from time import *
import time
import os


dllpath = os.path.join(os.path.dirname(__file__), '..', 'Camera/atmcd64d')
#print(dllpath)
windll.LoadLibrary(dllpath)
#hack to releas GIL during wait
# MVll = ctypes.windll.mvDeviceManager
# llWait = MVll.DMR_ImageRequestWaitFor
# llWait.argtypes = [ctypes.c_int,
                   # ctypes.c_int,
                   # ctypes.c_int,
                   # ctypes.POINTER(ctypes.c_int)]
# llWait.restype = ctypes.c_int
#


class CamTimeoutError(Exception):
    def __init__(self):
        super(CamTimeoutError, self).__init__(self, 'Timeout')

class TimeoutError(Exception):
    def __init__(self):
        Exception.__init__(self, 'Timeout')

class Cam(object):

    def __init__(self):
        self.andormode='live'
        self.width=0
        self.height=0
        windll.atmcd64d.Initialize(".")
        camsn = c_long()
        windll.atmcd64d.GetCameraSerialNumber(byref(camsn))
        if camsn.value == 0:
            self.error = True
            print("Andor not available Cam")
        else:
            self.error = False
            print("Andor initialized")
            print('Andor camera s/n:', camsn.value)

    def open(self):
        print('Andor open')
        windll.atmcd64d.SetTriggerMode(1) #external
        windll.atmcd64d.SetReadMode(4) #read images
        windll.atmcd64d.SetShutter(1,1,1000,1000)
        return self

    def close(self):
        print('Andor close')

    def shutdown(self):
        windll.atmcd64d.ShutDown()
        print('Andor shutdown')
        
    def stop(self):
        print('Andor stop')
        windll.atmcd64d.AbortAcquisition()
        windll.atmcd64d.SetShutter(1,0,1000,1000)
        
    def gettemperature(self):
        temperature=c_float()
        windll.atmcd64d.GetTemperatureF(byref(temperature))
        return temperature.value
        
    def wait(self, timeout=10):
        status = c_int()
        currentnumberimages = c_int()
        windll.atmcd64d.GetTotalNumberImagesAcquired(byref(currentnumberimages))
        print("currentnumberimages = ", currentnumberimages.value)
        time.sleep(0.5)#--------------------------------#
        if self.andormode == 'absorption3' or self.andormode == 'live':
            if currentnumberimages.value != self.numberandorimages:
                print('Image #', currentnumberimages.value)
                self.numberandorimages = currentnumberimages.value
            else:
                raise CamTimeoutError
        if self.andormode == 'TriggeredAcquisition':
            windll.atmcd64d.GetStatus(byref(status))
            print("status = ", status.value)
            if status.value == 20073:
                self.numberandorimages = currentnumberimages.value
                sleep(0.2)
            else:
                raise CamTimeoutError

    def start_cooling(self):
        tmin=c_int()
        tmax=c_int()
        windll.atmcd64d.GetTemperatureRange(byref(tmin),byref(tmax))
        windll.atmcd64d.SetTemperature(tmin.value)
        windll.atmcd64d.CoolerON()
        print("Andor start cooling")
        print('  set min temp = ', tmin.value)
        
    def stop_cooling(self):
        windll.atmcd64d.CoolerOFF()
        print("Andor stop cooling")
        #print '  temp = ', self.gettemperature()
    
    def frame_height(self):
        xsize = c_long()
        ysize = c_long()
        windll.atmcd64d.GetDetector(byref(xsize),byref(ysize))
        return ysize.value

    def frame_width(self):
        xsize = c_long()
        ysize = c_long()
        windll.atmcd64d.GetDetector(byref(xsize),byref(ysize))
        return xsize.value

    def set_timing(self, integration=100,
                   repetition=0, ampgain=0, emgain=0):
        print('Andor Imaging mode: ', self.andormode)
        aa=8#-----------------------Set aa=0, just for debugging-----------#
        if self.andormode == 'FastKinetics':
            print('Setting camera parameters for fast kinetics.')
            self.width=self.frame_width()+aa
            self.height=self.frame_height()+aa
            windll.atmcd64d.SetAcquisitionMode(4) #1 single mode 2 accumulate mode 5 run till abort
            #windll.atmcd64d.SetFastKinetics(501,2,c_float(3.0e-3),4,1,1)
            windll.atmcd64d.SetFastKinetics(501,2,c_float(integration*1.0e-3),4,1,1)
        elif self.andormode == 'live':
            print('Setting camera parameters for live mode.')
            self.width=self.frame_width()+aa
            self.height=self.frame_height()+aa
            windll.atmcd64d.SetAcquisitionMode(5) #1 single mode 2 accumulate mode 5 run till abort
        elif self.andormode == 'TriggeredAcquisition':
            print('Setting camera parameters for Triggered Acquisition mode')
            self.width=self.frame_width()+aa
            self.height=self.frame_height()+aa
            windll.atmcd64d.SetAcquisitionMode(5) #1 single mode 2 accumulate mode 5 run till abort
        print('Andor set timings:')
        print('  set exposure time =', integration, 'ms')
        print('  set repetition time =', repetition, 'ms')
        print("rep = ", repetition)
        if repetition!=0:
            print("rep = ", repetition, " and Trigger is Internal")
            windll.atmcd64d.SetTriggerMode(0)     #0 internal 1 external 10 software trigger
            windll.atmcd64d.SetExposureTime(c_float(integration*1.0e-3))
            windll.atmcd64d.SetKineticCycleTime(c_float(repetition*1.0e-3))   # check *******
        else:
            windll.atmcd64d.SetTriggerMode(7)     #0 internal 1 external 7 external exposure 10 software trigger
            windll.atmcd64d.SetExposureTime(c_float(integration*1.0e-3))
            windll.atmcd64d.SetKineticCycleTime(0)   # check *******
        if self.andormode == 'absorptionfast':
            windll.atmcd64d.SetAcquisitionMode(4)    #1 single mode 2 accumulate mode 5 run till abort
            windll.atmcd64d.SetTriggerMode(6)        #0 internal 1 external 10 software trigger

             
        #windll.atmcd64d.SetNumberAccumulation(repetition)
        #windll.atmcd64d.SetAccumulationCycleTime(1)   # check *******
        windll.atmcd64d.SetImage(1,1,1,self.width,1,self.height)
        readexposure = c_float()
        readaccumulate = c_float()
        readkinetic = c_float()
        windll.atmcd64d.GetAcquisitionTimings(byref(readexposure),byref(readaccumulate),byref(readkinetic))
        print('Andor read timings:')
        print('  read exposure time =', readexposure.value*1000, 'ms')
        print('  read accumulate time =', readaccumulate.value*1000, 'ms')
        print('  read kinetic time =', readkinetic.value*1000, 'ms')
        print('Andor image size:', self.width, 'x', self.height)
        gainvalue = c_float()
        windll.atmcd64d.GetPreAmpGain(ampgain,byref(gainvalue))
        print('Andor preamp gain #%d'%ampgain,'=', gainvalue.value)
        windll.atmcd64d.SetPreAmpGain(ampgain)
        print('Andor EM gain =',emgain)
        windll.atmcd64d.SetEMGainMode(0)    #accept values 0-255
        windll.atmcd64d.SetEMCCDGain(emgain)    #accept values 0-255
        
    def start_live_acquisition(self):       
        windll.atmcd64d.StartAcquisition()
        self.numberandorimages=0

    def roidata(self):
        starttime=time.time()
        if self.andormode == 'TriggeredAcquisition' or self.andormode == 'live':
            print('Retrieving image: ', self.width,'x',self.height)
            imgtype = c_long*(self.width*self.height)#remove+2 when operating on Andor
            img = imgtype()
            windll.atmcd64d.GetMostRecentImage(img,c_long(self.width*self.height))
            imgout=numpy.ctypeslib.as_array(img)
            imgout=numpy.reshape(imgout,(self.height,self.width))
        if self.andormode == 'FastKinetics':
            print('Retrieving images: ', self.width,'x',self.height)
            imgtype = c_long*(self.width*self.height)
            img = imgtype()
            windll.atmcd64d.GetAcquiredData(img,c_long(self.width*self.height))
            imgout=numpy.ctypeslib.as_array(img)
            imgout=numpy.reshape(imgout,(self.height,self.width))
            windll.atmcd64d.StartAcquisition()
        endtime=time.time()
        print('  readout time = ', endtime-starttime, ' s')
        return imgout

# if __name__ == '__main__':
#     cam = Cam()
#     cam.open()
#     cam.start_cooling()
#     print(cam.gettemperature())
#     time.sleep(5)
#     print(cam.gettemperature())
#     cam.wait()
#     img = cam.roidata()
#     print()
#     cam.close()
  
    
