# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from copy import deepcopy

import logging


class OverrideRecord:
    def __init__(self, state, shutters=None, globals=None, voltages=None, shuttle=True):
        self.state = state
        self.shutters = shutters if shutters else dict() # list of channel, value tuples
        self.globals = globals if globals else dict()  # list of name, value tuples
        self.voltages = voltages  # name of shuttling node or None
        self.shuttle = shuttle  # True: shuttle, False: instant

    def revertRecord(self, globalDict, shutterDict, shutter, voltageControl, revert=None):
        """Return an OverrideRecord which specifies how to undo the changes.

        This function first creates an OverrideRecord (o) which has the current value of the parameters that the current state
        will change. However, if the previous state had changed something that is also changed by this state, the current
        value is not the correct value to revert to at the end. Therefore, o is then updated with the contents of 'revert',
        which is another OverrideRecord which has the reversions that the previous state required."""
        try:
            o = OverrideRecord('-' + self.state,
                           globals=dict((name, globalDict[name]) for name in self.globals),
                           shutters=dict((name, bool(shutter & (1 << shutterDict.channel(name)))) for name in self.shutters),
                           voltages=voltageControl.currentShuttlingPosition() if self.voltages else None,
                           shuttle=self.shuttle)
            if revert is not None:
                o.globals.update((key, value) for key, value in revert.globals.items() if key in o.globals)
                o.shutters.update((key, value) for key, value in revert.shutters.items() if key in o.shutters)
                if revert.voltages is not None:
                    o.voltages = revert.voltages
                    o.shuttle = revert.shuttle
        except Exception as e:
            logging.getLogger(__name__).exception("Cannot apply setting in autoload {}".format(e))
        return o

    def update(self, other):
        self.shutters.update(other.shutters)
        self.globals.update(other.globals)
        if other.voltages:
            self.voltages = other.voltages
            self.shuttle = other.shuttle

    def setdefault(self, other):
        """Return a copy of the OverrideRecord, with the overrides updated according to the other OverrideRecord passed in."""
        updatedOverrideRecord = deepcopy(self)
        if other is not None:
            updatedOverrideRecord.globals.update((key, value) for key, value in other.globals.items() if key not in self.globals)
            updatedOverrideRecord.shutters.update((key, value) for key, value in other.shutters.items() if key not in self.shutters)
            if updatedOverrideRecord.voltages is None:
                updatedOverrideRecord.voltages = other.voltages
                updatedOverrideRecord.shuttle = other.shuttle
        return updatedOverrideRecord

    def apply(self, globalDict, shutterDict, pulser, voltageControl):
        try:
            for name, value in self.shutters.items():
                pulser.setShutterBit(shutterDict.channel(name), value)
            for name, value in self.globals.items():
                globalDict[name] = value
            if self.voltages is not None:
                     voltageControl.shuttleTo(self.voltages, onestep=not self.shuttle)
        except Exception as e:
            logging.getLogger(__name__).exception("Cannot apply setting in autoload {}".format(e))
