import os
import sys

import Timing


sys.path.insert(0, os.path.abspath('..'))

#create the test object whcih will control the niSync card
test = Timing.Timing()

#write to the object's data to configure the niSync card
test.sampleRate = 100e3

try:
    #initialize will connect all clock and trigger terminals
    test.init('PXI1Slot2')

    #send a trigger programatically
    test.sendSoftwareTrigger()
    
#except Timing.niSyncError as e :
#    if e.code == -1073807240:
#        print 'Warning:'
#        print e
#    else:
#        raise


finally:
    #close when done with the object
    test.close()
