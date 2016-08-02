# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtGui
import copy

from scan.EvaluationBase import EvaluationAlgorithms
from scan.AbszisseType import AbszisseType
from modules.quantity import is_Q

class EvaluationTableModel( QtCore.QAbstractTableModel):
    dataChanged = QtCore.pyqtSignal( object, object )
    headerDataLookup = ['Type', 'Id', 'Channel', 'Evaluation', 'Name', 'Hist', 'Plot', 'Abszisse' ]
    def __init__(self, updateSaveStatus, plotnames=None, evalList=None, parent=None, analysisNames=None, counterNames=None, globalDict=dict()):
        super(EvaluationTableModel, self).__init__(parent)
        self.globalDict = globalDict
        if evalList:
            self.evalList = evalList
        else:
            self.evalList = list()
        self.plotnames = plotnames
        self.updateSaveStatus = updateSaveStatus
        self.evalAlgorithmList = list()
        self.analysisNames = analysisNames if analysisNames is not None else list()
        self.counterNamesList = [values for key, values in sorted(counterNames.items())] if counterNames else None
        self.counterNames = counterNames
        self.counterIndex = dict((name, index) for index, name in counterNames.items()) if counterNames else dict()
        self.setDataLookup =  {  (QtCore.Qt.EditRole, 0): self.setType,
                                 (QtCore.Qt.EditRole, 1): self.setCounterId,
                                 (QtCore.Qt.EditRole, 2): self.setCounter,
                                 (QtCore.Qt.EditRole, 3): self.setAlgorithm,
                                 (QtCore.Qt.EditRole, 4): self.setDataName,
                                 (QtCore.Qt.EditRole, 6): self.setPlotName,
                                 (QtCore.Qt.EditRole, 7): self.setAbszisse,
                                 (QtCore.Qt.CheckStateRole, 5): self.setShowHistogram,
                                }
        self.dataLookup = {  (QtCore.Qt.DisplayRole, 0): lambda e: e.type if self.hasChannel(e) else "",
                             (QtCore.Qt.DisplayRole, 1): lambda e: e.counterId if e.type=='Counter' and self.hasChannel(e) else "",
                             (QtCore.Qt.DisplayRole, 2): self.counterName,
                             (QtCore.Qt.DisplayRole, 3): lambda e: e.evaluation,
                             (QtCore.Qt.DisplayRole, 4): lambda e: e.name,
                             (QtCore.Qt.DisplayRole, 6): lambda e: e.plotname,
                             (QtCore.Qt.DisplayRole, 7): lambda e: e.abszisse.name,
                             (QtCore.Qt.EditRole, 0): lambda e: e.type,
                             (QtCore.Qt.EditRole, 1): lambda e: str(e.counterId),
                             (QtCore.Qt.EditRole, 2):    self.counterName,
                             (QtCore.Qt.EditRole, 3):    lambda e: e.evaluation,
                             (QtCore.Qt.EditRole, 4):    lambda e: e.name,
                             (QtCore.Qt.EditRole, 6):    lambda e: e.plotname,
                             (QtCore.Qt.EditRole, 7):    lambda e: e.abszisse.name,
                             (QtCore.Qt.CheckStateRole, 5): lambda e: QtCore.Qt.Checked if e.showHistogram else QtCore.Qt.Unchecked,
                             (QtCore.Qt.BackgroundColorRole, 1): lambda e: QtCore.Qt.white if e.type=='Counter' and self.hasChannel(e) else QtGui.QColor(200, 200, 200),
                             (QtCore.Qt.BackgroundColorRole, 2): lambda e: QtCore.Qt.white if self.hasChannel(e) else QtGui.QColor(200, 200, 200),
                             (QtCore.Qt.BackgroundColorRole, 0): lambda e: QtCore.Qt.white if self.hasChannel(e) else QtGui.QColor(200, 200, 200)
                             }
        self.abszisseNames = [e.name for e in AbszisseType]
        self.choiceLookup = { 0: lambda e: ['Counter', 'Result'],
                              2: lambda e: self.counterNamesList if e.type == 'Counter' else None,
                              3: lambda e: sorted(EvaluationAlgorithms.keys()),
                              6: lambda e: sorted(self.getPlotnames()),
                              7: lambda e: self.abszisseNames }

    @staticmethod
    def hasChannel(evaluation):
        algo = EvaluationAlgorithms.get(evaluation.evaluation)
        return algo and algo.hasChannel

    def counterName(self, e):
        if not self.hasChannel(e):
            return ""
        if e.type == 'Counter' and self.counterNames:
            return self.counterNames.get(e.counter, e.counter)
        return e.counter

    def setAnalysisNames(self, names):
        self.analysisNames = names
        
    def setType(self, index, t):
        self.evalList[index.row()].type = str(t)
        self.dataChanged.emit( index, self.index(index.row(), 1) )
        return True
        
    def setCounterId(self, index, value):
        self.evalList[index.row()].counterId = int(value)
        self.dataChanged.emit( index, index )
        return True      
        
    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)

    def getPlotnames(self):
        return ['None'] + self.plotnames
    
    def getAnalysisNames(self):
        return [""]+self.analysisNames
    
    def choice(self, index):
        return self.choiceLookup[index.column()](self.evalList[index.row()])
            
    def setEvalList(self, evalList, evalAlgorithmList):
        self.beginResetModel()
        self.evalList = evalList
        self.evalAlgorithmList = evalAlgorithmList
        self.endResetModel()
        
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.evalList)
    
    def columnCount(self,  parent=QtCore.QModelIndex()):
        return 8
    
    def data(self, index, role): 
        if index.isValid():
            return self.dataLookup.get((role, index.column()), lambda e: None)(self.evalList[index.row()])
        return None
        
    def flags(self, index ):
        if index.column() in [3, 4, 6, 7]:
            return  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable
        if index.column()==5:
            return  QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
        if index.column()==1 and self.evalList[index.row()].type=='Counter' and self.hasChannel(self.evalList[index.row()] ):
            return  QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
        if index.column() in [0, 2] and self.hasChannel(self.evalList[index.row()] ):
            return  QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
        return  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role ):
        if (role == QtCore.Qt.DisplayRole):
            if (orientation == QtCore.Qt.Vertical): 
                return str(section)
            elif (orientation == QtCore.Qt.Horizontal): 
                return self.headerDataLookup[section]
        return None 

    def setCounter(self, index, value):
        self.evalList[index.row()].counter = int(value) if is_Q(value) else self.counterIndex.get(str(value), 0)
        self.dataChanged.emit(index, index)
        return True      

    def setShowHistogram(self, index, value):
        self.evalList[index.row()].showHistogram = (value == QtCore.Qt.Checked )
        self.dataChanged.emit( index, index )
        return True      
                
    def setValue(self, index, value):
        self.setData( index, value, QtCore.Qt.EditRole)
                
    def setDataName(self, index, name):
        name = name.strip()
        self.evalList[index.row()].name = name
        self.evalAlgorithmList[index.row()].setSettingsName(name)
        self.dataChanged.emit( index, index )
        return True
    
    def setPlotName(self, index, plotname):
        self.evalList[index.row()].plotname = str(plotname)
        self.dataChanged.emit( index, index )
        return True
    
    def setAbszisse(self, index, abszisse):
        self.evalList[index.row()].abszisse = AbszisseType(str(abszisse))
        self.dataChanged.emit( index, index ) 
        return True        
    
    def setAlgorithm(self, index, algorithm):
        algorithm = str(algorithm)
        evaluation = self.evalList[index.row()]
        previousEvaluation = copy.deepcopy(self.evalList[index.row()])
        previousAlgorithm = previousEvaluation.evaluation
        if algorithm!=previousAlgorithm:
            evaluation.settingsCache[previousAlgorithm] = previousEvaluation.settings
            evaluation.evaluation = algorithm
            algo = EvaluationAlgorithms[evaluation.evaluation](globalDict=self.globalDict)
            algo.subscribe( self.updateSaveStatus )   # track changes of the algorithms settings so the save status is displayed correctly
            if evaluation.evaluation in evaluation.settingsCache:
                evaluation.settings = evaluation.settingsCache[evaluation.evaluation]
            else:
                evaluation.settings = dict()
            algo.setSettings( evaluation.settings, evaluation.name )
            self.evalAlgorithmList[index.row()] = algo     
            self.dataChanged.emit( self.index(index.row(), 0), index )
        return True
