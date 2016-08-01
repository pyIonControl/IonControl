IonControl-firmware-UMD
	ConfigurationId: 0x7001
	Breakout board: Duke v2
	Shutters:
		7:0, OUT1, External
		15:8, OUT2, External
		23:16, OUT7, External
		31:24, SMA[7:0], Rf switches
		39:32, internal, PI loop enable
		47:40, internal, DAC Scan Enable
	Triggers out:
		7:0, DDS
		8, LDAC
	DDS: 
		0: AD9912, OUT3, channel 2, JP2-31, trigger 0, shutter 24
		1: AD9912, OUT3, channel 1, JP2-34, trigger 1, shutter 25
		2: AD9912, OUT4, channel 2, JP2-30, trigger 2, shutter 26
		3: AD9912, OUT4, channel 1, JP2-33, trigger 3, shutter 27
		4: AD9912, OUT5, channel 2, JP2-29, trigger 4, shutter 28
		5: AD9912, OUT5, channel 1, JP2-32, trigger 5, shutter 29
		6: AD9912, OUT6, channel 2, JP2-37, trigger 6, shutter 30
		7: AD9912, OUT6, channel 1, JP2-38, trigger 7, shutter 31
	DAC:
		8 Channels as labelled, trigger 8 is LDAC
	ADC:
		8 channels as labelled
	Counters:
		7:0, IN1, External
		15:8, IN2, External
		23:16, IN1, External (same as channels 7:0)
		31:24, IN1, External, timestamping
	Triggers in:
		7:0, IN3, External, Edge trigger
		7:0, IN3, External, Level trigger
	Serial Out:
		Not implemented
		
IonControl-firmware-UMD-20MHz-DDS-SCLK
	As IonControl-firmware-UMD
	difference is that SCLK for DDS AD9912 is set to 20MHz instead of 40MHz
		
IonControl-firmware-Cavity
	ConfigurationId: 0x4203
	Breakout board: Duke v2
	Shutters:
		7:0, OUT1, External
		14:8, OUT2, External
		15, OUT2[7], External, Serial output
		23:16, OUT7, External
		31:24, SMA[7:0], Rf switches
		39:32, internal, PI loop enable
		47:40, internal, DAC Scan Enable
	Triggers out:
		7:0, DDS
		8, LDAC
	DDS: 
		0: AD9912, OUT3, channel 2, JP2-31, trigger 0, shutter 24
		1: AD9912, OUT3, channel 1, JP2-34, trigger 1, shutter 25
		2: AD9912, OUT4, channel 2, JP2-30, trigger 2, shutter 26
		3: AD9912, OUT4, channel 1, JP2-33, trigger 3, shutter 27
		4: AD9912, OUT5, channel 2, JP2-29, trigger 4, shutter 28
		5: AD9912, OUT5, channel 1, JP2-32, trigger 5, shutter 29
		6: AD9912, OUT6, channel 2, JP2-37, trigger 6, shutter 30
		7: AD9912, OUT6, channel 1, JP2-38, trigger 7, shutter 31
	DAC:
		8 Channels as labelled, trigger 8 is LDAC
	ADC:
		8 channels as labelled
	Counters:
		7:0, IN1, External
		15:8, IN2, External
		23:16, IN1, External (same as channels 7:0)
		31:24, IN1, External, timestamping
	Triggers in:
		7:0, IN3, External, Edge trigger
		7:0, IN3, External, Level trigger
	Serial Out:
		OUT2[7]
	PDH Auto Lock:
		Implemented on PI channel 0
		
IonControl-firmware-QGA
	ConfigurationId: 0x4202
	Breakout board: Sandia v2
	Shutters:
		7:0, OUT1, External
		14:8, OUT2, External
		15, OUT2[7], External, Serial output
		31:24, SMA[7:0], Rf switches, ACTIVE LOW
		39:32, internal, PI loop enable
		47:40, internal, DAC Scan Enable
	Triggers out:
		7:0, DDS
		8, LDAC
	DDS: 
		0: AD9912, OUT3, channel 2, JP2-31, trigger 0, shutter 24
		1: AD9912, OUT3, channel 1, JP2-34, trigger 1, shutter 25
		2: AD9912, OUT4, channel 2, JP2-30, trigger 2, shutter 26
		3: AD9912, OUT4, channel 1, JP2-33, trigger 3, shutter 27
		4: AD9912, OUT5, channel 2, JP2-29, trigger 4, shutter 28
		5: AD9912, OUT5, channel 1, JP2-32, trigger 5, shutter 29
		6: AD9912, OUT6, channel 2, JP2-37, trigger 6, shutter 30
		7: AD9912, OUT6, channel 1, JP2-38, trigger 7, shutter 31
	DAC:
		4 Channels as labelled, trigger 8 is LDAC, NOT operational
	ADC:
		4 channels as labelled
	Counters:
		7:0, IN1, External
		15:8, IN1, External
		23:16, IN1, External (same as channels 7:0)
		31:24, IN1, External, timestamping
	Triggers in:
		7:0, IN2, External, Edge trigger
		7:0, IN2, External, Level trigger
	Serial Out:
		OUT2[7]
	PDH Auto Lock:
		Not implemented
		