# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
class BlockAutoRange:
    """Encapsulate blockSignals in __enter__ __exit__ idiom"""
    def __init__(self, viewport):
        self._viewBox = viewport.getViewBox()

    def __enter__(self):
        self.oldstate = self._viewBox.autoRangeEnabled()
        self.holdZero = getattr(self._viewBox, 'holdZero', None)
        self._viewBox.enableAutoRange('xy', False)
        return self._viewBox

    def __exit__(self, exittype, value, traceback):
        if self.holdZero is not None:
            self._viewBox.holdZero = self.holdZero
        self._viewBox.enableAutoRange(x=self.oldstate[0])
        self._viewBox.enableAutoRange(y=self.oldstate[1])

