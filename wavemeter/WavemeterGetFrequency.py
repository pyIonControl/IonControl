# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import http.client


class WavemeterReadException(Exception):
    pass

class WavemeterGetFrequency(object):
    def __init__(self, address = "132.175.165.36:8082"):
        self.address = address
        self.nAttempts = 0
        self.nMaxAttempts = 100
        self.connection = http.client.HTTPConnection(self.address, timeout = 5)
        #self.connection.set_debuglevel(5)
        #print "Initialize WavemeterGetFrequency" 
        
    def __del__(self):
        self.connection.close()
        
    def get_frequency(self, channel):
        self.channel = channel
        try:
            requeststr = "/wavemeter/wavemeter/wavemeter-status?channel={0}".format( channel )
            self.connection.request("GET", requeststr )
            response = self.connection.getresponse()
            responsestring = response.read().strip()
        except Exception as e:
            print("Exception:", e)
            self.connection.close()
            self.connection = http.client.HTTPConnection(self.address, timeout = 50)
            self.nAttempts += 1
            if self.nAttempts == self.nMaxAttempts:
                raise WavemeterReadException("Wavemeter connection failed")
            else:
                return self.get_frequency(self.channel)
        else:
            self.nAttempts = 0
            frequency = float(responsestring)
            print("wavemeter response '{0}' {1}".format( responsestring, frequency ))
            return frequency
            
    def set_frequency(self, freq, channel):
        self.channel = channel
        try:
            self.connection.request("GET", "/wavemeter/wavemeter/wavemeter-status?channel=%d&course=%f" % (channel, freq))
            self.response = self.connection.getresponse()
        except:
            self.connection.close()
            self.connection = http.client.HTTPConnection(self.address, timeout = 50)
            self.nAttempts += 1
            if self.nAttempts == self.nMaxAttempts:
                return -1
            else:
                self.get_frequency(self.channel)
        else:
            self.nAttempts = 0
            return  float(self.response.read())       
##        try:
##            self.connection.request("GET", "/wavemeter/wavemeter/wavemeter-status?%d" % channel)
##            self.response = self.connection.getresponse()
##        except:
##            print "connection error"
##            return -1            
##        else:
##            if self.response.status == 200:#OK code
##                try:
##                    r = float(self.response.read())
##                except:
##                    print "bad wavemeter response: %s %s" % (self.response.status, self.response.reason)
##                    r = -1
##                return r
##            else:
##                print "bad server response: %s %s" % (self.response.status, self.response.reason)
##                return -1

if __name__ == '__main__':
    import timeit
    fg = WavemeterGetFrequency()
    def speed():
        print(fg.get_frequency(4))
    t = timeit.Timer("speed()", "from __main__ import speed")
    print(t.timeit(number = 10))
    del fg    
