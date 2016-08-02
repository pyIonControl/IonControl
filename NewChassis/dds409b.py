# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import visa

class novatech_409b(object):

    def __init__(self, alias = "409b"):
        self.dds = visa.instrument(alias, baud_rate=19200)
        self.dds.ask('E D')


    def set_frequency(self, freq, channel):
        cmd = 'f' + str(channel) + ' ' + str(freq)
        self.dds.ask(cmd)

    def set_amplitude(self, amp, channel):
        cmd = 'v' + str(channel) + ' ' + str(amp)
        self.dds.ask(cmd)

    def set_phase(self, phase, channel):
        cmd = 'p' + str(channel) + ' ' + str(phase)
        self.dds.ask(cmd)

    def get_frequency(self, channel):
        status = self.query()
        parsed = status.split('\n')
        return int( parsed[channel].split()[0], 16)/1e7

    def get_phase(self, channel):
        status = self.query()
        parsed = status.split('\n')
        return int( parsed[channel].split()[1], 16)

    def get_amplitude(self, channel):
        status = self.query()
        parsed = status.split('\n')
        return int( parsed[channel].split()[2], 16)

    def query(self):
        status = self.dds.ask('que')
        if status[0] == '\n':
            status = status[1:]
        for idx in range(4):
            status = status +  self.dds.read()
        return status


