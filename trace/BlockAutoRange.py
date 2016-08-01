# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

class BlockAutoRange(object):
    def __init__(self, plotWidget):
        self.plotWidget = plotWidget

    def __enter__(self):
        self.autoRangeX, self.autoRangeY = self.plotWidget.autoRangeEnabled()
        return self.plotWidget

    def __exit__(self, type, value, traceback):
        self.plotWidget.enableAutoRange(x=self.autoRangeX, y=self.autoRangeY)
        self.plotWidget.autoRange()

class BlockAutoRangeList(object):
    def __init__(self, plotWidgetList):
        self.plotWidgetList = plotWidgetList

    def __enter__(self):
        self.autoRange = [p.autoRangeEnabled() for p in self.plotWidgetList]
        return self

    def __exit__(self, type, value, traceback):
        for autoRange, plotWidget in zip(self.autoRange, self.plotWidgetList):
            plotWidget.enableAutoRange(x=autoRange[0], y=autoRange[1])
            plotWidget.autoRange()