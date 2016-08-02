###########################################################################
#
#   PMTtest.pp -- Jan 17 2008
#  tests if talking to PMT.

#define DDS729	   0
#define DDSDoppler 4
#define PMTChannel 1

# 397 beam frequencies and amplitudes
var F_Red_Doppler 120, parameter, MHz, AD9912_FRQ
var A_Red_Doppler 1023, parameter
var F_Blue_Doppler 120, parameter, MHz, AD9912_FRQ
var A_Blue_Doppler 1023, parameter
var F_Detect 120, parameter, MHz, AD9912_FRQ
var A_Detect 1023, parameter

# 729 beam frequencies
var F_729_SP 150, parameter, MHz, AD9912_FRQ
var F_729_SC 150, parameter, MHz, AD9912_FRQ
var F_729_Analyzing 150, parameter, MHz, AD9912_FRQ
var A_729 1023, parameter

# masks and shutters
var CoolingOnMask     1, mask
var CoolingOn         1, shutter CoolingOnMask
var CoolingOffMask    1, mask
var CoolingOff        0, shutter CoolingOffMask
var SidebandOnMask	  0, mask
var SidebandOn        0, shutter SidebandOnMask
var SidebandOffMask   0, mask
var SidebandOff       0, shutter SidebandOffMask
var DetectOnMask      0, mask
var DetectOn		  0, shutter DetectOnMask
var DetectOffMask     0, mask
var DetectOff         0, shutter DetectOffMask
var RepumpOnMask      0, mask
var RepumpOn          0, shutter RepumpOnMask
var RepumpOffMask     0, mask
var RepumpOff         0, shutter RepumpOffMask

# times
var CoolingTime       1, parameter, ms
var Epsilon          500, parameter, ns
var BlueCoolingTime    1, parameter, ms
var SpinPolTime        1, parameter, ms
var SidebandPiTime     1, parameter, ms
var SidebandCoolingDelta 1, parameter, ms
var AnalyzingTime      1, parameter, ms
var DetectTime         1, parameter, ms
var RepumpTime         1, parameter, ms

# control parameters
var MaxInitRepeat 10, parameter
var experiments   100, parameter
var pmtInput    1, counter
var ddsApplyTrigger   3,trigger
var DetectThreshold 6, parameter
var SP_loops        10, parameter
var SC_loops        10, parameter

# internal variables
var experimentsleft 100
var Null 0
var endLabel 0xffffffff
var SP_counter 0
var SC_counter 0
var sctime 0
var initRemaining 0

# startup switching on cooling quickly
	SHUTTERMASK CoolingOnMask
	ASYNCSHUTTER CoolingOn
	DDSFRQ DDSDoppler, F_Red_Doppler
	DDSAMP DDSDoppler, A_Red_Doppler
	DDSAMP DDS729, A_729
	TRIGGER ddsApplyTrigger
	UPDATE CoolingTime

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
	JMPZ cool
	
initlooplabel: NOP
	# Make sure the ion is bright
	SHUTTERMASK  CoolingOnMask
	ASYNCSHUTTER CoolingOn
	DDSFRQ		DDSDoppler, F_Detect
	COUNTERMASK pmtInput
	WAIT
	DDSAMP	 	DDSDoppler, A_Detect  
	UPDATE      DetectTime
	
	WAIT
	UPDATE	    Epsilon
	DEC initRemaining
	STWR initRemaining
	JMPZ endlabel              # id the ion did not show up after MaxInitRepeat tries we will give up for good
	LDCOUNT		PMTChannel
	CMP      	DetectThreshold 	# if counts greater than threshold w=w else W=0
	JMPZ     	initlooplabel  		# if w=0 back to init
	
cool: NOP
	DDSFRQ   	DDSDoppler, F_Blue_Doppler
	SHUTTERMASK  CoolingOnMask
	ASYNCSHUTTER CoolingOn
	WAIT
	DDSAMP	 	DDSDoppler, A_Blue_Doppler
	UPDATE      BlueCoolingTime
	
	LDWR     	SP_loops      # Number of spin polarization Loops
	JMPZ	 	exp           # if SP_loops=0 it skips to exp
	STWR     	SP_counter    # put SP_loops into counter  
	
SP: NOP                       
	DDSFRQ	 	DDS729, F_729_SP
	TRIGGER ddsApplyTrigger
	SHUTTERMASK  CoolingOffMask
	ASYNCSHUTTER CoolingOff	
	SHUTTERMASK  SidebandOnMask
	ASYNCSHUTTER SidebandOn
	WAIT
	UPDATE SpinPolTime
	
	SHUTTERMASK  SidebandOffMask
	ASYNCSHUTTER SidebandOff
	SHUTTERMASK  RepumpOnMask
	ASYNCSHUTTER RepumpOn
	WAIT
	UPDATE RepumpTime
	
	SHUTTERMASK  RepumpOffMask
	ASYNCSHUTTER RepumpOff

	DEC      	SP_counter
	STWR     	SP_counter
	JMPNZ    	SP

	LDWR	 SC_loops
    JMPZ     exp	# if SC_loops=0 it skips to exp
	STWR	 SC_counter # put SC_loops into counter
	LDWR     SidebandPiTime
	STWR     sctime
	
SC: NOP	
	DDSFRQ	 	DDS729, F_729_SC
	TRIGGER ddsApplyTrigger
	SHUTTERMASK  SidebandOnMask
	ASYNCSHUTTER SidebandOn
	WAIT
	UPDATE sctime
	
	SHUTTERMASK  RepumpOnMask
	ASYNCSHUTTER RepumpOn
	WAIT
	UPDATE RepumpTime
	SHUTTERMASK  RepumpOffMask
	ASYNCSHUTTER RepumpOff	
	
	LDWR     sctime
	ADDW     SidebandCoolingDelta
	STWR     sctime
	DEC      SC_counter
	STWR     SC_counter
	JMPZ     exp
	JMPNZ    SC
	
exp: NOP
	DDSFRQ	 	DDS729, F_729_Analyzing   #SHUTRVAR   	SHUTR_driveD5half
	TRIGGER ddsApplyTrigger
	SHUTTERMASK  SidebandOnMask
	ASYNCSHUTTER SidebandOn
	WAIT
	UPDATE AnalyzingTime
	
	DDSFRQ		DDSDoppler, F_Detect
	DDSAMP	 	DDSDoppler, A_Detect
	COUNTERMASK pmtInput
	TRIGGER ddsApplyTrigger
	SHUTTERMASK  DetectOnMask
	ASYNCSHUTTER DetectOn
	
	WAIT
	UPDATE DetectTime
	
	DDSFRQ		DDSDoppler, F_Red_Doppler
	SHUTTERMASK  CoolingOnMask
	ASYNCSHUTTER CoolingOn
	COUNTERMASK  Null
	TRIGGER ddsApplyTrigger
	WAIT
	DDSAMP	 	DDSDoppler, A_Red_Doppler
	UPDATE CoolingTime
	
	DEC experimentsleft
	STWR experimentsleft
	JMPNZ init
	JMP scanloop
	
endlabel: LDWR endLabel
	WRITEPIPE
	END