###########################################################################
#
# simple sequence with one cooling interval during which countrates can be measured
# repeated in infinite loop
#
#define COOLDDS 0

# var syntax:
# var name value, type, unit, encoding
var startupMask       1, mask
var startup           1, shutter startupMask
var startupTime       1, parameter, ms
var coolingOnMask     1, mask
var coolingOn         1, shutter coolingOnMask
var coolingCounter    1, counter
var coolingOffMask    1, mask
var coolingOff        0, shutter coolingOffMask
var coolingOffCounter 0, counter
var coolingTime       10, parameter, ms
var experiments     350, parameter
var experimentsleft 350
var epsilon        500, parameter, ns
var endLabel 0xffffffff

	SHUTTERMASK startupMask
	ASYNCSHUTTER startup
	UPDATE startupTime
	LDWR experiments
	STWR experimentsleft
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

	DEC experimentsleft
	STWR experimentsleft
	JMPNZ cooling	

	# write the end indicator
	LDWR endLabel
	WRITEPIPE	
	END
