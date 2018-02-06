# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging
import random

import numpy

from modules import DataDirectory
from modules import enum
from modules.Expression import Expression
from modules.quantity import is_Q, Q

OpStates = enum.enum('idle', 'running', 'paused', 'starting', 'stopping', 'interrupted')

NoneScanCode = [4095, 0]  # TODO: should use the pulserconfiguration dataMemorySize
MaxWordsInFifo = 2040


class ScanGeneratorBase:
    def __init__(self, scan):
        self.scan = scan

    def xKey(self, index):
        return index % self.scan.singleScanLength

    @property
    def gateSequenceInfo(self):
        return {}

    def dataOnFinal(self, experiment, currentState):
        experiment.onStop()

    def xValue(self, index, data):
        return index % self.scan.singleScanLength

    def xRange(self):
        return []


class ParameterScanGenerator(ScanGeneratorBase):
    expression = Expression()

    def __init__(self, scan):
        super().__init__(scan)
        self.nextIndexToWrite = 0
        self.numUpdatedVariables = 1

    def prepare(self, pulseProgramUi, maxUpdatesToWrite=None):
        self.maxUpdatesToWrite = maxUpdatesToWrite
        if self.scan.gateSequenceUi.settings.enabled:
            _, data, self.gateSequenceSettings = self.scan.gateSequenceUi.gateSequenceScanData()    
        else:
            data = []
        parameterName = self.scan.scanParameter if self.scan.scanTarget == 'Internal' else self.scan.parallelInternalScanParameter
        if parameterName ==  "None":
            self.scan.code, self.numVariablesPerUpdate = NoneScanCode * len(self.scan.list), 1
        else:
            self.scan.code, self.numVariablesPerUpdate = pulseProgramUi.variableScanCode(parameterName, self.scan.list, extendedReturn=True)
        self.numUpdatedVariables = len(self.scan.code) // 2 // len(self.scan.list)
        if maxUpdatesToWrite is not None:
            maxWordsToWrite = 2 * self.numUpdatedVariables * maxUpdatesToWrite
            if len(self.scan.code) > maxWordsToWrite:
                self.nextIndexToWrite = maxWordsToWrite
                return self.scan.code[:maxWordsToWrite], data
        self.nextIndexToWrite = len(self.scan.code)
        return self.scan.code, data

    def restartCode(self, currentIndex):
        currentWordCount = 2 * self.numUpdatedVariables * currentIndex
        if self.maxUpdatesToWrite is not None:
            maxWordsToWrite = 2 * self.numUpdatedVariables * self.maxUpdatesToWrite
            if len(self.scan.code) - currentWordCount > maxWordsToWrite:
                self.nextIndexToWrite = maxWordsToWrite + currentWordCount
                return (self.scan.code[currentWordCount:self.nextIndexToWrite])
        self.nextIndexToWrite = len(self.scan.code)
        return self.scan.code[currentWordCount:]
        
    def xValue(self, index, data):
        value = self.scan.list[index]
        if self.scan.xExpression:
            value = self.expression.evaluate( self.scan.xExpression, {"x": value} )
        if not is_Q(value):
            return value
        if (not self.scan.xUnit and not value.dimensionless) or not value.dimensionality == Q(1, self.scan.xUnit).dimensionality:
            self.scan.xUnit = str(value.to_compact().units)
        return value.m_as(self.scan.xUnit)
        
    def dataNextCode(self, experiment ):
        if self.nextIndexToWrite<len(self.scan.code):
            start = self.nextIndexToWrite
            self.nextIndexToWrite = min( len(self.scan.code)+1, self.nextIndexToWrite + 2*self.numUpdatedVariables )
            return self.scan.code[start:self.nextIndexToWrite]
        return []
        
    def xRange(self):
        return self.scan.start.m_as(self.scan.xUnit), self.scan.stop.m_as(self.scan.xUnit)
                                     
    def appendData(self, traceList, x, evaluated, timeinterval):
        if evaluated and traceList:
            traceList[0].x.append(x)
            traceList[0].timeintervalAppend(timeinterval)
        for trace, (y, error, raw, valid) in zip(traceList, evaluated):
            trace.y.append(y)
            trace.raw.append(raw)
            if error is not None:
                trace.bottom.append(error[0])
                trace.top.append(error[1])


class StepInPlaceGenerator(ScanGeneratorBase):
    def __init__(self, scan):
        super().__init__(scan)
        
    def prepare(self, pulseProgramUi, maxUpdatesToWrite=None):
        if self.scan.gateSequenceUi.settings.enabled:
            _, data, self.gateSequenceSettings = self.scan.gateSequenceUi.gateSequenceScanData()    
        else:
            data = []
        self.scan.code = NoneScanCode # writing the last memory location
        return self.scan.code*50, data # write 5 points to the fifo queue at start,
                        # this prevents the Step in Place from stopping in case the computer lags behind evaluating by up to 5 points

    def restartCode(self, currentIndex):
        return self.scan.code * 50
        
    def dataNextCode(self, experiment):
        return self.scan.code
        
    def appendData(self, traceList, x, evaluated, timeinterval):
        steps = self.scan.maxPoints
        if evaluated and traceList:
            if len(traceList[0].x)<steps or steps==0:
                traceList[0].x.append(x)
                traceList[0].timeintervalAppend(timeinterval)
                for trace, (y, error, raw, valid) in zip(traceList, evaluated):
                    trace.y.append(y)
                    trace.raw.append(raw)
                    if error is not None:
                        trace.bottom.append(error[0])
                        trace.top.append(error[1])
            else:
                traceList[0].x = traceList[0].x[-steps+1:].append(x)
                traceList[0].timeintervalAppend(timeinterval, steps)
                for trace, (y, error, raw, valid) in zip(traceList, evaluated):
                    trace.y = trace.y[-steps+1:].append(y)
                    trace.raw = trace.raw[-steps+1:].append(raw)
                    if error is not None:
                        trace.bottom = trace.bottom[-steps+1:].append(error[0])
                        trace.top = trace.top[-steps+1:].append(error[1])


class FreerunningGenerator(ScanGeneratorBase):
    expression = Expression()
    def __init__(self, scan):
        super().__init__(scan)
        
    def prepare(self, pulseProgramUi, maxUpdatesToWrite=None):
        if self.scan.gateSequenceUi.settings.enabled:
            _, data, self.gateSequenceSettings = self.scan.gateSequenceUi.gateSequenceScanData()    
        else:
            data = []
        return ([], data) # write 5 points to the fifo queue at start,
                        # this prevents the Step in Place from stopping in case the computer lags behind evaluating by up to 5 points

    def restartCode(self, currentIndex):
        return []
        
    def dataNextCode(self, experiment):
        return None
        
    def xValue(self, index, data):
        return self.expression.evaluate( self.scan.xExpression, { 'x': data.scanvalue if data.scanvalue else 0} )  if self.scan.xExpression else data.scanvalue

    def appendData(self, traceList, x, evaluated, timeinterval):
        if evaluated and traceList:
            traceList[0].x.append(x)
            traceList[0].timeintervalAppend(timeinterval)
            for trace, (y, error, raw, valid) in zip(traceList, evaluated):
                trace.y.append(y)
                trace.raw.append(raw)
                if error is not None:
                    trace.bottom.append(error[0])
                    trace.top.append(error[1])


class GateSequenceScanGenerator(ScanGeneratorBase):
    def __init__(self, scan):
        super().__init__(scan)
        self.nextIndexToWrite = 0
        self.numUpdatedVariables = 1
        self.maxWordsToWrite = None
        
    def prepare(self, pulseProgramUi, maxUpdatesToWrite=None):
        logger = logging.getLogger(__name__)
        self.maxUpdatesToWrite = maxUpdatesToWrite
        address, data, self.gateSequenceSettings = self.scan.gateSequenceUi.gateSequenceScanData()
        parameter = self.gateSequenceSettings.startAddressParam
        logger.debug( "GateSequenceScan {0} {1}".format( address, parameter ) )
        self.scan.list = address * self.scan.repeats
        self.scan.singleScanLength = len(address)
        self.scan.index = list(range(len(self.scan.list)))
        if self.scan.scantype == 1:
            self.scan.list.reverse()
            self.scan.index.reverse()
        elif self.scan.scantype == 2:
            zipped = list(zip(self.scan.index, self.scan.list))
            random.shuffle(zipped)
            self.scan.index, self.scan.list = list(zip( *zipped ))
        self.scan.code = pulseProgramUi.pulseProgram.variableScanCode(parameter, self.scan.list)
        self.numVariablesPerUpdate = 1
        logger.debug( "GateSequenceScanCode {0} {1}".format(self.scan.list, self.scan.code) )
        if self.scan.gateSequenceSettings.debug:
            dumpFilename, _ = DataDirectory.DataDirectory().sequencefile("fpga_sdram.bin")
            with open( dumpFilename, 'wb') as f:
                f.write( bytearray(numpy.array(data, dtype=numpy.int32).view(dtype=numpy.int8)) )
            codeFilename, _ = DataDirectory.DataDirectory().sequencefile("start_address.txt")
            with open( codeFilename, 'w') as f:
                for a in self.scan.code[1::2]:
                    f.write( "{0}\n".format(a) )
            codeFilename, _ = DataDirectory.DataDirectory().sequencefile("start_address_sorted.txt")
            with open( codeFilename, 'w') as f:
                for index, a in enumerate(sorted(self.scan.code[1::2])):
                    f.write( "{0} {1}\n".format(index, a) )
        if self.maxWordsToWrite is not None:
            if len(self.scan.code) > self.maxWordsToWrite:
                self.nextIndexToWrite = self.maxWordsToWrite
                return (self.scan.code[:self.maxWordsToWrite], data)
        self.nextIndexToWrite = len(self.scan.code)
        return (self.scan.code, data)

    def restartCode(self, currentIndex):
        currentWordCount = 2 * self.numUpdatedVariables * currentIndex
        if self.maxWordsToWrite is not None:
            if len(self.scan.code) - currentWordCount > self.maxWordsToWrite:
                self.nextIndexToWrite = self.maxWordsToWrite + currentWordCount
                return (self.scan.code[currentWordCount:self.nextIndexToWrite])
        self.nextIndexToWrite = len(self.scan.code)
        return self.scan.code[currentWordCount:]

    def xValue(self, index, data):
        return self.scan.index[index % self.scan.singleScanLength]

    def dataNextCode(self, experiment):
        if self.nextIndexToWrite<len(self.scan.code):
            start = self.nextIndexToWrite
            self.nextIndexToWrite = min( len(self.scan.code)+1, self.nextIndexToWrite + 2*self.numUpdatedVariables )
            return self.scan.code[start:self.nextIndexToWrite]
        return []
        
    def xRange(self):
        return [0, len(self.scan.list)]

    def appendData(self, traceList, x, evaluated, timeinterval):
        if evaluated and traceList:
            traceList[0].x.append(x)
            traceList[0].timeintervalAppend(timeinterval)
        for trace, (y, error, raw, valid) in zip(traceList, evaluated):
            trace.y.append(y)
            trace.raw.append(raw)
            if error is not None:
                trace.bottom.append(error[0])
                trace.top.append(error[1])

    def xKey(self, index):
        return self.scan.gateSequenceUi.gateString(index % self.scan.singleScanLength)

    @property
    def gateSequenceInfo(self):
        try:
            return self.scan.gateSequenceUi.gateSequenceInfo
        except AttributeError:
            print(self.scan.gateSequenceUi, self.scan.gateSequenceUi.__class__)
            raise


GeneratorList = [ParameterScanGenerator, StepInPlaceGenerator, GateSequenceScanGenerator, FreerunningGenerator]   
