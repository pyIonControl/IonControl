# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from modules.Expression import Expression
from gui.ExpressionValue import ExpressionValue   #@UnresolvedImport


class AdjustValue(ExpressionValue):
    def __init__(self, name=None, line=0, globalDict=None):
        ExpressionValue.__init__(self, name, globalDict)
        self.line = line
        
    def __hash__(self):
        return hash(self.value)

