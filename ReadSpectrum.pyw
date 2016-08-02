# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from trace import Traceui
from trace import pens
import logging
from mylogging import LoggingSetup  #@UnusedImport

from PyQt5 import QtCore, QtGui
import PyQt5.uic
try:
    import visa  #@UnresolvedImport
except ImportError:
    logging.getLogger(__name__).error("Visa not present")

from modules import DataDirectory
from persist import configshelve 
from readInstrument import Read_E5100B
from readInstrument import Read_N9010A
from readInstrument import Read_N9342CN


instrumentmap = {
    'N9342CN' : Read_N9342CN.N9342CN,
    'N9344C' : Read_N9342CN.N9342CN,
    'E5100B' : Read_E5100B.E5100B,
    'N9010A' : Read_N9010A.N9010A
}

ReadSpectrumForm, ReadSpectrumBase = PyQt5.uic.loadUiType('ReadSpectrum.ui')

class ReadSpectrum( ReadSpectrumForm ):
    def __init__(self,config):
        self.Instruments = dict()
        self.TraceList = list()
        self.config = config
    
    def setupUi(self, MainWindow):
        ReadSpectrumForm.setupUi(self, MainWindow)
        MainWindow.connect(self.actionRead_Instrument, QtCore.SIGNAL('triggered ()'), self.onReadInstrument )
        MainWindow.connect(self.actionScan_Instruments, QtCore.SIGNAL('triggered ()'), self.onScanInstruments )
        MainWindow.connect(self.comboBoxInstruments, QtCore.SIGNAL('currentIndexChanged(int)'), self.onInstrumentSelect)
        QtCore.QTimer.singleShot(10,self.onScanInstruments)
        self.penicons = pens.penicons().penicons()
        self.traceui = Traceui.Traceui(self.penicons)
        self.traceui.setupUi(self.traceui)
        self.dockWidget.setWidget( self.traceui )
        if 'project' in config:
            self.Project.setText(config['project'])
        if 'filename' in config:
            self.Filename.setText(config['filename'])
        if 'plotnew' in config:
            self.checkBoxPlotNew.setChecked(config['plotnew'])
    
    def findDevices(self):
        self.statusbar.showMessage("Scanning for connected Instruments...")
        self.comboBoxInstruments.clear()
        rm = visa.ResourceManager()
        instrumentlist = rm.list_resources()
        for inst in instrumentlist:
            if (str.find(inst,"COM")!=0):
                try:
                    rm = visa.ResourceManager()
                    name = self.rm.open_resource( inst ).query("*IDN?").split(",")
                    self.Instruments.update( {inst : name} )
                    self.comboBoxInstruments.addItem(name[0]+" "+name[1],inst)
                except visa.VisaIOError as err:
                    print( "Ignore:", inst, err )
        if self.comboBoxInstruments.count()>0:
            self.onInstrumentSelect(0)
        self.statusbar.showMessage("Scan Instruments finished, "+str(self.comboBoxInstruments.count())+" found.")
                    
    def onScanInstruments(self):
        self.findDevices()
        
    def onInstrumentSelect(self,index):
        #print self.Instruments
        address = self.comboBoxInstruments.itemData(index)
        if address in self.Instruments:
            name = self.Instruments[address]
            #print "Instrument",name,address,"selected"
            self.Instrument = instrumentmap[name[1]](address)

    def onReadInstrument(self):
        self.statusbar.clearMessage()
        try:
            self.plot = Traceui.PlottedTrace( self.Instrument.readTrace(), self._graphicsView, pens.penList )
            self.StartFrequency.setText(self.plot.trace.varstr('Start'))
            self.StopFrequency.setText(self.plot.trace.varstr('Stop'))
            self.FrequencyStep.setText(self.plot.trace.varstr('Step'))
            self.ResolutionBandwidth.setText(self.plot.trace.varstr('ResolutionBandwidth'))
            self.VideoBandwidth.setText(self.plot.trace.varstr('VideoBandwidth'))
            self.Instrument.t.description["comment"] = str(self.Comment.text())
            self.onSaveTrace()
            if self.checkBoxPlotNew.isChecked():
                self.plot.plot(-1)
            
            self.traceui.addTrace(self.plot)
        except Exception as ex:
            self.statusbar.showMessage(str(ex))


    def onSaveTrace(self):
        try:
            project = self.Project.text()
            filename = self.Filename.text()
            if (project.length()>0 and filename.length()>0):
                path = DataDirectory.DataDirectory(str(project))
                self.plot.trace.filename , components  = path.sequencefile(str(filename))
                self.plot.trace.name = components[1]
                self.plot.trace.saveTrace(self.trace.filename)
                self.statusbar.showMessage("Wrote file: "+self.plot.trace.filename)
                print(self.plot.trace.name)
            config['project'] = project
            config['filename'] = filename
        except Exception as ex:
            self.statusbar.showMessage(str(ex))
                    
        

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    with configshelve.configshelve("ReadSpectrum") as config:
        ui = ReadSpectrum(config)
        ui.setupUi(MainWindow)
        MainWindow.show()
        sys.exit(app.exec_())
