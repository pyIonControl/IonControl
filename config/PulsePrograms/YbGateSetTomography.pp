###########################################################################
#
#   PMTtest.pp -- Jan 17 2008
#  tests if talking to PMT.
#

#define DDSDetect 1
#define DDSMicrowave 2
#define PMTChannel 9

# 397 beam frequencies and amplitudes
var DetectFreq 100, parameter, MHz, AD9912_FRQ
var DetectAmp 1023, parameter
var MicrowaveFreq 40, parameter, MHz, AD9912_FRQ
var MicrowaveInitPhase 0, parameter, , AD9912_PHASE
var MicrowaveAnalyzePhase 0, parameter, , AD9912_PHASE

# masks and shutters
var InitializationShutter 0, shutter
var CoolingOnMask     1, mask
var CoolingOn            1, shutter CoolingOnMask
var CoolingOffMask    1, mask
var CoolingOff        0, shutter CoolingOffMask
var PumpingOnMask   0, mask
var PumpingOn        0, shutter PumpingOnMask
var PumpingOffMask   0, mask
var PumpingOff        0, shutter PumpingOffMask
var MicrowaveOnMask 0 , mask
var MicrowaveOn 0, shutter MicrowaveOnMask
var MicrowaveOffMask 0, mask
var MicrowaveOff 0, shutter MicrowaveOffMask
var DetectOnMask      0, mask
var DetectOn		  0, shutter DetectOnMask
var DetectOffMask     0, mask
var DetectOff         0, shutter DetectOffMask

# times
var CoolingTime       1, parameter, ms
var PumpTime         0, parameter, ms
var QubitInitTime 10,parameter, ms
var QubitAnalyzeTime 0,parameter, ms
var DetectTime      1, parameter, ms
var Epsilon          500, parameter, ns
var AmplitudeSettlingTime 100, parameter, us
var gateTime      100, parameter, us
var piTime            90, parameter, us

# control parameters
var MaxInitRepeat 10, parameter
var experiments   100, parameter
var CheckIonCounters 0, counter
var DetectCounters 0, counter
var ddsApplyTrigger   3,trigger
var ddsMicrowaveApply 0,trigger
var PresenceThreshold 6, parameter
var UseGateSequence 0,parameter

# internal variables
var experimentsleft 100
var Null 0
var endLabel 0xffffffff
var initRemaining 0
var trainPhase 0
var trainTime 0
var PulsesRemaining 0
var RamStartAddress 0, address

# startup switching on cooling quickly
	SHUTTERMASK  endLabel
	ASYNCSHUTTER InitializationShutter
	DDSFRQ DDSDetect, DetectFreq
	DDSAMP DDSDetect, DetectAmp
	TRIGGER ddsApplyTrigger
	UPDATE Epsilon

scanloop: NOP
	# Read the scan parameter from the input data if there is nothing else jump to stop
	# the parameters are echoed to the output stream as separators
	JMPPIPEEMPTY endlabel
	READPIPEINDF
	NOP
	WRITEPIPEINDF 
	NOP
	READPIPE
	NOP
	WRITEPIPE
	NOP
	STWI
	# reload the number of experiments
	LDWR experiments
	STWR experimentsleft

	
init: NOP
	LDWR MaxInitRepeat
	STWR initRemaining
	SETRAMADDR RamStartAddress
	
cool: NOP
	# Cool ion and check it is there
	SHUTTERMASK  CoolingOnMask
	ASYNCSHUTTER CoolingOn
	COUNTERMASK CheckIonCounters
	WAIT
	UPDATE      CoolingTime
	COUNTERMASK Null
	WAIT
	UPDATE	Epsilon
	# check the number of counts seen, if > threshold go to Pump
	LDCOUNT	PMTChannel
	CMP      	PresenceThreshold 	# if counts greater than threshold w=w else W=0
	JMPNZ     	pump  		# if w!=0 go on
	LDWR MaxInitRepeat
	JMPZ pump                       # if MaxInitRepeat=0 go on to pump
	DEC initRemaining
	STWR initRemaining
	JMPNZ cool
	JMP endlabel              # id the ion did not show up after MaxInitRepeat tries we will give up for good
	
pump: NOP
	SHUTTERMASK  CoolingOffMask
	ASYNCSHUTTER CoolingOff	
	LDWR PumpTime
	JMPZ QubitInit
	SHUTTERMASK  PumpingOnMask
	ASYNCSHUTTER PumpingOn
	WAIT
	UPDATE      PumpTime
	
	SHUTTERMASK  PumpingOffMask
	ASYNCSHUTTER PumpingOff	

QubitInit: NOP  
	LDWR QubitInitTime
	JMPZ PulseTrainInit
	DDSFRQ DDSMicrowave, MicrowaveFreq
	DDSPHS DDSMicrowave, MicrowaveInitPhase
	TRIGGER ddsMicrowaveApply
	SHUTTERMASK  MicrowaveOnMask
	ASYNCSHUTTER MicrowaveOn
	WAIT
	UPDATE QubitInitTime
	
	SHUTTERMASK  MicrowaveOffMask
	ASYNCSHUTTER MicrowaveOff
	
PulseTrainInit: NOP
	LDWR UseGateSequence
	JMPZ QubitAnalyze

	RAMREAD 
	NOP
	STWR PulsesRemaining
PulseTrain: NOP
	LDWR PulsesRemaining
	JMPZ QubitAnalyze
	DEC PulsesRemaining
	STWR PulsesRemaining
	RAMREAD
	NOP
	STWR trainPhase
	RAMREAD
	NOP
	STWR trainTime
	JMPZ PulseTrainWait
	DDSPHS DDSMicrowave, trainPhase
	SHUTTERMASK  MicrowaveOnMask
	ASYNCSHUTTER MicrowaveOn
	WAIT
	UPDATE trainTime
	SHUTTERMASK  MicrowaveOffMask
	ASYNCSHUTTER MicrowaveOff
PulseTrainWait: NOP	
	RAMREAD
	NOP
	STWR trainTime
	JMPZ PulseTrain
	SHUTTERMASK  MicrowaveOffMask
	ASYNCSHUTTER MicrowaveOff
	WAIT
	UPDATE trainTime
	JMP PulseTrain	
		

QubitAnalyze: NOP
	LDWR QubitAnalyzeTime
	JMPZ detect
	DDSFRQ DDSMicrowave, MicrowaveFreq
	DDSPHS DDSMicrowave, MicrowaveAnalyzePhase
	TRIGGER ddsMicrowaveApply
	SHUTTERMASK  MicrowaveOnMask
	ASYNCSHUTTER MicrowaveOn
	WAIT
	UPDATE QubitAnalyzeTime
	
	SHUTTERMASK  MicrowaveOffMask
	ASYNCSHUTTER MicrowaveOff

detect: NOP
	LDWR DetectTime
	JMPZ postdetect
	DDSFRQ DDSDetect, DetectFreq
	SHUTTERMASK  DetectOnMask
	ASYNCSHUTTER DetectOn
	COUNTERMASK DetectCounters
	TRIGGER ddsApplyTrigger
	
	WAIT
	UPDATE DetectTime
	
	SHUTTERMASK DetectOffMask
	ASYNCSHUTTER DetectOff

postdetect: NOP
	DEC experimentsleft
	STWR experimentsleft
	JMPNZ init
	JMP scanloop
	
endlabel: LDWR endLabel
	WAIT
	WRITEPIPE
	END