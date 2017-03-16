# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
"""
Camera.py acquire images live or subjected to an external trigger and displays them.
"""

from PyQt5 import QtCore, QtWidgets, QtGui
import PyQt5
import numpy
import logging
from contextlib import closing

import os, os.path
import threading, queue
import time
from Camera import fileSettings
from Camera import readImage
from scan import ScanControl, ScanList

from pyqtgraph import image

#from astropy.io import fits

from dedicatedCounters import AutoLoad
from dedicatedCounters import DedicatedCountersSettings
from Camera import CameraSettings
from dedicatedCounters import DedicatedDisplay
from dedicatedCounters import InputCalibrationUi
from modules import enum
from modules.quantity import Q




uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/Camera.ui')
CameraForm, CameraBase = PyQt5.uic.loadUiType(uipath)

# try:
#     import ANDOR
#     camandor = ANDOR.Cam()
#     useAndor = not camandor.error
# except ImportError:
#     useAndor = False
#     print ("Andor not available.")

from Camera.ANDOR import Cam, CamTimeoutError
camandor=Cam()
useAndor=True

class AndorTemperatureThread(threading.Thread):  # Class added
    """This Thread monitor the Andor Temperature and displays it in the Status Bar"""
    def __init__(self, app):
            threading.Thread.__init__(self)
            self.app = app


    def run(self):
            global andortemp
            andortemp = True
            while andortemp:
                self.app.statusBar().showMessage("Temp = %.1f °C" % camandor.gettemperature() )
                #self.app.statusBar().showMessage("T = %.1f °C" %time.time())
                #print(self.camandor.gettemperature())
                time.sleep(2)

    def stop(self):
            global andortemp
            andortemp = False
            self.app.statusBar().showMessage("Not Cooling")

class AndorProperties(object):
    def __init__(self, ampgain=0, emgain=0):
        self._ampgain = ampgain
        self._emgain = emgain

    def get_ampgain(self):
        return self._ampgain

    def set_ampgain(self,value):
        self._ampgain = value

    ampgain = property(get_ampgain, set_ampgain)

    def get_emgain(self):
        return self._emgain

    def set_emgain(self,value):
        self._emgain = value

class CamTiming(object):
    def __init__(self, exposure, repetition=None, live=True):
        self._exposure = exposure
        self._repetition = repetition
        self._live = live

    def get_exposure(self):
        if self._live:
            return self._exposure
        else:
            if useAndor: #change this when you test it
                return self._exposure
            else:
                return 0

    def set_exposure(self, value):
        self._exposure = value

    exposure = property(get_exposure, set_exposure)

    def get_repetition(self):
        if self._live:
            return self._repetition
        else:
            if useAndor:
                return self._exposure
            else:
                return 0

    def set_repetition(self, value):
        self._repetition = value

    repetition = property(get_repetition, set_repetition)

    def get_live(self):
        return self._live

    def set_live(self, value=True):
        self._live = bool(value)

    live = property(get_live, set_live)

    def get_external(self):
        return not self.live

    def set_external(self, value):
        self.live = not value

    external = property(get_external, set_external)

class AcquireThread(threading.Thread):
    """Base class for image acquisition threads."""

    def __init__(self, app, cam, queue):
        threading.Thread.__init__(self)
        self.app = app
        self.cam = cam
        self.queue = queue

        self.running = False
        self.nr = 0

    def run(self):
        pass

    def stop(self):
        self.running = False

class AcquireThreadAndor(AcquireThread):
    def run(self):
        self.running = True
        print('Starting Acquiring Thread and the mode is = ', camandor.andormode)
        with closing(self.cam.open()):

            if self.app.timing_andor.external:
                print("Exp is gonna be = ",self.app.settings.exposureTime.value.magnitude,self.app.settings.exposureTime.value.u)
                print("EM is gonna be = ", self.app.settings.EMGain.value)

                if   str(self.app.settings.exposureTime.value.u) == 'us': exp=self.app.settings.exposureTime.value.magnitude*0.001
                elif str(self.app.settings.exposureTime.value.u) == 'ms': exp=self.app.settings.exposureTime.value.magnitude
                else:                                                     exp = self.app.settings.exposureTime.value.magnitude
                print('exp = ', exp)
                self.cam.set_timing(integration=exp,
                                    repetition=0,
                                    ampgain=self.app.properties_andor.get_ampgain(),
                                    emgain=int(self.app.settings.EMGain.value))

            else:
                #AndorTemperatureThread(self.app).stop()
                self.cam.set_timing(integration=self.app.timing_andor.exposure,
                                    repetition=self.app.timing_andor.repetition,
                                    ampgain=self.app.properties_andor.get_ampgain(),
                                    emgain=self.app.settings.EMGain)

            #self.cam.start_live_acquisition()# let's comment this out, we will introduce the live afterwards

            while self.running:
                try:
                    #self.cam.wait(0.1)
                    pass

                except CamTimeoutError:
                    pass
                else:
                    img = self.cam.roidata()
                    time.sleep(1)
                    # self.running=False
                    self.nr += 1
                    self.queue.put((self.nr, img.astype(numpy.float32)))  # TODO: ????
                    print("--------Acquiringthread--------")
                    print("Just Acquired an img and put it in the queue:")
                    print(img)

            # put empty image to queue
            self.queue.put((- 1, None))

        print("Exiting AndorImageProducerThread")

    def stop(self):
        global andortemp
        andortemp = True# understand what the Temeperature dependence has to do here
        self.running = False
        # try:
        self.cam.stop()
        if not andortemp:
            AndorTemperatureThread(self.app).start()

class ConsumerThread(threading.Thread):
    def __init__(self, app, queue):
        threading.Thread.__init__(self, name="ImageConsumerThread")
        self.queue = queue
        self.app = app
        self.running = False

    def run(self):
        pass

    def get_image(self, timeout=1):
        """get image from queue, skip empty images (nr<0)"""
        nr = - 1
        while nr < 0:
            nr, img = self.queue.get(block=True, timeout=timeout)
        return nr, img

    def message(self, msg):
        #wx.PostEvent(self.app, StatusMessageEvent(data=msg))
        self.app.statusBar().showMessage(str(msg))


    def save_abs_img(self, filename, img):
        """Saves absorption images"""
        rawimg = (1000 * (img + 1)).astype(numpy.uint16)
        readImage.write_raw_image(filename, rawimg, False)
        self.message('Saving Image')

    def save_raw_img(self, filename, img):
        """Saves Raw images"""
        rawimg = img.astype(numpy.uint16)
        readImage.write_raw_image(filename, rawimg, True)
        self.message('S')

    def saveimage(self, dir,filename,img):
        imagesavedir = dir
        imagesavefilename = "%s%s%s.sis" % (time.strftime("%Y%m%d%H%M%S"),"-ScanName","-Image-number")
        imagesavefilenamefull = os.path.normpath(os.path.join(imagesavedir, imagesavefilename))
        rawimg = img.astype(numpy.uint16)
        readImage.write_raw_image(imagesavefilenamefull, rawimg, False)


    def stop(self):
        self.running = False
        # TODO: empty queue

class ConsumerThreadAndorSingleImage(ConsumerThread):
    def run(self):
        self.running = True
        print("Andor single image")
        while self.running:
            try:
                nr, img = self.queue.get(timeout=10)
                # self.message('ok')
                # print camandor.gettemperature()

            except queue.Empty:
                self.message('R')

            else:
                if nr > 0:
                    #wx.PostEvent(self.app, AndorSingleImageAcquiredEvent(imgnr=nr, img=img))"find a new function"
                    self.message('I')

        self.message('E')
        print("Exiting ImageConsumerThread")

class ConsumerThreadAndorFast(ConsumerThread):
    """Acquire three images, calculate absorption image, save to file, display"""

    def run(self):
        self.running = True
        # print "-----------------------"
        while self.running:
            try:
                nr1, img1 = self.get_image(timeout=5)
                self.message('1')
                if not self.running: break
                print("image ok")
                nr2, img2 = self.get_image(timeout=5)
                self.message('2')
                if not self.running: break
                print("image ok")

            except queue.Empty:
                self.message(None)
                self.message('W')

            else:
                # calculate absorption image
                # img = - (np.log(img1 - img3) - np.log(img2 - img3))
                h, w = img1.shape
                img = + (numpy.log(img1[h / 2:] - img2[h / 2:]) - numpy.log(img1[:h / 2] - img2[:h / 2]))

                # if self.app.imaging_andor_remove_background:
                #    ma, sa = find_background(img2)
                #    img[img2<ma+4*sa] = np.NaN

                if self.app.imaging_andor_useROI:
                    # set all pixels in absorption image outside roi to NaN
                    r = self.app.marker_roi_andor.roi.ROI

                    imgR = numpy.empty_like(imga)
                    # for timg in [imga, imgb]:
                    for timg in [imga]:
                        imgR[:] = numpy.NaN
                        imgR[r] = timg[r]
                        timg[:] = imgR[:]

                data = {'image1': img1,
                        'image2': img2,
                        'image3': img1,
                        'image_numbers': (nr1, nr2, nr1),
                        'absorption_image': img}
                wx.PostEvent(self.app, AndorTripleImageAcquiredEvent(data=data))

                self.save_abs_img(settings.imagefile, img)
                self.save_raw_img(settings.rawimage1file, img1)
                self.save_raw_img(settings.rawimage2file, img2)

        self.message('E')
        print("Exiting ImageConsumerThread")

class ConsumerThreadIons(ConsumerThread):
    """Acquire one images, calculate absorption image, save to file, display"""
    def run(self):
        self.running = True
        while self.running:
            try:
                nr, img = self.get_image(timeout=10)
                print("--------Consumerthread--------")
                print("Taken image from Queue")
                print(img)
                time.sleep(1)
                self.message('Acquiring')
                if not self.running: break
                print("image ok")
                #self.save_abs_img(fileSettings.imagefile, img)
                #self.saveimage(fileSettings.imagesavepath,'Cane.sis',img)

            except queue.Empty:
                print("---------The queue is Empty---------")
                self.message('Waiting for Images')

            else:
                #self.save_abs_img(fileSettings.imagefile, img)
                self.saveimage(fileSettings.imagesavepath,'Cane.sis',img)

                print("--------Just saved an image--------")

        self.message('Exit')
        print("Exiting ImageConsumerThread")

class Camera(CameraForm, CameraBase):
    dataAvailable = QtCore.pyqtSignal(object)
    OpStates = enum.enum('idle', 'running', 'paused')

    def __init__(self, config, dbConnection, pulserHardware, globalVariablesUi, shutterUi, ScanExperiment, parent=None):
        CameraForm.__init__(self)
        CameraBase.__init__(self, parent)

        #Properties to integrate with other components of the code
        self.config = config
        self.configName = 'Camera'
        self.dbConnection = dbConnection
        self.pulserHardware = pulserHardware
        self.globalVariables = globalVariablesUi.globalDict
        self.globalVariablesChanged = globalVariablesUi.valueChanged
        self.globalVariablesUi = globalVariablesUi
        self.shutterUi = shutterUi
        self.ScanExperiment = ScanExperiment



        # Timing and acquisition settings
        self.imaging_mode_andor = 'TriggeredAcquisition'



    @property
    def settings(self):
        return self.settingsUi.settings

    def setupUi(self, parent):
        CameraForm.setupUi(self, parent)

        self.setWindowTitle("Andor Camera")



        # Settings


        self.settingsUi = CameraSettings.CameraSettings(self.config,self.globalVariablesUi)
        self.settingsUi.setupUi(self.settingsUi)
        self.settingsDock.setWidget(self.settingsUi)
        self.settingsUi.valueChanged.connect(self.onSettingsChanged)
        self.CameraParameters=self.settingsUi.ParameterTableModel.parameterDict

        # Arrange the dock widgets
        #self.tabifyDockWidget(self.centralwidget, self.settingsDock)

        # Queues for image acquisition
        print("NumberofExperiments = ", self.settingsUi.settings.NumberOfExperiments)
        print("Exposure time = ", self.settingsUi.settings.exposureTime)
        print("EMGain = ", self.settingsUi.settings.EMGain)
        self.imagequeue_andor = queue.Queue(1)#self.settingsUi.settings.NumberOfExperiments
        self.timing_andor = CamTiming(exposure=100, repetition=1, live=False)
        self.properties_andor = AndorProperties(ampgain=0, emgain=0)
        self.imaging_andor_useROI = False

        #Actions
        self.actionSave.triggered.connect(self.onSave)
        self.actionAcquire.triggered.connect(self.onAcquire)
        self.actionCoolCCD.triggered.connect(self.onCoolCCD)
        self.actionLive.triggered.connect(self.onLive)

        #statusbar
        self.statusBar().showMessage('T = ')

        # --------------------------------------- image display ---------------------------------------#
        # self.filename = 'Z:/Lab/Andor Project/imaging_software_g/bitmaps/acquire_splash_big.png'
        # self.filename = 'Z:/Lab/Andor Project/imaging_software_g/bitmaps/80up_1.fits'
        # image_data = fits.getdata(self.filename)
        # image_f = image_data[[0], :, range(0, 256)]
        # self.image= QtGui.QImage(image_f.shape[0], image_f.shape[1], QtGui.QImage.Format_RGB32)
        # for x in range(image_f.shape[0]):
        #     for y in range(image_f.shape[1]):
        #         self.image.setPixel(x, y, QtGui.QColor(image_f[x][y]/50.).rgb())
        #
        # self.pixmap = QtGui.QPixmap.fromImage(self.image.scaledToWidth(570))
        # scene = QtWidgets.QGraphicsScene(self)
        # scene.addPixmap(self.pixmap)
        # self.CameraView.setScene(scene)
        # self.CameraView.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        #----------------------------------------------------------------------------------------------#

        if self.configName + '.MainWindow.State' in self.config:
            QtGui.QMainWindow.restoreState(self, self.config[self.configName + '.MainWindow.State'])
        self.onSettingsChanged()

    def saveConfig(self):
        self.settings.state = self.saveState()
        self.settings.isVisible = self.isVisible()
        self.config[self.configName] = self.settings
        self.settingsUi.saveConfig()


    def onSave(self):
        print("save image")

        print(self.ScanExperiment.scanControlWidget.getScan().list)
        print(self.ScanExperiment.scanControlWidget.getScan().list[0])
        print(self.ScanExperiment.scanControlWidget.getScan().list[-1])
        self.settingsUi.saveConfig()
        # needs astropy
        # image_file = os.path.join(os.path.dirname(__file__), '..', 'ui/icons/80up_1.fits')
        # image_data = fits.getdata(image_file)
        # image_f = image_data[[0], :, range(0, 256)]
        # image(image_f, title="Ions")

    def onSettingsChanged(self):
        pass

    def onCoolCCD(self):
        if self.actionCoolCCD.isChecked():
            camandor.start_cooling()
            AndorTemperatureThread(self).start()
        else:
            camandor.stop_cooling()
            AndorTemperatureThread(self).stop()

    def OnIdle(self, event):
        self.busy = 0

    def OnSingleImageAcquiredAndor(self):

        if event.img is not None:
            # cut image into halves
            img1 = event.img[:, :]

            # avoid deadlock if too many images to process
            if self.Pending():
                self.busy += 1
            else:
                self.busy = 0

            if self.busy > 3:
                print("I am busy, skip displaying")
                self.show_status_message('.')
            else:
                self.image1a.show_image(img1, description="image #%d" % event.imgnr)

    def onLive(self):
        self.imaging_mode_andor == 'Live'
        camandor.andormode='Live'


    def onAcquire(self):
        if self.actionAcquire.isChecked():
            self.imaging_mode_andor == 'TriggeredAcquisition'
            camandor.andormode='TriggeredAcquisition'
            self.start_acquisition_andor()
        else:
            self.stop_acquisition_andor()

        #self.do_toggle_button(event.Checked(), self.ID_AcquireAndorButton)

    def start_acquisition_andor(self):
        self.acquiring_andor = True
        print("start_acquisition_andor called")
        #self.menu.EnableTop(self.ID_TimingAndor, False)

        self.imgproducer_andor = AcquireThreadAndor(self,camandor,self.imagequeue_andor)
        self.imgconsumer_andor = ConsumerThreadIons(self, self.imagequeue_andor)

        # if self.imaging_mode_andor == 'live':
        #     self.imgconsumer_andor = ConsumerThreadAndorSingleImage(self, self.imagequeue_andor)
        # elif self.imaging_mode_andor == 'TriggeredAcquisition':
        #     self.imgconsumer_andor = ConsumerThreadIons(self, self.imagequeue_andor)
        #     print("ConsumerThreadIons called but not started")

        self.imgproducer_andor.start()
        self.imgconsumer_andor.start()


    def stop_acquisition_andor(self):
        self.imgconsumer_andor.stop()
        self.imgproducer_andor.stop()
        self.imgconsumer_andor.running=False
        self.imgproducer_andor.running=False


        self.imgconsumer_andor.join(2)#2
        self.imgproducer_andor.join(6)#6


        #if self.imgproducer_andor.isAlive() or self.imgconsumer_andor.isAlive():
        #    print("could not stop Andor acquisition threads!", threading.enumerate())

        self.acquiring_andor = False
        #self.menu.EnableTop(self.ID_TimingAndor, True)

    # def OnSaveImageAndor(self):
    #     print("save image")
    #     #imgA = self.image1a.imgview.get_camimage()
    #     #readsis.write_raw_image(settings.imagefile, imgA, True)
    #     #wx.PostEvent(self, StatusMessageEvent(data='s')

# if __name__ == '__main__':
#     camandor = Cam()
#     camandor.open()
#     camandor.set_timing(integration=100, repetition=0, ampgain=0, emgain=0)
#     camandor.start_cooling()
#
#     #CameraGui = Camera('config', 'dbConnection', 'pulserHardware', 'globalVariablesUi', 'shutterUi','externalInstrumentObservable')
#     #Tthread = AndorTemperatureThread(CameraGui,camandor)
#     #Tthread.start()
#
#     #camandor.wait()
#     img = camandor.roidata()
#
#     print(img)
#     #camandor.close()