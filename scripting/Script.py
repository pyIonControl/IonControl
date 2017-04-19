# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import os
from PyQt5 import QtCore
import inspect
import traceback
import time
from pathlib import Path

class ScriptException(Exception):
    pass

class Script(QtCore.QThread):
    """Encapsulates a running script together with all the scripting functions. Script executes in separate thread.
    
    The script behavior is as follows: each script function that manipulates a GUI element does so by emitting a
    signal, followed by entering  QWaitCondition. The ScriptHandler responds to the signal, and wakes up the 
    QWaitCondition. For access to GUI data, the script waits at a QWaitCondition until the data is available.
    When the data is available, the ScriptHandler sets the script data variables appropriately, and then wakes the
    wait condition. This back-and-forth handoff between the Script thread and the ScriptHandler (which lives in the
    main GUI thread) is what ensures synchronicity and avoids race conditions.

    Note that the script thread does not have an event loop. This means that it cannot respond to emitted signals,
    and calls like Script.quit and Script.exit do not work. Instead, the script emits signals indicating what to
    change, and then enters a QWaitCondition. The ScriptingUi responds to the signal, and tells the script to exit
    the wait condition once the action has been done. 
    
    All the script functions are executed via the script function decorator, which simplifies the code.

    Args:
        fullname (str): full path to script
        code (str): code in the script
        parent (QObject): parent QObject, if any

    """
    #Signals to send information to the main thread
    locationSignal = QtCore.pyqtSignal(list)  # arg: trace locations corresponding to the script
    consoleSignal = QtCore.pyqtSignal(str, bool, str) #args: String to write, True if no error occurred, color to use
    exceptionSignal = QtCore.pyqtSignal(str, str) #args: exception message, traceback
    
    #Signals to send instructions to the main thread
    pauseScriptSignal = QtCore.pyqtSignal()
    stopScriptSignal = QtCore.pyqtSignal()
    pauseScanSignal = QtCore.pyqtSignal()
    stopScanSignal = QtCore.pyqtSignal()
    
    setGlobalSignal = QtCore.pyqtSignal(str, float, str) #args: name, value, unit
    addGlobalSignal = QtCore.pyqtSignal(str, float, str) #args: name, value, unit
    startScanSignal = QtCore.pyqtSignal(list)  # args: globalOverrides list
    setScanSignal = QtCore.pyqtSignal(str) #arg: scan name
    setEvaluationSignal = QtCore.pyqtSignal(str) #arg: evaluation name
    setAnalysisSignal = QtCore.pyqtSignal(str) #arg: analysis name
    plotPointSignal = QtCore.pyqtSignal(float, float, str, int) #args: x, y, tracename, plotStyle
    plotListSignal = QtCore.pyqtSignal(list, list, str, bool, int) #args: xList, yList, tracename, overwrite, plotStyle
    addPlotSignal = QtCore.pyqtSignal(str) #arg: plot name
    abortScanSignal = QtCore.pyqtSignal()
    createTraceSignal = QtCore.pyqtSignal(list) #arg: trace creation data
    closeTraceSignal = QtCore.pyqtSignal(str) #arg: trace to close
    fitSignal = QtCore.pyqtSignal(str, str) #args: fitName, traceName
    genericCallSignal = QtCore.pyqtSignal(str, object, object) #args: function name, argument tuple, keyword argument dict
    consolePrintSignal = QtCore.pyqtSignal(str, bool, str) #args: String to write, True if no error occurred, color to use
    setAWGSignal = QtCore.pyqtSignal(str, str) #args: AWG name, AWG settings name
    programAWGSignal = QtCore.pyqtSignal(str) #arg: AWG name
    namedTraceSignal = QtCore.pyqtSignal(str, str, int, float, str, bool) #args: top node, child node, row, data and column (x or y), ignore trailing nans when appending (bool)
    loadVoltageDefSignal = QtCore.pyqtSignal(str,str) #args: file name (sans '.txt'), path

    def __init__(self, fullname=Path(), code='', parent=None, homeDir=Path()):
        super(Script, self).__init__(parent)
        self.fullname = fullname
        self.code = code
        self.dispfull = True #display local paths in filenameComboBox
        self.homeDir = homeDir
        
        self.mutex = QtCore.QMutex() #used to control access to class variables that are accessed by ScriptHandler
        
        self.pauseWait = QtCore.QWaitCondition() #Used to wait while script is paused
        self.scanWait = QtCore.QWaitCondition() #Used to wait for end of scan
        
        self.dataWait = QtCore.QWaitCondition() #Used to wait for single data point
        self.allDataWait = QtCore.QWaitCondition() #Used to wait for full data set
        self.analysisWait = QtCore.QWaitCondition() #Used to wait for analysis results
        self.guiWait = QtCore.QWaitCondition() #Used to wait for gui to execute command
        self.genericWait = QtCore.QWaitCondition() #Used to wait for generic data to be set

        for name in scriptFunctions: #Define global functions corresponding to the scripting functions
            globals()[name] = getattr(self, name)
        
        #Below are all class elements that are modified directly during operation by ScriptHandler
        #All access to these parameters is mutex protected while the script is running
        
        #parameters that control the script execution process
        self.repeat = False
        self.paused = False
        self.stopped = False
        self.slow = False
        
        #parameters that control synchronization with the gui
        self.scanStatus = 'idle'
        self.scanIsRunning = False
        self.waitOnScan = False
        self.analysisReady = False
        self.allDataReady = False
        self.dataReady = False

        #parameters to send information from the gui to the script
        self.analysisResults = dict()
        self.fitResults = dict()
        self.genericResult = None
        self.data = dict()
        self.allData = dict()
        self.exception = None

    @QtCore.pyqtProperty(str)
    def shortname(self):
        if self.dispfull:
            return self.localpathname
        return self.filename

    @QtCore.pyqtProperty(str)
    def filename(self):
        return str(self.fullname.name)

    @QtCore.pyqtProperty(str)
    def localpathname(self):
        return str(self.fullname.relative_to(self.homeDir).as_posix())

    def run(self):
        """run the script"""
        try:
            d = dict(locals(), **globals()) #Executing in this scope allows a function defined in the script to call another function defined in the script
            while True:
                exec(compile(open(str(self.fullname)).read(), str(self.fullname), 'exec'), d, d) #run the script
                if not self.repeat:
                    break
        except Exception as e:
            trace = traceback.format_exc()
            with QtCore.QMutexLocker(self.mutex):
                self.exceptionSignal.emit(type(e).__name__+": " + str(e), trace)

    def emitLocation(self):
        """Emits a signal containing the current script location"""
        frame = inspect.currentframe()
        stack_trace = traceback.extract_stack(frame) #Gets the full stack trace
        del frame #Getting rid of captured frames is recommended
        locs = [loc for loc in stack_trace if loc[0] == str(self.fullname)] #Find the locations that match the script name
        self.locationSignal.emit(locs)

    def scriptFunction(waitForGui=True, waitForAnalysis=False, waitForData=False, waitForAllData=False,
                       runIfStopped=False): #@NoSelf
        """Decorator for script functions.
        
        This decorator performs all the functions that are common to all the script functions. It checks
        whether the script has been stopped or paused, and emits the current location in the script. Once
        the function has executed, it waits to be told to continue by the main GUI. Exceptions that occur
        during execution are sent back to the script thread and raised here.

        Args:
            waitForGui (Optional[bool]): defaults to True. If True, script waits on guiWait after executing function.
            waitForAnalysis (Optional[bool]): defaults to False. If True, script waits on analysisWait before executing function.
            waitForData (Optional[bool]): defaults to False. If True, script waits on dataWait before executing function.
            waitForAllData (Optional[bool]): defaults to False. If True, script waits on allDataWait before executing function.
            runIfStopped (Optional[bool]): defaults to False. If True, function executes even if the script has been stopped."""
        def realScriptFunction(func):
            """The decorator without arguments (returned by the decorator with arguments)"""
            def baseScriptFunction(self, *args, **kwds):
                """The base script function that wraps all the other script functions"""
                with QtCore.QMutexLocker(self.mutex): #Acquire mutex before inspecting any variables
                    if (not self.stopped) or (self.stopped and runIfStopped): #if stopped, don't do anything
                        if self.scanIsRunning and self.waitOnScan:
                            self.scanWait.wait(self.mutex)
                        if self.paused:
                            self.pauseWait.wait(self.mutex)
                        self.emitLocation()
                        if self.slow:
                            self.mutex.unlock()
                            time.sleep(0.4) #On slow, we wait on each line for 0.4 s 
                            self.mutex.lock() 
                        if waitForAnalysis and not self.analysisReady:
                            self.analysisWait.wait(self.mutex)
                        if waitForAllData and not self.allDataReady:
                            self.allDataWait.wait(self.mutex)
                        if waitForData and not self.dataReady:
                            self.dataWait.wait(self.mutex)
                        returnData = func(self, *args, **kwds) #This is the actual function
                        if waitForGui:
                            self.guiWait.wait(self.mutex)
                        if self.exception:
                            raise self.exception
                        return returnData
            baseScriptFunction.isScriptFunction = True
            baseScriptFunction.__name__ = func.__name__
            baseScriptFunction.__doc__ = func.__doc__
            return baseScriptFunction
        return realScriptFunction

    @scriptFunction(waitForGui=False)
    def consolePrint(self, message, error=False, color=''):
        """consolePrint(message, error=False, color=''):
        write a message to the console.

        Args:
            message (str): the message to print
            error (bool): If True, message prints in red
            color (str): color to print in if error is False, HTML color names accepted
        """
        self.consolePrintSignal.emit(str(message), error, color)

    @scriptFunction()
    def setGlobal(self, name, value, unit):
        """setGlobal(name, value, unit)
        set global 'name' to (value, unit).

        This is equivalent to typing in a value/unit in the globals table.

        Args:
            name (str): name of the global to change
            value (float): value to set it to
            unit (str): unit to use

        Raises:
            ScriptException: if there is not a global with the given name. This is to avoid typos leading to unexpected behavior. To add a global, use 'addGlobal'"""
        self.setGlobalSignal.emit(name, value, unit)

    @scriptFunction(waitForGui=False)
    def getGlobal(self, name):
        """getGlobal(name)
        get current value of global 'name'"""
        self.genericCallSignal.emit('getGlobal', (name,), dict())
        self.genericWait.wait(self.mutex)
        if isinstance(self.genericResult, ScriptException):
            self.exception = self.genericResult
        return self.genericResult

    @scriptFunction()
    def addGlobal(self, name, value, unit):
        """addGlobal(name, value, unit)
        add a global 'name', set to (value, unit).     
         
        This is equivalent to adding a global via the globals UI,and then setting its value in the globals table.
        
        Args:
            name (str): name of the global to add
            value (float): value to set it to
            unit (str): unit to use"""
        self.addGlobalSignal.emit(name, value, unit)
        
    @scriptFunction()
    def pauseScript(self):
        """pauseScript()
        Pause the script.
        
        This is equivalent to clicking the "pause script" button."""
        self.pauseScriptSignal.emit()
        
    @scriptFunction()
    def stopScript(self):
        """stopScript()
        Stop the script.
        
        This is equivalent to clicking the "stop script" button."""
        self.stopScriptSignal.emit()

    @scriptFunction()
    def startScan(self, globalOverrides=list(), wait=True):
        """startScan(globalOverrides=list(), wait=True)
        Start the scan.
        
        This is equivalent to clicking "start" on the experiment GUI.
        Optionally a list of (name, magnitude) tuples or (name, (value, unit)) tuples
        can be given that overrides global variables during the scan.
        If wait=True, the script will not continue until the scan is finished.

        globalOverrides: list((name, value)) or list((name, (value, unit)))
        wait: bool"""
        self.waitOnScan = wait
        self.startScanSignal.emit(globalOverrides)
        
    @scriptFunction()
    def setScan(self, name):
        """setScan(name)
        set the scan settings to "name."
        
        This is equivalent to selecting "name" from the scan settings drop down menu.

        Args:
            name (str): name of the scan settings to set

        Raises:
            ScriptException: if there is no scan by that name"""
        self.setScanSignal.emit(name)

    @scriptFunction()
    def setAWG(self, awgName, name):
        """setAWG(awgName, name)
        set the AWG (named "awgName") settings to "name."

        This is equivalent to selecting "name" from the AWG settings drop down menu.

        Args:
            name (str): name of the AWG settings to set

        Raises:
            ScriptException: if there is no AWG settings by that name"""
        self.setAWGSignal.emit(awgName, name)

    @scriptFunction()
    def programAWG(self, awgName):
        """programAWG(awgName)
        Program the AWG named "awgName".

        This is equivalent to clicking "program AWG"
        """
        self.programAWGSignal.emit(awgName)

    @scriptFunction()
    def setEvaluation(self, name):
        """setEvaluation(name)
        set the evaluation settings to "name."
        
        This is equivalent to selecting "name" from the evaluation settings drop down menu.

        Args:
            name (str): name of the evaluation settings to set

        Raises:
            ScriptException: if there is no evaluation by that name"""
        self.setEvaluationSignal.emit(name)
     
    @scriptFunction()
    def setAnalysis(self, name):
        """setAnalysis(name)
        set the analysis settings to "name."
        
        This is equivalent to selecting "name" from the analysis settings drop down menu.

        Args:
            name (str): name of the analysis settings to set

        Raises:
            ScriptException: if there is no analysis by that name"""
        self.setAnalysisSignal.emit(name)

    @scriptFunction()
    def plotPoint(self, x, y, traceName, plotStyle=-1):
        """plotPoint(x, y, traceName, plotStyle=-1)
        Plot a single point (x, y) to trace traceName.

        Args:
            x (float): x coordinate
            y (float): y coordinate
            traceName (str): name of trace to use
            plotStyle (int): plot with lines, points, etc...
                        0: lines
                        1: points
                        2: linespoints
                        3: lines errors
                        4: points errors
                        5: linespoints errors
                otherwise: GUI default

        Raises:
            ScriptException: if traceName is not a trace"""
        self.plotPointSignal.emit(x, y, traceName, plotStyle)

    @scriptFunction()
    def plotList(self, xList, yList, traceName, overwrite=False, plotStyle=-1):
        """plotList(xList, yList, traceName, overwrite=False, plotStyle=-1)
        Plot a set of points given in xList, yList to trace traceName.

        Args:
            x (list[float]): x coordinates
            y (list[float]): y coordinates
            traceName (str): name of trace to use
            overwrite (bool): if True, overwrite existing data
            plotStyle (int): plot with lines, points, etc...
                        0: lines
                        1: points
                        2: linespoints
                        3: lines errors
                        4: points errors
                        5: linespoints errors
                otherwise: GUI default

        Raises:
            ScriptException: if traceName is not a trace
            ScriptException: if x and y are of unequal lengths"""
        if type(xList).__module__ == 'numpy':
            xList = xList.tolist()
        if type(yList).__module__ == 'numpy':
            yList = yList.tolist()
        self.plotListSignal.emit(xList, yList, traceName, overwrite, plotStyle)
        
    @scriptFunction()
    def addPlot(self, name):
        """addPlot(name)
        Add a plot named "name".
         
        This is equivalent to clicking "add plot" on the experiment GUI. If 'name' already exists, does nothing.
        
        Args:
            name (str): name of plot to add"""
        self.addPlotSignal.emit(name)

    @scriptFunction()
    def pauseScan(self):
        """pauseScan()
        Pause the scan.
        
        This is equivalent to clicking "pause" on the experiment GUI."""
        self.pauseScanSignal.emit()
        
    @scriptFunction()
    def stopScan(self):
        """stopScan()
        Stop the scan.
        
        This is equivalent to clicking "stop" on the experiment GUI."""
        self.stopScanSignal.emit()
    
    @scriptFunction()  
    def abortScan(self):
        """abortScan()
        Abort the scan.
        
        This is equivalent to clicking "abort" on the experiment GUI."""
        self.abortScanSignal.emit()
        
    @scriptFunction()
    def createTrace(self, traceName, plotName, xUnit='', xLabel='', comment=''):
        """createTrace(traceName, plotName, xUnit='', xLabel='', comment='')
        create a new trace

        Args:
            traceName (str): name of new trace
            plotName (str): plot to plot it on
            xUnit (str): unit for x axis
            xLabel (str): label for x axis
            comment (str): comment for trace file

        Raises:
            ScriptException: if plotName is not a plot"""
        traceCreationData = [traceName, plotName, xUnit, xLabel, comment]
        self.createTraceSignal.emit(traceCreationData)

    @scriptFunction()
    def closeTrace(self, traceName):
        """closeTrace(traceName)
        Finalize trace. Registers in the measurement log and saves. No new data can be added to the trace.

        If this function is not called on a trace, it will be closed automatically when the script ends.

        Args:
            traceName (str): name of trace to close
        """
        self.closeTraceSignal.emit(traceName)

    @scriptFunction()
    def fit(self, fitName, traceName):
        """fit(fitName, traceName)
        Fit trace using specified fit.
        Args:
            traceName (str): name of trace to fit
            fitName (str): name of fit settings to use (from fit GUI)
        """
        self.fitSignal.emit(fitName, traceName)

    @scriptFunction()
    def loadVoltageDef(self, fileName, path=''):
        """loadVoltageDef(fileName, path='')
        Load a waveform and its associated shuttling.xml file.
        Args:
            fileName (str): name of waveform including the '.txt'
            path (str): path to the fileName
        """
        self.loadVoltageDefSignal.emit(fileName, path)

    @scriptFunction(waitForGui=False)
    def waitForScan(self):
        """waitForScan()
        Wait for scan to finish before continuing script.
        
        If startScan is run with wait=True, this function is unnecessary."""
        self.waitOnScan = True
    
    @scriptFunction(waitForGui=False, waitForData=True)
    def getData(self):
        """getData()
        Get the most recent data point from a running scan.

        Returns:
            dict: data from running scan. **key**: the name of each evaluation in the evaluation list. **val**: tuple (x, y)."""
        self.dataReady = False
        return self.data

    @scriptFunction(waitForGui=False, waitForAllData=True)
    def getAllData(self):
        """getAllData()
        Get the full set of data from the most recent scan.
        
        Returns:
            dict: all data from most recent scan. **key**: name of each evaluation in the evaluation list. **val**: tuple (xList, yList)."""
        self.allDataReady = False
        return self.allData

    @scriptFunction(waitForGui=False, waitForAnalysis=True)
    def getAnalysis(self):
        """getAnalysis()
        Get the analysis results for the most recent scan.
        
        Returns:
            dict: analysis results as dictionary of dictionaries. **key**: to the name of each analysis in the analysis list. **val**: Another dictionary. **Inner key**: names of fit parameters in the specified evaluation. **Inner val**: fit value of that parameter
        
        Example:
            A Gaussian fit named "myFit" in the analysis, with center parameter 'x0', would return its best fit center value as::

        getAnalysis()['myFit']['x0']"""
        self.analysisReady = False
        return self.analysisResults

    @scriptFunction(waitForGui=False)
    def getFit(self):
        """getFit()
        Get the fit results for the most recent scan.

        Returns:
            dict: fit results as dictionary. **key**: to the name of the parameter **val**: fit value of that parameter

        Example:
            A Gaussian fit named "myFit" in the analysis, with center parameter 'x0', would return its best fit center value as::

        getFit['x0']"""
        return self.fitResults

    @scriptFunction(waitForGui=False)
    def scanRunning(self):
        """scanRunning()
        Determine if scan is running.

        Returns:
            bool: True if the scan is running. Otherwise, False."""
        return self.scanIsRunning
    
    @scriptFunction(waitForGui=False)
    def getScanStatus(self):
        """getScanStatus()
        Return the current state of the scan.

        Returns:
            str: One of 'idle', 'running', 'paused', 'starting', 'stopping', or 'interrupted'"""
        return self.scanStatus
        
    @scriptFunction(waitForGui=False, runIfStopped=True)
    def scriptIsStopped(self):
        """scriptIsStopped()
        Determine if script is stopped.

        Returns:
            bool: True if the script has been stopped, Otherwise, False."""
        return self.stopped

    @scriptFunction(waitForGui=False)
    def pushToNamedTrace(self, topNode, child, row, data, col='y', ignoreTrailingNaNs=True):
        """pushToNamedTrace(topNode, child, index, data, col='y', ignoreTrailingNaNs=True)
        Push data to a Named Trace at a specified index. If the index is longer than the Named Trace, the trace will
        be padded with NaNs.

        col specifies x or y data but can be a trace column dict key if desired. Currently supported column names are:
            - 'x'   :: x axis data
            - 'y'   :: y axis data
            - 'top' :: upper bound error bar value
            - 'bottom' :: lower bound error bar value
            - 'height' :: symmetric error bar value (takes precedence over top and bottom)

        If row = -1, data will be appended to the Named Trace. When ignoreTrailingNaNs is True, appended data
        will be added after the last number and ignore trailing NaNs. When ignoreTrailingNaNs is False, data will
        be appended after the trailing NaNs.

        Returns:
            bool: True"""
        self.namedTraceSignal.emit(topNode, child, row, data, col, ignoreTrailingNaNs)
        return True

def checkScripting(func):
    """Check whether a function has been marked as a script function"""
    return hasattr(func, 'isScriptFunction')

scriptFunctions = [a[0] for a in inspect.getmembers(Script, checkScripting)] #Get the names of the scripting functions
scriptDocs = [getattr(Script, name).__doc__ for name in scriptFunctions] #Get the doc strings