var delay 500, parameter, ms
var longdelay 1, parameter, s
var shortdelay 1, parameter, us
var mask 0xffffffff, shutter
var one 1, shutter
var two 2, shutter
var three 3, shutter
var four 4, shutter
var five 5, shutter
var counteron 0x0, counter
var counteroff 0, counter
var end 0xffffffff
var temp 0x1234
var integrationTime 500, parameter, ms

here: NOP
	SHUTTERMASK mask
	ASYNCSHUTTER one
	COUNTERMASK counteron
	UPDATE longdelay
	ASYNCSHUTTER two
	CounterMASK counteroff
	WAIT
	UPDATE 1, longdelay
	UPDATE longdelay
	LDWR counteron
	WRITEPIPE
	ASYNCSHUTTER three
	COUNTERMASK counteron
	WAIT
	UPDATE integrationTime
	ASYNCSHUTTER four
	CounterMASK counteroff
	WAIT
	UPDATE longdelay
	ASYNCSHUTTER five
	WAIT
	UPDATE longdelay
	WAIT
	
	# if nothin else to do jump to the end
	JMPPIPEEMPTY endlabel
	READPIPEINDF
	NOP
	WRITEPIPEINDF
	NOP
	READPIPE
	NOP
	WRITEPIPE 
	NOP
	JMP here
	
endlabel: LDWR end
	WRITEPIPE
	END