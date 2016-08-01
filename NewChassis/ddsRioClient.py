# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from socket import socket, AF_INET, SOCK_STREAM

class ddsRioSocket(socket):
    def __init__(self):
        self.host = '192.138.33.101'
        self.port = 6431
        self._maxBufferSize = 1024
        self.rtn ='\r\n'
        self.verbosity = 0
        super(ddsRioSocket, self).__init__(AF_INET, SOCK_STREAM)

    def connect(self):
        print(self.host, self.port)
        super(ddsRioSocket, self).connect((self.host, self.port))
        data = super(ddsRioSocket, self).recv(self._maxBufferSize).strip()
        if self.verbosity:
            print('Connection String: {}'.format(data))
        connected = data.find('Welcome') == 0

    def sendReceive(self, data):
        self.send(data + self.rtn)
        if self.verbosity:
            print('Sent: {}'.format(data))
        received = self.recv(self._maxBufferSize).strip()
        if self.verbosity:
            print('Received: {}'.format(received))
        return received

    def close(self):
        received = self.sendReceive('exit')
        if self.verbosity:
            print('Close String: {}'.format(received))
        super(ddsRioSocket, self).close()


class ddsRioClient(object):
    def __init__(self):
        pass

    def _hexStr(self, data):
        return '%X' % data


class ddsRioNetClient(ddsRioClient):
    def __init__(self, address=''):
        super(ddsRioNetClient, self).__init__()
        self._socket = ddsRioSocket()
        self._socket.host = address
        self.registerNames = {
                0x00: 'PHASEADJ1',
                0X01: 'PHASEADJ2', 
                0x02: 'FREQTUNING1',
                0X03: 'FREQTUNING2',
                0x04: 'DELTAFREQ',
                0x05: 'UPDATECLK',
                0x06: 'RAMPRATECLK',
                0x07: 'CNTRLREG',
                0x08: 'OSKMULT',
                0x09: 'DCARE',
                0x0A: 'OSKRAMPRATE',
                0x0B: 'CNTRLDAC'
                }

    def _setAddress(self, value):
        self._socket.host = value

    def _getAddress(self):
        return self._socket.host

    address = property(_getAddress, _setAddress)

    def connect(self, address = None):
        if address:
            self.address = address
        self._socket.connect()

    def writeRegister(self, register, value):
        cmdName = 'dds:setreg '
        cmdParams = '{0},{1}'
        if isinstance(register, int):
            command = cmdName + cmdParams.format(self.registerNames[register], self._hexStr(value))
        elif isinstance(register, str):
            command = cmdName + cmdParams.format(register, self._hexStr(value))
        data = self._socket.sendReceive(command)
        done = data.find('Done') == 0

    def readRegister(self, register):
        cmdName = 'dds:getreg '
        cmdParams = '{0}'
        if isinstance(register, int):
            command = cmdName + cmdParams.format(self.registerNames[register])
        elif isinstance(register, str):
            command = cmdName + register
        data = self._socket.sendReceive(command)
        return int(data, 16)

    def writePhaseAdj1(self, data):
        self.writeRegister(0x00, data)

    def writePhaseAdj2(self, data):
        self.writeRegister(0x01, data)

    def writeFreqTuning1(self, data):
        self.writeRegister(0x02, data)

    def writeFreqTuning2(self, data):
        self.writeRegister(0x03, data)

    def writeDeltaFreq(self, data):
        self.writeRegister(0x04, data)

    def writeUpdateClk(self, data):
        self.writeRegister(0x05, data)

    def writeRampRateClk(self, data):
        self.writeRegister(0x06, data)

    def writeCntrlReg(self, data):
        self.writeRegister(0x07, data)

    def writeOskMult(self, data):
        self.writeRegister(0x08, data)

    def _writeDCare(self, data):
        self.writeRegister(0x09, data)

    def writeOskRampRate(self, data):
        self.writeRegister(0x0A, data)

    def writeCntrlDac(self, data):
        self.writeRegister(0x0B, data)

    def readPhaseAdj1(self):
        return self.readRegister(0x00)

    def readPhaseAdj2(self):
        return self.readRegister(0x01)

    def readFreqTuning1(self):
        return self.readRegister(0x02)

    def readFreqTuning2(self):
        return self.readRegister(0x03)

    def readDeltaFreq(self):
        return self.readRegister(0x04)

    def readUpdateClk(self):
        return self.readRegister(0x05)

    def readRampRateClk(self):
        return self.readRegister(0x06)

    def readCntrlReg(self):
        return self.readRegister(0x07)

    def readOskMult(self):
        return self.readRegister(0x08)

    def _readDCare(self):
        return self.readRegister(0x09)

    def readOskRampRate(self):
        return self.readRegister(0x0A)

    def readCntrlDac(self):
        return self.readRegister(0x0B)

    def readAll(self):
        for key in list(self.registerNames.keys()):
            data = client.readRegister(key)
            print('reg {0}: {1}'.format(client._hexStr(key), client._hexStr(data))) 

    def close(self):
        self._socket.close()

if __name__ == '__main__':
    try:
        client = ddsRioNetClient()
        client.connect('192.168.33.101')
        sock = client._socket
        client.readAll()
        '''
        for x in client.registerNames.keys():
            data = client.readRegister(x)
            print 'reg {0}: {1}'.format(client._hexStr(x), client._hexStr(data)) 
        '''
    finally:
        pass
        #client.close()
