###########################################################################
#
#   PMTtest.pp -- Jan 17 2008
#  tests if talking to PMT.

#insert extras.pp

#define REDDDS	   0
#define BLUEDDS	   1  #Changed Craig Nov 15 2010 for new AOM
#define IRDDS	   4
#define COOLDDS    3

# var syntax:
# var name value, type, unit, encoding
var datastart 3900, address   # serves as tooltip
var dataend 4000, address
var addr 0, address
var sample 0, address
var delay 0, address
var coolingFreq     250, parameter, MHz, AD9912_FRQ
var coolingOnMask     1, mask
var coolingOn         1, shutter coolingOnMask
var coolingOffMask    1, mask
var coolingOff        0, shutter coolingOffMask
var fixedValue       0, shutter
var coolingTime       1, parameter, ms
var experiments     350, parameter
var epsilon         100, parameter, ns
var ddsApplyTrigger 3,trigger

	LDWR     datastart
	STWR     addr	
	LDWR	 experiments
	STWR	 sample
cooling: NOP
	DDSFRQ COOLDDS, coolingFreq
	DDSFRQFINE COOLDDS, coolingFreq
	SHUTTERMASK coolingOnMask
	ASYNCSHUTTER coolingOn
	WAIT
	UPDATE coolingTime
	SHUTTERMASK coolingOffMask
	ASYNCSHUTTER coolingOff
	WAIT
	UPDATE epsilon
	DEC
	JMPNZ cooling
	
	END
