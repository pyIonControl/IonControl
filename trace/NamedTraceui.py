# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from trace import Traceui
from gui import TraceTableEditor
from PyQt5 import QtGui, QtCore, QtWidgets
from functools import partial
from trace.BlockAutoRange import BlockAutoRangeList
import expressionFunctions.ExprFuncDecorator as trc

class Settings(Traceui.Settings):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.filelist = []

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('unplotLastTrace', True)
        self.__dict__.setdefault('collapseLastTrace', False)
        self.__dict__.setdefault('expandNew', True)
        self.__dict__.setdefault('filelist', [])

class NamedTraceui(Traceui.Traceui):
    externalUpdate = QtCore.pyqtSignal()
    def __init__(self, penicons, config, experimentName, graphicsViewDict, parent=None, lastDir=None, hasMeasurementLog=False, highlightUnsaved=False, preferences=None):
        super().__init__(penicons, config, experimentName, graphicsViewDict, parent, lastDir, hasMeasurementLog, highlightUnsaved, preferences=preferences)
        self.penicons = penicons
        self.config = config
        self.configname = "NamedTraceui."+experimentName
        self.settings = self.config.get(self.configname+".settings", Settings(lastDir=lastDir, plotstyle=0))
        self.graphicsViewDict = graphicsViewDict
        self.hasMeasurementLog = hasMeasurementLog
        self.highlightUnsaved = highlightUnsaved
        self.newDataAvailable = False

    def setupUi(self, *args):
        super().setupUi(*args)
        self.model.flagsLookup[self.model.column.name] = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
        self.model.categoryFlagsLookup[self.model.column.name] = QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
        self.model.dataLookup.update({
            (QtCore.Qt.DisplayRole, self.model.column.name): lambda node: node.content.name,
            (QtCore.Qt.EditRole, self.model.column.name): lambda node: node.content.name
            })
        self.model.setDataLookup.update({(QtCore.Qt.EditRole, self.model.column.name): self.renameTraceField})
        self.model.categoryDataLookup.update({
            (QtCore.Qt.DisplayRole, self.model.column.name): lambda node: node.id,
            (QtCore.Qt.EditRole, self.model.column.name): lambda node: node.id
        })
        self.model.categorySetDataLookup.update({(QtCore.Qt.EditRole, self.model.column.name): self.renameTraceField})

        self.editData = QtWidgets.QAction("Edit Data", self)
        self.editData.triggered.connect(self.onEditData)
        self.addAction(self.editData)
        self.removeData = QtWidgets.QAction("Remove Data", self)
        self.removeData.triggered.connect(self.onNamedDelete)
        self.removeButton.clicked.disconnect()
        self.removeButton.clicked.connect(self.onNamedDelete) #  (self.traceView.onDelete)
        self.addAction(self.removeData)
        self.saveTrace =  QtWidgets.QAction("Save New Copy", self)
        self.saveTrace.triggered.connect(self.forceSave)
        self.addAction(self.saveTrace)
        try:
            for filename in self.settings.filelist:
                self.openFile(filename)
            self.updateNames()
        except NameError:
            self.settings.filelist = []

    def onOpenFile(self):
        """Execute when the open button is clicked. Open an existing trace file from disk."""
        fnames, _ = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open files', self.settings.lastDir)
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            for fname in fnames:
                self.openFile(fname)
                self.settings.filelist += [fname]
                self.settings.filelist = list(set(self.settings.filelist))
        self.updateNames()

    def updateNames(self):
        for node in self.model.root.children:
            if node.parent is not None and node.nodeType == 0:
                nodename = node.children[0].content.traceCollection.description['name']
                if nodename != '':
                    node.content = nodename
                    node.id = nodename
                    for child in node.children:
                        child.content.traceCollection.description['name'] = nodename
                        child.content.traceCollection._filenamePattern = nodename
                        child.id = nodename + '_' + child.content.name
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}
        self.model.nodeDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def onEditData(self):
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        self.tableEditor = TraceTableEditor.TraceTableEditor()
        self.tableEditor.setupUi(uniqueSelectedNodes, self.model)
        self.tableEditor.finishedEditing.connect(self.saveAndUpdateFileList)
        self.tableEditor.tablemodel.dataChanged.connect(self.newData)
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}

    def renameTraceField(self, index, newname):
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        for node in uniqueSelectedNodes:
            if node.nodeType == 0:
                if newname != node.content:
                    self.newDataAvailable = True
                node.content = newname
                node.id = newname
                for child in node.children:
                    child.content.traceCollection.description['name'] = newname
                    child.content.traceCollection._filenamePattern = newname
                    child.id = newname + '_' + child.content.name
            elif node.nodeType == 1:
                if newname != node.content.name:
                    self.newDataAvailable = True
                node.content.name = newname
                node.content.tracePlotting.name = newname
                node.id = node.parent.id + '_' + newname
            break
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}
        self.model.nodeDict = {v.id: v for k,v in self.model.nodeDict.items()}
        self.saveAndUpdateFileList()
        return True

    def forceSave(self):
        self.newData()
        self.saveAndUpdateFileList()

    def saveAndUpdateFileList(self, keys=set()):
        if self.newDataAvailable:
            if keys == set():
                self.onSave(saveCopy=True)
            else:
                for k in keys:
                    tc = self.model.nodeDict[k].children[0].content.traceCollection
                    tc.save(tc._fileType, saveCopy=True)
            self.settings.filelist = []
            for k,v in self.model.nodeDict.items():
                if v.parent is not None and v.nodeType == 0:
                    self.settings.filelist.append(self.model.nodeDict[k].children[0].content.traceCollection.filename)
        self.newDataAvailable = False

    def updateExternally(self, topNode, child, row, data, col, saveEvery=False):
        self.newDataAvailable = True
        if col == 'x':
            self.model.nodeDict[topNode+'_'+child].content.trace[self.model.nodeDict[topNode+'_'+child].content._xColumn][row] = data
            self.model.nodeDict[topNode+'_'+child].content.replot()
        elif col == 'y':
            self.model.nodeDict[topNode+'_'+child].content.trace[self.model.nodeDict[topNode+'_'+child].content._yColumn][row] = data
            self.model.nodeDict[topNode+'_'+child].content.replot()
        else:
            if col in self.model.nodeDict[topNode+'_'+child].content.trace:
                self.model.nodeDict[topNode+'_'+child].content.trace[col][row] = data
        if saveEvery:
            self.saveAndUpdateFileList()

    def newData(self):
        self.newDataAvailable = True

    def onNamedDelete(self, a):
        selectedNodes = self.traceView.selectedNodes()
        uniqueSelectedNodes = [node for node in selectedNodes if node.parent not in selectedNodes]
        with BlockAutoRangeList([gv['widget'] for gv in self.graphicsViewDict.values()]):
            for node in uniqueSelectedNodes:
                if node.nodeType == 0:
                    filename = node.children[0].content.traceCollection.filename
                    if filename in self.settings.filelist:
                        self.settings.filelist.remove(filename)
                    self.onDelete(a)
        trc.NamedTraceDict = {v.id: v for k,v in self.model.nodeDict.items()}



