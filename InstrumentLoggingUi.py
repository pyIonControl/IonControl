# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os

import logging
import sys

from notify.notification import NotificationCenter
from notify.notification_ui import NotificationUi

isPy3 = sys.version_info[0] > 2
if isPy3:
    from PyQt5 import QtCore, QtGui, QtWidgets
    import PyQt5.uic
else:
    from PyQt4 import QtCore, QtGui, QtWidgets
    import PyQt4.uic

from mylogging.ExceptionLogButton import ExceptionLogButton
from mylogging import LoggingSetup  #@UnusedImport
from modules import DataDirectory
from persist import configshelve
from uiModules import MagnitudeParameter #@UnusedImport
from pyqtgraph.exporters.ImageExporter import ImageExporter

from trace import Traceui
from trace import pens

from pyqtgraph.dockarea import DockArea, Dock
from uiModules.DateTimePlotWidget import DateTimePlotWidget
from externalParameter.InstrumentLogging import LoggingInstruments
from externalParameter.InstrumentLoggingSelection import InstrumentLoggingSelection
from externalParameter.InstrumentLoggingHandler import InstrumentLoggingHandler
from fit.FitUi import FitUi
from externalParameter.InstrumentLoggerQueryUi import InstrumentLoggerQueryUi
from externalParameter.InstrumentLoggingDisplay import InstrumentLoggingDisplay
from modules.SequenceDict import SequenceDict
from mylogging.LoggerLevelsUi import LoggerLevelsUi
from functools import partial
from gui.Preferences import PreferencesUi
from modules.SceneToPrint import SceneToPrint
from ProjectConfig.Project import Project, ProjectInfoUi
import ctypes
from persist import Timeseries

_ = Timeseries.TimeseriesPersist  # We want this imported

setID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID

WidgetContainerForm, WidgetContainerBase = PyQt5.uic.loadUiType(r'ui\InstrumentLoggingUi.ui')

class FinishException(Exception):
    pass

class InstrumentLoggingUi(WidgetContainerBase, WidgetContainerForm):
    levelNameList = ["debug", "info", "warning", "error", "critical"]
    levelValueList = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    plotConfigurationChanged = QtCore.pyqtSignal( object )
    def __init__(self, project, config):
        super(InstrumentLoggingUi, self).__init__()
        self.config = config
        self.project = project
        self.dockWidgetList = list()
        self.plotDict = dict()
        self.instrument = ""
        self.loggingLevel = config.get('Settings.loggingLevel', logging.INFO)
        self.consoleMaximumLines = config.get('Settings.consoleMaximumLinesNew', 100)
        self.consoleEnable = config.get('Settings.consoleEnable', False)
        self.printMenu = None
        if self.loggingLevel not in self.levelValueList: self.loggingLevel = logging.INFO
        
    def __enter__(self):
        return self
    
    def __exit__(self, excepttype, value, traceback):
        return False
    
    def setupUi(self, parent):
        super(InstrumentLoggingUi, self).setupUi(parent)
                
        self.dockWidgetConsole.hide()
        self.loggerUi = LoggerLevelsUi(self.config)
        self.loggerUi.setupUi(self.loggerUi)
        self.loggerDock = QtWidgets.QDockWidget("Logging")
        self.loggerDock.setWidget(self.loggerUi)
        self.loggerDock.setObjectName("_LoggerDock")
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.loggerDock)
        self.loggerDock.hide()

        logger = logging.getLogger()        
        self.toolBar.addWidget(ExceptionLogButton())

        # Notification center
        self.notificationCenter = NotificationCenter(subscriptions=self.config.get("NotificationSubscriptions"))
        self.notificationCenterUi = NotificationUi(self.notificationCenter)
        self.notificationCenterUi.setupUi(self.notificationCenterUi)
        self.notificationCenterDock = QtWidgets.QDockWidget("Notifications")
        self.notificationCenterDock.setObjectName("Notifications")
        self.notificationCenterDock.setWidget(self.notificationCenterUi)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.notificationCenterDock)
        self.notificationPeriodicTimer = QtCore.QTimer()
        self.notificationPeriodicTimer.timeout.connect(self.notificationCenter.periodicWork)
        self.notificationPeriodicTimer.start(180000)  # send rate limited pending messages every 3 minutes

        # Setup Console Dockwidget
        self.levelComboBox.addItems(self.levelNameList)
        self.levelComboBox.currentIndexChanged[int].connect( self.setLoggingLevel )            
        self.levelComboBox.setCurrentIndex( self.levelValueList.index(self.loggingLevel) )
        self.consoleClearButton.clicked.connect( self.onClearConsole )
        self.linesSpinBox.valueChanged.connect( self.onConsoleMaximumLinesChanged )
        self.linesSpinBox.setValue( self.consoleMaximumLines )
        self.checkBoxEnableConsole.stateChanged.connect( self.onEnableConsole )
        self.checkBoxEnableConsole.setChecked( self.consoleEnable )

        self.parent = parent
        self.tabDict = SequenceDict()
               
        self.setupPlots()     
        
        self.preferencesUi = PreferencesUi(config, self)
        self.preferencesUi.setupUi(self.preferencesUi)
        self.preferencesUiDock = QtWidgets.QDockWidget("Print Preferences")
        self.preferencesUiDock.setWidget(self.preferencesUi)
        self.preferencesUiDock.setObjectName("_preferencesUi")
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.preferencesUiDock)

          
        # Traceui
        self.penicons = pens.penicons().penicons()
        self.traceui = Traceui.Traceui(self.penicons, self.config, "Main", self.plotDict)
        self.traceui.setupUi(self.traceui)
        setattr(self.traceui, 'autoSaveTraces', self.config.get('autoSaveTraces', False))
        self.traceui.autoSaveAction = QtWidgets.QAction('Autosave traces', self.traceui)
        self.traceui.autoSaveAction.setCheckable(True)
        self.traceui.autoSaveAction.setChecked(self.traceui.autoSaveTraces)
        self.traceui.autoSaveAction.triggered.connect(lambda checked: setattr(self.traceui, 'autoSaveTraces', checked))
        self.traceui.addAction(self.traceui.autoSaveAction)
        traceuiDock = self.setupAsDockWidget(self.traceui, "Traces", QtCore.Qt.LeftDockWidgetArea)

        # new fit widget
        self.fitWidget = FitUi(self.traceui, self.config, "Main")
        self.fitWidget.setupUi(self.fitWidget)
        self.fitWidgetDock = self.setupAsDockWidget(self.fitWidget, "Fit", QtCore.Qt.LeftDockWidgetArea, stackBelow=traceuiDock)

        self.instrumentLoggingHandler = InstrumentLoggingHandler(self.traceui, self.plotDict, self.config,
                                                                 'externalInput', notifications=self.notificationCenter)

        self.ExternalParametersSelectionUi = InstrumentLoggingSelection(self.config, classdict=LoggingInstruments, plotNames=list(self.plotDict.keys()),
                                                                        instrumentLoggingHandler=self.instrumentLoggingHandler )
        self.ExternalParametersSelectionUi.setupUi( self.ExternalParametersSelectionUi )
        self.ExternalParameterSelectionDock = QtWidgets.QDockWidget("Params Selection")
        self.ExternalParameterSelectionDock.setObjectName("_ExternalParameterSelectionDock")
        self.ExternalParameterSelectionDock.setWidget(self.ExternalParametersSelectionUi)
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.ExternalParameterSelectionDock)
        self.instrumentLoggingHandler.paramTreeChanged.connect( self.ExternalParametersSelectionUi.refreshParamTree)
        self.instrumentLoggingHandler.setInputChannels( self.ExternalParametersSelectionUi.inputChannels() )
        self.ExternalParametersSelectionUi.inputChannelsChanged.connect( self.instrumentLoggingHandler.setInputChannels )
    
        self.instrumentLoggingDisplay = InstrumentLoggingDisplay(self.config)
        self.instrumentLoggingDisplay.setupUi( self.ExternalParametersSelectionUi.inputChannels(), self.instrumentLoggingDisplay )
        self.instrumentLoggingDisplayDock = QtWidgets.QDockWidget("Params Reading")
        self.instrumentLoggingDisplayDock.setObjectName("_ExternalParameterDisplayDock")
        self.instrumentLoggingDisplayDock.setWidget(self.instrumentLoggingDisplay)
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, self.instrumentLoggingDisplayDock)
        self.ExternalParametersSelectionUi.inputChannelsChanged.connect( self.instrumentLoggingDisplay.setupParameters )
        self.instrumentLoggingHandler.newData.connect( self.instrumentLoggingDisplay.update )

        self.instrumentLoggingQueryUi = InstrumentLoggerQueryUi(self.config, self.traceui, self.plotDict )
        self.instrumentLoggingQueryUi.setupUi( self.instrumentLoggingQueryUi )
        self.instrumentLoggingQueryUiDock = self.setupAsDockWidget(self.instrumentLoggingQueryUi, "Query", QtCore.Qt.LeftDockWidgetArea)
    
        self.addPlot = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/add-plot.png"), "Add new plot", self)
        self.addPlot.setToolTip("Add new plot")
        self.addPlot.triggered.connect(self.onAddPlot)
        self.toolBar.addAction(self.addPlot)
        
        self.removePlot = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/remove-plot.png"), "Remove a plot", self)
        self.removePlot.setToolTip("Remove a plot")
        self.removePlot.triggered.connect(self.onRemovePlot)
        self.toolBar.addAction(self.removePlot)

        self.renamePlot = QtWidgets.QAction( QtGui.QIcon(":/openicon/icons/rename-plot.png"), "Rename a plot", self)
        self.renamePlot.setToolTip("Rename a plot")
        self.renamePlot.triggered.connect(self.onRenamePlot)
        self.toolBar.addAction(self.renamePlot)

        self.setWindowTitle( "Instrument Logger ({0})".format(self.project) )
        if 'MainWindow.State' in self.config:
            self.parent.restoreState(self.config['MainWindow.State'])
        try:
            if 'pyqtgraph-dockareastate' in self.config:
                self.area.restoreState(self.config['pyqtgraph-dockareastate'])
        except Exception as e:
            logger.error("Cannot restore dock state in experiment {0}. Exception occurred: ".format(self.experimentName) + str(e))
        self.initMenu()
        self.actionProject.triggered.connect( self.onProjectSelection)
        self.actionExit.triggered.connect(self.onClose)
        self.actionSave.triggered.connect(self.onSave)

    def onProjectSelection(self):
        ui = ProjectInfoUi(self.project)
        ui.show()
        ui.exec_()

    def onEnableConsole(self, state):
        self.consoleEnable = state==QtCore.Qt.Checked
                
    def onClearConsole(self):
        self.textEditConsole.clear()
        
    def onConsoleMaximumLinesChanged(self, maxlines):
        self.consoleMaximumLines = maxlines
        self.textEditConsole.document().setMaximumBlockCount(maxlines)

    def setLoggingLevel(self, index):
        self.loggingLevel = self.levelValueList[index]
                   
    def setupPlots(self):
        self.area = DockArea()
        self.setCentralWidget(self.area)
        self.plotDict = dict()
        # initialize all the plot windows we want
        plotNames = self.config.get( 'PlotNames', ['Scan'] )
        if len(plotNames)<1:
            plotNames.append('Scan')
        for name in plotNames:
            dock = Dock(name)
            widget = DateTimePlotWidget(self, name=name)
            view = widget._graphicsView
            self.area.addDock(dock, "bottom")
            dock.addWidget(widget)
            self.plotDict[name] = {"dock":dock, "widget":widget, "view":view}
        
    def setupAsDockWidget(self, widget, name, area=QtCore.Qt.RightDockWidgetArea, stackAbove=None, stackBelow=None ):
        dock = QtWidgets.QDockWidget(name)
        dock.setObjectName(name)
        dock.setWidget( widget )
        self.addDockWidget(area, dock )
        self.dockWidgetList.append( dock )
        if stackAbove is not None:
            self.tabifyDockWidget( stackAbove, dock )
        elif stackBelow is not None:
            self.tabifyDockWidget( dock, stackBelow )
        return dock           

    def onAddPlot(self):
        name, ok = QtWidgets.QInputDialog.getText(self, 'Plot Name', 'Please enter a plot name: ')
        if ok:
            name = str(name)
            dock = Dock(name)
            widget = DateTimePlotWidget(self)
            view = widget._graphicsView
            self.area.addDock(dock, "bottom")
            dock.addWidget(widget)
            self.plotDict[name] = {"dock":dock, "widget":widget, "view":view}
            self.plotConfigurationChanged.emit( self.plotDict )
            
    def onRemovePlot(self):
        logger = logging.getLogger(__name__)
        if len(self.plotDict) > 0:
            name, ok = QtWidgets.QInputDialog.getItem(self, "Select Plot", "Please select which plot to remove: ", list(self.plotDict.keys()), editable=False)
            if ok:
                name = str(name)
                self.plotDict[name]["dock"].close()
                del self.plotDict[name]
                self.plotConfigurationChanged.emit( self.plotDict )
        else:
            logger.info("There are no plots which can be removed")
                
    def onRenamePlot(self):
        logger = logging.getLogger(__name__)
        if len(self.plotDict) > 0:
            name, ok = QtWidgets.QInputDialog.getItem(self, "Select Plot", "Please select which plot to rename: ", list(self.plotDict.keys()), editable=False)
            if ok:
                newName, newOk = QtWidgets.QInputDialog.getText(self, 'New Plot Name', 'Please enter a new plot name: ')
                if newOk:
                    name = str(name)
                    newName = str(newName)
                    self.plotDict[name]["dock"].label.setText(str(newName))
                    self.plotDict[newName] = self.plotDict[name]
                    del self.plotDict[name]
                    self.plotConfigurationChanged.emit( self.plotDict )
        else:
            logger.info("There are no plots which can be renamed")

    def onSave(self):
        logger = logging.getLogger(__name__)
        logger.info( "Saving config" )
        filename, _ = DataDirectory.DataDirectory().sequencefile("InstrumentLogger-configuration.db")
        self.saveConfig()
        self.config.saveConfig(filename)
    
    def onClose(self):
        self.parent.close()
        
    def onMessageWrite(self,message,level=logging.DEBUG):
        if self.consoleEnable and level>= self.loggingLevel:
            cursor = self.textEditConsole.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            if level < logging.ERROR:
                self.textEditConsole.setTextColor(QtCore.Qt.black)
            else:
                self.textEditConsole.setTextColor(QtCore.Qt.red)
            cursor.insertText(message)
            self.textEditConsole.setTextCursor(cursor)
            self.textEditConsole.ensureCursorVisible()

    def closeEvent(self, e):
        logger = logging.getLogger(__name__)
        logger.info( "Close Event" )
        logger = logging.getLogger("")
        logger.debug( "Saving Configuration" )
        self.saveConfig()

    def saveConfig(self):
        self.config['MainWindow.State'] = self.parent.saveState()
        for tab in list(self.tabDict.values()):
            tab.saveConfig()
        self.config['MainWindow.pos'] = self.pos()
        self.config['MainWindow.size'] = self.size()
        self.config['PlotNames'] = list(self.plotDict.keys())
        self.config['pyqtgraph-dockareastate'] = self.area.saveState()
        self.config['Settings.loggingLevel'] = self.loggingLevel
        self.config['Settings.consoleMaximumLinesNew'] = self.consoleMaximumLines
        self.config['Settings.consoleEnable'] = self.consoleEnable
        self.config['autoSaveTraces'] = self.traceui.autoSaveTraces
        self.ExternalParametersSelectionUi.saveConfig()
        self.instrumentLoggingHandler.saveConfig()
        self.instrumentLoggingQueryUi.saveConfig()
        self.preferencesUi.saveConfig()
        self.config["NotificationSubscriptions"] = self.notificationCenter.subscriptions

    def onPrint(self, target):
        printer = QtPrintSupport.QPrinter(mode=QtPrintSupport.QPrinter.ScreenResolution)
        if self.preferencesUi.preferences().printPreferences.doPrint:
            dialog = QtPrintSupport.QPrintDialog(printer, self)
            dialog.setWindowTitle("Print Document")
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return;    
        printer.setResolution(self.preferencesUi.preferences().printPreferences.printResolution)

        pdfPrinter = QtPrintSupport.QPrinter()
        pdfPrinter.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat);
        pdfPrinter.setOutputFileName(DataDirectory.DataDirectory().sequencefile(target+".pdf")[0])
        self.doPrint(target, printer, pdfPrinter, self.preferencesUi.preferences().printPreferences)

    def doPrint(self, target, printer, pdfPrinter, preferences):
        widget = self.plotDict[target]['widget']
        if preferences.savePdf:
            with SceneToPrint(widget):
                painter = QtGui.QPainter(pdfPrinter)
                widget.render( painter )
                del painter
        
        # create an exporter instance, as an argument give it
        # the item you wish to export
        with SceneToPrint(widget, preferences.gridLinewidth, preferences.curveLinewidth):
            exporter = ImageExporter(widget._graphicsView.scene()) 
      
            # set export parameters if needed
            pageWidth = printer.pageRect().width()
            pageHeight = printer.pageRect().height()
            exporter.parameters()['width'] = pageWidth*preferences.printWidth   # (note this also affects height parameter)
              
            # save to file
            png = exporter.export(toBytes=True)
            if preferences.savePng:
                png.save(DataDirectory.DataDirectory().sequencefile(target+".png")[0])
            
            if preferences.doPrint:
                painter = QtGui.QPainter( printer )
                painter.drawImage(QtCore.QPoint(pageWidth*preferences.printX, pageHeight*preferences.printY), png)

    def initMenu(self):
        """Initialize print menu and view menu"""
        #View menu
        self.menuView.clear()
        dockList = self.findChildren(QtWidgets.QDockWidget)
        for dock in dockList:
            self.menuView.addAction(dock.toggleViewAction())

        # Print menu
        if self.printMenu is not None:
            self.printMenu.clear()
        else:
            self.printMenu = self.menuFile.addMenu("Print")
        for plot in list(self.plotDict.keys()):
            action = self.printMenu.addAction( plot )
            action.triggered.connect( partial(self.onPrint, plot ))
       

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    project = Project()
    logger = logging.getLogger("")
    setID('TrappedIons.InstrumentLogging') #Makes the icon in the Windows taskbar match the icon set in Qt Designer

    overrideConfigFile = project.projectConfig.get('configurationFile')
    overrideFileType = {'.yml': 'yaml', '.yaml': 'yaml', '.db': 'sqlite'}.get(os.path.splitext(overrideConfigFile)[1], 'sqlite') if overrideConfigFile else None
    loadFromDate = project.projectConfig.get('configurationFile')
    with configshelve.configshelve(project.dbConnection, loadFromDate=project.projectConfig.get('loadFromDateTime', None),
                                   filename=overrideConfigFile, filetype=overrideFileType) as config:
        with InstrumentLoggingUi(project, config) as ui:
            ui.setupUi(ui)
            LoggingSetup.qtHandler.textWritten.connect(ui.onMessageWrite)
            ui.show()
            sys.exit(app.exec_())