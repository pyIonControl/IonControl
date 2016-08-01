# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import sys
import os.path
import numpy

# Our devices
from Devices import e3633a, RFSource, TOAMeasurement
#from kmf_toa_measurement import TOAMeasurement
# Josh's code
sys.path.append("C:\\PythonCode.git")
from .pCounter import pCounter
from .WaveformChassis import WaveformChassis
from .itfParser import itfParser
from .DAQmxUtility import Mode
from .eMapParser import eMapParser

base_dir = "C:\\Experiments\\Thunderbird"

def getDCTickle():
    dc = RFSource("fg", "dc_tickle_33210a", 1)
    dc.setAmplitude(0.10)
    dc.turnOn()
    return dc

def getDopplerPS():
    ps = e3633a("transfer_lock_ps")
    return ps

def getChassis():
    chassis = WaveformChassis()
    chassis.mode = Mode.Static
    chassis.initFromFile(os.path.join(base_dir, 'chassis.cfg'))

    return chassis

def getNICounter(gateTime=300, nSamples=1):
    ctr = pCounter()
    ctr.samples = nSamples
    ctr.sampleRate = 1e3/gateTime
    ctr.clockSourceTerm = 'PFI0'
    ctr.edgeCntrTerm = 'PFI1'
    ctr.initFromFile(os.path.join(base_dir, "chassis.cfg"))
    return ctr

def getTOA():
    toa = TOAMeasurement(counter = "sr620_counter", badCallsLimit = 2)
    toa.idle()
    return toa

def getRFTickle():
    tickle_src = RFSource("fg", "tickle_source_afg3101", 1)
    tickle_src_amp = 0.6
    tickle_src.setAmplitude( tickle_src_amp )

def getRFSource():
    rf_drive = RFSource("fg", "rf_source_afg3102", 1)
    rf_drive_freq = rf_drive.frequency()#MHz
    
    rf_trig = RFSource("fg", "rf_source_afg3102", 2, eqInst = rf_drive)
    rf_trig.writeHard('SOURce2:FUNC:SHAP SQU')
    rf_trig.writeHard('SOURce2:VOLT:LEV:IMM:AMPL 1Vpp')
    rf_trig.setFrequency( rf_drive_freq )

    return rf_drive, rf_trig

def getRFTrigger():
    x = getRFSource()
    return x[1]

def getRFDrive():
    x = getRFSource()
    return x[0]

mapper = eMapParser()
mapper.open(os.path.join(base_dir, "thunderbird_map.txt"))
eNum, aoNum, dNum = mapper.read()
mapper.close()

ao_to_elec = dict(list(zip(aoNum, eNum)))
elec_to_ao = dict(list(zip(eNum, aoNum)))

def convert_to_elec(aoList):
    # This function converts a voltage line sorted by AO numbers to one sorted
    # by electrode numbers
    fixedLine = numpy.zeros(len(aoList))
    for x in range(1, 49):
        if x<10:
            key = "0" + str(x)
        else:
            key = str(x)
        fixedLine[x-1] = aoList[ int(elec_to_ao[key])]
    return fixedLine

def convert_to_ao(eList):
    # This function converts a voltage line sorted by electrode numbers to one
    # sorted by AO channels 
    return numpy.array([eList[int(ao_to_elec[str(x)])-1] for x in range(48)])

def getState():
    # This function will poll some various devices and generate a dictionary
    # indicating the current state of the devices. This dictionary can be passed
    # to the dataFile class to generate the header

    state = {}
    temp = getRFSource()
    rfdrive = temp[0]
    ctr = getNICounter()


    state["RF Amplitude"] = rfdrive.amplitude()
    state["RF Frequency"] = rfdrive.frequency()
    state["Gate time"] = ctr.binTime
    state["Samples"] = ctr.samples
    state["Doppler PS"] = getDopplerPS().voltage()


    return state
