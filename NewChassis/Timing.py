# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from . import niSyncFunctions as niSync
from .niSyncError import niSyncError
import ctypes

## This class will generate perform the timing and synchronization required to
#  synchronize all cards on the PXI backplane.
class Timing(object):
    
    ## This function is a constructor for the Timing class.
    #  @param self The object pointer.
    def __init__(self):
        ## This is the reference to the NI-Sync session.
        self.session = niSync.ViSession()

        ## This the name of the NI-Sync resource that refers to the
        #  synchronization PXI card.
        self.resourceName = niSync.ViRsrc()

        ## This is the status of the NI-Sync session.
        #
        #  A value greater than 0 means that an error has occurred.
        #  When the status is greater than 0 an error should be reported
        #  by the class.
        self.status = niSync.ViStatus(0)

        ## This is a boolean that is true when the NI-Sync session has
        #  been initialized.
        self.initialized = False

        self._sampleRate = 100e3

        ## The dds is used to generate the sample clock. 
        #
        #  The lower the value of the divisor the more inaccurate the sample clock.
        #  This value is defualted to its maximum of 32.
        self.divisor = 32

        ## This is the DDS frequency that is calculated from the sample
        #  rate and the divisor.
        #
        #  The DDS frequency is the sample rate divided by the divisor.
        self.ddsFreq = self._sampleRate / self.divisor

        ## This is the number of pxi star slots available on the chassis.
        #
        #  In order for the sample clock to be distributed to all cards, this value
        #  must be equal to or larger than the number of potential cards on the
        #  Chassis.
        self.pxiStarSlots = 20
        
    ## This function checks if there is an error and prints the error message
    #  to the user.
    #  @param self The object pointer.
    def _checkError(self):
        if self.status != 0:
            errorMessage = ctypes.create_string_buffer(500)
            code = self.status
            self.status = niSync.error_message(self.session, self.status,
                    errorMessage)
            #print errorMessage.value
            raise niSyncError(code, errorMessage.value)
    
    ## This function connects to the niSync device and starts to setup clock
    #  and trigger connections.
    #  @param self The object pointer.
    #  @param deviceName The name of the niSync device.  This name can be found in
    #  Measurement and Automation Explorer. Example value: "PXI1Slot14"
    def init(self, deviceName):
        self.resourceName = niSync.ViRsrc(deviceName)
        self.status = niSync.init(self.resourceName, 0, 1,
                ctypes.byref(self.session))
        self._checkError()
        
        #Set the Front Sync Clock Source
        self.status = niSync.SetAttributeViString(self.session,
                niSync.ViConstString(), niSync.NISYNC_ATTR_FRONT_SYNC_CLK_SRC,
                niSync.NISYNC_VAL_DDS)
        self._checkError()
        
        #Set the Rear Sync Clock Source
        self.status = niSync.SetAttributeViString(self.session,
                niSync.ViConstString(), niSync.NISYNC_ATTR_REAR_SYNC_CLK_SRC,
                niSync.NISYNC_VAL_DDS)
        self._checkError()

        #Set the DDS Frequency
        self._setDDSFreq()
        
        #Set the Clock Divisor 1
        self._setDivisor()
        
        #Connect the clock to PFI0, PFI2, and PFI4 on the front of the NISync device
        triggerTerminals = [niSync.NISYNC_VAL_PFI0, niSync.NISYNC_VAL_PFI2,
                niSync.NISYNC_VAL_PFI4]
        for terminal in triggerTerminals:
            self.status = niSync.ConnectTrigTerminals(self.session,
                    niSync.NISYNC_VAL_SYNC_CLK_DIV1, terminal,
                    niSync.NISYNC_VAL_SYNC_CLK_ASYNC, niSync.NISYNC_VAL_DONT_INVERT,
                    niSync.NISYNC_VAL_UPDATE_EDGE_RISING)
            self._checkError()
        
        #Connect the Global SW Trigger to PFI1, PFI3 on the front of the
            #NISync device
        swTriggerTerminals = [niSync.NISYNC_VAL_PXITRIG0,
                niSync.NISYNC_VAL_PXITRIG1, niSync.NISYNC_VAL_PXITRIG2,
                niSync.NISYNC_VAL_PFI1, niSync.NISYNC_VAL_PFI3]

        for terminal in swTriggerTerminals:
            self.status = niSync.ConnectSWTrigToTerminal(self.session,
                    niSync.NISYNC_VAL_SWTRIG_GLOBAL, terminal,
                    niSync.NISYNC_VAL_SYNC_CLK_FULLSPEED,
                    niSync.NISYNC_VAL_DONT_INVERT,
                    niSync.NISYNC_VAL_UPDATE_EDGE_RISING, niSync.ViReal64(0))
            self._checkError()

        #Connect the Backplane PXI_TRIG5 to PFI5 on the front of the
        #NISync device
        self.status = niSync.ConnectTrigTerminals(self.session,
                niSync.NISYNC_VAL_PFI5, niSync.NISYNC_VAL_PXITRIG5,
                niSync.NISYNC_VAL_SYNC_CLK_ASYNC, niSync.NISYNC_VAL_DONT_INVERT,
                niSync.NISYNC_VAL_UPDATE_EDGE_RISING)
        self._checkError()
        
        #Connect the Clock to all Star trigger lines
        allStarLines = list(range(self.pxiStarSlots))
        clockTerminals = list()
        for starLine in allStarLines:
            clockTerminals.append("PXI_Star" + str(starLine))
        
        #clockTerminals = [niSync.NISYNC_VAL_PXISTAR0, niSync.NISYNC_VAL_PXISTAR1,
        #                  niSync.NISYNC_VAL_PXISTAR2]
        try:
            for terminal in clockTerminals:
                self.status = niSync.ConnectTrigTerminals(self.session,
                        niSync.NISYNC_VAL_SYNC_CLK_DIV1, terminal,
                        niSync.NISYNC_VAL_SYNC_CLK_ASYNC,
                        niSync.NISYNC_VAL_DONT_INVERT,
                        niSync.NISYNC_VAL_UPDATE_EDGE_RISING)
                #print 'terminal: {0}, status:{1}'.format(terminal, self.status)
                self._checkError()
        except niSyncError as e:
           if e.code == -1073807240:
               pass
           elif e.code == -1074118586:
               pass
           else:
               raise

        self.initialized = True


    def _setDDSFreq(self):
        self.ddsFreq = self._sampleRate * self.divisor
        ddsFreq = niSync.ViReal64(self.ddsFreq)
        self.status = niSync.SetAttributeViReal64(self.session, niSync.
                ViConstString(), niSync.NISYNC_ATTR_DDS_FREQ, ddsFreq)
        self._checkError()

    def _setDivisor(self):
        divisor = niSync.ViInt32(self.divisor)
        self.status = niSync.SetAttributeViInt32(self.session,
                niSync.ViConstString(), niSync.NISYNC_ATTR_SYNC_CLK_DIV1,
                divisor)
        self._checkError()

    def _setSampleRate(self, sampleRate):
        self._sampleRate = sampleRate
        if self.initialized:
            self._setDDSFreq()
            self._setDivisor()

    def _getSampleRate(self):
        return self._sampleRate

    ## This is the sample rate of the sample clock that gets
    #  distributed to all of the cards on a PXI Chassis.
    sampleRate = property(_getSampleRate, _setSampleRate)

    ## This function will send a trigger to all devices when it is called.
    #  @param self The object pointer.
    def sendSoftwareTrigger(self):
        self.status = niSync.SendSoftwareTrigger(self.session,
                niSync.NISYNC_VAL_SWTRIG_GLOBAL)
        self._checkError()
    
    ## This function will close the connection to the niSync device.
    #  @param self The object pointer.
    def close(self):
        if self.initialized:
            self.status = niSync.close(self.session)
            self._checkError()
            self.initialized = False
        
    ## This is the destructor for the Timing class.
    #  @param self The object pointer.
    def __del__(self):
        self.close()
        
        del self.session
        del self.resourceName
        del self.status
        del self._sampleRate
        del self.divisor
        del self.pxiStarSlots
