###########################################################################
#
# simple sequence with one cooling interval during which countrates can be measured
# repeated in infinite loop
#
# A Pulse Programmer file for the ScanParameter experiment has to fulfill the following conditions
# 
#
const COOLDDS 4
const TickleDDS 5
const ZERO 0

# var syntax:
# var name value, type, unit, encoding

# Frequencies
var coolingFreq     118, parameter, MHz, AD9912_FRQ
var detectFreq      100, parameter, MHz, AD9912_FRQ
var tickleFreq          15, parameter, MHz, AD9912_FRQ

#Amplitude
var A_cooling 1023, parameter
var A_detect 100, parameter 

# Shutters
var startupMask      0x4000001, mask
var startup           0x4000001, shutter startupMask
var darkOnMask       0, mask
var darkOn                0, shutter darkOnMask
var coolingOnMask     1, mask
var coolingOn         1, shutter coolingOnMask
var coolingOffMask    1, mask
var coolingOff        0, shutter coolingOffMask

# Counters
var detectCounter     0, counter
var coolingCounter    2, counter
var coolingOffCounter 0, counter

# Triggers
var ddsApplyTrigger   0x3f,trigger

# Times
var startupTime       1, parameter, ms
var coolingTime       5, parameter, ms
var detectTime        10, parameter, ms
var darkTime           0, parameter, ms
var epsilon         2, parameter, us
var epsilonTwo  2, parameter, ms
var pretriggerTime 2, parameter, ms

# General
var experiments   10, parameter
var Threshold 0, parameter
var maxcoolingrep   1000, parameter

# Internal
var experimentsleft 10
var endLabel 0xffffffff
var null 0
var coolingrepcounterFlag 0x40000000
var coolingrepcounter 0

# Preparation
	SHUTTERMASK startupMask
	ASYNCSHUTTER startup
	DDSFRQ COOLDDS, coolingFreq
	DDSFRQFINE COOLDDS, coolingFreq
	DDSFRQ TickleDDS, tickleFreq
	TRIGGER ddsApplyTrigger
	UPDATE startupTime

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
	DDSFRQ TickleDDS, tickleFreq

experimentloop: NOP
	DDSFRQ COOLDDS, coolingFreq 
	DDSAMP COOLDDS, A_cooling
	TRIGGER ddsApplyTrigger
	LDWR null
	STWR coolingrepcounter
cooling: NOP
	INC coolingrepcounter
	STWR coolingrepcounter
	CMP maxcoolingrep             # if coolingrepcounter greater than MaxCoolingRep w=w else W=0
	JMPNZ endlabel
	SHUTTERMASK coolingOnMask
	ASYNCSHUTTER coolingOn
	COUNTERMASK coolingCounter
	WAIT                             # for end of startup or last
	UPDATE coolingTime
	COUNTERMASK coolingOffCounter
	SHUTTERMASK coolingOffMask
	ASYNCSHUTTER coolingOff
	WAIT
	UPDATE epsilon
	LDWR Threshold
	JMPZ	dark
	LDCOUNT	ZERO
	CMP      	Threshold 	# if counts greater than threshold w=w else W=0
	JMPZ     	cooling  		# if w=0 back to init
	LDWR coolingrepcounter
	ADDW coolingrepcounterFlag
	WRITEPIPE

dark: NOP
	LDWR darkTime
	JMPZ detect
	SHUTTERMASK darkOnMask
	ASYNCSHUTTER darkOn
	WAIT
	UPDATE darkTime
	COUNTERMASK detectCounter
	WAIT
	UPDATE pretriggerTime	
	
detect: NOP
	DDSFRQ COOLDDS,detectFreq 
	DDSAMP COOLDDS, A_detect
	TRIGGER ddsApplyTrigger
	SHUTTERMASK coolingOnMask
	ASYNCSHUTTER coolingOn
	COUNTERMASK detectCounter
	WAIT                             # for end of startup or last
	UPDATE detectTime	
	
	COUNTERMASK null
	DEC experimentsleft
	STWR experimentsleft
	WAIT
	UPDATE epsilonTwo
	JMPNZ experimentloop
	JMP scanloop
	
endlabel: NOP
	WAIT
	 LDWR endLabel
	WRITEPIPE
	END