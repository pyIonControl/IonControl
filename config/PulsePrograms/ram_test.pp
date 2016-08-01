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
var integrationTime 5, parameter, ms
var ramaddr 0, address


	SETRAMADDR ramaddr
	UPDATE integrationTime
	WAIT
	JMPRAMINVALID endlabel
	RAMREAD
	WRITEPIPE
	NOP
	RAMREAD
	WRITEPIPE
	NOP
	RAMREAD
	WRITEPIPE
	NOP
	RAMREAD
	WRITEPIPE
	NOP
	
endlabel: LDWR end
	WRITEPIPE
	END