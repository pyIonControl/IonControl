"""
Created on 04 Dec 2015 at 1:49 PM

author: jmizrahi
"""

from modules.Expression import Expression

class VarAsOutputChannel(object):
    """This is a class that makes the AWG parameters work as an external parameter output channel in a parameter scan.

    The AWG variables are not external parameter output channels, but the external parameter scan method needs the scan
    parameter to have several specific methods and attributes (as OutputChannel does). This class provides those attributes."""
    expression = Expression()
    def __init__(self, awgUi, name, globalDict):
        self.awgUi = awgUi
        self.name = name
        self.useExternalValue = False
        self.savedValue = None
        self.globalDict = globalDict

    @property
    def value(self):
        return self.awgUi.settings.varDict[self.name]['value']

    @property
    def strValue(self):
        return self.awgUi.settings.varDict[self.name]['text']

    @property
    def device(self):
        return self.awgUi.device

    def saveValue(self, overwrite=True):
        """save current value"""
        if self.savedValue is None or overwrite:
            self.savedValue = self.value
        return self.savedValue

    def setValue(self, targetValue):
        """set the variable to targetValue"""
        if targetValue is not None:
            self.awgUi.settings.varDict[self.name]['value'] = targetValue
            modelIndex = self.awgUi.tableModel.createIndex(self.awgUi.settings.varDict.index(self.name), self.awgUi.tableModel.column.value)
            self.awgUi.tableModel.dataChanged.emit(modelIndex, modelIndex)
            for channelUi in self.awgUi.awgChannelUiList:
                channelUi.replot()
            self.device.program()
        return True

    def restoreValue(self):
        """restore the value saved previously, if any, then clear the saved value."""
        value = self.savedValue if self.strValue is None else self.expression.evaluateAsMagnitude(self.strValue, self.globalDict)
        if value is not None:
            self.setValue(value)
            self.savedValue = None
        return True