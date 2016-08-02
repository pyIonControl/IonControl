# const values
const DDSDetect 0
const DDSRef 5
# variables 
var NULL 0
var FFFFFFFF 4294967295
var inlinevar_2 5
var endLabel 0xfffe0000, exitcode
var DetectFreq 100, parameter, MHz, AD9912_FRQ
var DetectFreqFine 100, parameter, MHz, AD9912_FRQFINE
var Ref 100, parameter, MHz, AD9912_FRQ
var RefFine 100, parameter, MHz, AD9912_FRQFINE
var DetectPhase 0, parameter, , AD9912_PHASE
var DetectAmp 1023, parameter
var startup 0, shutter
var on_mask 0, mask
var on 0, shutter on_mask
var initTime 1, parameter, ms
var TriggerInMask 1, parameter
var waitTime 0, parameter
var mytrigger 0, trigger
var mydelay 0, parameter
# inline variables
# end header


 DDSFRQFINE DDSRef, RefFine
#NOP
#DDSAMP DDSDetect, DetectAmp
  DDSFRQ DDSDetect, DetectFreq
 DDSFRQFINE DDSDetect, DetectFreqFine
#NOP
#DDSAMP DDSRef, DetectAmp
  DDSFRQ DDSRef, Ref
# line 21: procedurecall set_shutter( on )
  SHUTTERMASK on_mask
  ASYNCSHUTTER on
# line 22: procedurecall set_trigger(mytrigger)
  TRIGGER mytrigger
# line 23: procedurecall update (waitTime)
  WAITDDSWRITEDONE
  WAIT
  UPDATE waitTime
# line 24: procedurecall update()
  WAITDDSWRITEDONE
  WAIT
  UPDATE NULL
# line 27: procedurecall exit( endLabel )
  LDWR endLabel
  WAIT
  WRITEPIPE
  END