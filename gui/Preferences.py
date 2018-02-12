# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from pyqtgraph.parametertree import Parameter
from PyQt5 import QtCore, uic

from modules.AttributeComparisonEquality import AttributeComparisonEquality


class PrintPreferences(AttributeComparisonEquality):
    def __init__(self):
        self.printResolution = 1200
        self.printWidth = 0.4
        self.printX = 0.1
        self.printY = 0.1
        self.gridLinewidth = 8
        self.curveLinewidth = 8
        self.savePdf = False
        self.savePng = False
        self.doPrint = True
        self.saveSvg = True
        self.exportEmf = True
        self.exportWmf = True
        self.exportPdf = True
        self.inkscapeExecutable = r'C:\Program Files\Inkscape\inkscape.exe'
        self.gnuplotExecutable = r'C:\Program Files (x86)\gnuplot\\bin\pgnuplot.exe'
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('saveSvg', True)
        self.__dict__.setdefault('exportEmf', True)
        self.__dict__.setdefault('exportWmf', True)
        self.__dict__.setdefault('exportPdf', True)
        self.__dict__.setdefault('inkscapeExecutable', r'C:\Program Files\Inkscape\inkscape.exe')
        self.__dict__.setdefault('gnuplotExecutable', r'C:\Program Files (x86)\gnuplot\\bin\pgnuplot.exe')

    def paramDef(self):
        return [ {'name': 'resolution (dpi)', 'object': self, 'field': 'printResolution', 'type': 'int', 'value': self.printResolution},
                {'name': 'width (page width)', 'object': self, 'field': 'printWidth', 'type': 'float', 'value': self.printWidth},
                {'name': 'x (page width)', 'object': self, 'field': 'printX', 'type': 'float', 'value': self.printX}, 
                {'name': 'y (page height)', 'object': self, 'field': 'printY', 'type': 'float', 'value': self.printY},
                {'name': 'grid linewidth (px)', 'object': self, 'field': 'gridLinewidth', 'type': 'int', 'value': self.gridLinewidth},
                {'name': 'curve linewidth (px)', 'object': self, 'field': 'curveLinewidth', 'type': 'int', 'value': self.curveLinewidth},
               #{'name': 'save pdf', 'object': self, 'field': 'savePdf', 'type': 'bool', 'value': self.savePdf},
                {'name': 'print', 'object': self, 'field': 'doPrint', 'type': 'bool', 'value': self.doPrint},
                {'name': 'save svg', 'object': self, 'field': 'saveSvg', 'type': 'bool', 'value': self.saveSvg},
                {'name': 'export emf', 'object': self, 'field': 'exportEmf', 'type': 'bool', 'value': self.saveSvg},
                {'name': 'export wmf', 'object': self, 'field': 'exportWmf', 'type': 'bool', 'value': self.saveSvg},
                {'name': 'export pdf', 'object': self, 'field': 'exportPdf', 'type': 'bool', 'value': self.saveSvg},
                {'name': 'inkscape executable', 'object': self, 'field': 'inkscapeExecutable', 'type': 'str', 'value': self.inkscapeExecutable},
                {'name': 'gnuplot executable', 'object': self, 'field': 'gnuplotExecutable', 'type': 'str', 'value': self.gnuplotExecutable}]

class Preferences(AttributeComparisonEquality):
    def __init__(self):
        self.printPreferences = PrintPreferences()
        # persistence database
        
    def __setstate__(self, state):
        self.printPreferences = state.get('printPreferences', PrintPreferences())
               
    def paramDef(self):
        return [{'name': 'Print Preferences', 'type': 'group', 'children': self.printPreferences.paramDef() } ]
        

Form, Base = uic.loadUiType('ui/Preferences.ui')
        
class PreferencesUi(Form, Base):
    def __init__(self, config, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.config = config
        self._preferences = config.get('GlobalPreferences', Preferences())
    
    def setupUi(self, MainWindow):
        Form.setupUi(self, MainWindow)
        self.treeWidget.setParameters( self.parameter() )
 
    def update(self, param, changes):
        """
        update the parameter, called by the signal of pyqtgraph parametertree
        """
        for param, _, data in changes:
            setattr( param.opts['object'], param.opts['field'], data)

    def saveConfig(self):
        self.config['GlobalPreferences'] = self._preferences

    def parameter(self):
        # re-create the parameters each time to prevent a exception that says the signal is not connected
        self._parameter = Parameter.create(name='Preferences', type='group', children=self._preferences.paramDef())     
        self._parameter.sigTreeStateChanged.connect(self.update, QtCore.Qt.UniqueConnection)
        return self._parameter    
    
    def preferences(self):
        return self._preferences    
