

###########################################################################
#
# simple sequence with one cooling interval during which countrates can be measured
# repeated in infinite loop
#
#define COOLDDS 0

# var syntax:
# var name value, type, unit, encoding
var datastart 3900, address   # serves as tooltip
var dataend 4000, address
var coolingFreq     250, parameter, MHz, AD9912_FRQ
var coolingFreqFine 250, ,MHz, AD9912_FRQFINE
var startupMask       1, mask
var startup           1, shutter startupMask
var startupTime       1, parameter, ms
var coolingOnMask     1, mask
var coolingOn         1, shutter coolingOnMask
var coolingCounter    1, counter
var coolingOffMask    1, mask
var coolingOff        0, shutter coolingOffMask
var coolingOffCounter 0, counter
var coolingTime       100, parameter, ms
var experiments     350, parameter
var epsilon         100, parameter, ns
var ddsApplyTrigger   3,trigger

	SHUTTERMASK startupMask
	ASYNCSHUTTER startup
	UPDATE startupTime
#	DDSFRQ COOLDDS, coolingFreq
#	DDSFRQFINE COOLDDS, coolingFreqFine
	TRIGGER ddsApplyTrigger
cooling: NOP
	SHUTTERMASK coolingOnMask
	ASYNCSHUTTER coolingOn
	COUNTERMASK coolingCounter
	WAIT                             # for end of startup or last
	UPDATE coolingTime

	SHUTTERMASK coolingOffMask
	ASYNCSHUTTER coolingOff
	COUNTERMASK coolingOffCounter
	WAIT
	UPDATE epsilon

	# write the record separator
	WRITEPIPEINDF 
	LDWR epsilon
	NOP
	WRITEPIPE
	NOP
	NOP

	READPIPE
	CMPEQUAL 
	JMP cooling	
	END
