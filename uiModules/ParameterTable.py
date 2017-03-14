# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from PyQt5 import QtCore, QtGui, QtWidgets
from modules.SequenceDict import SequenceDict
from modules.enum import enum
from modules.Expression import Expression
from uiModules.ParameterTableDelegate import ParameterTableDelegate
from modules.quantity import Q
from modules.firstNotNone import firstNotNone
from functools import partial

class ParameterException(Exception):
    pass


class Parameter(object):
    """Class for parameters used in the parameter table.
    Args:
        name (str): The name displayed in the table
        dataType (str): the type of parameter
        value: The value of the parameter (type depends on dataType)
        tooltip (str): The tooltip to show in the table
        choices (list of str): The choices in a combo box (only used for dataType 'list')
        key: an alternative reference to the parameter
        text (str): An expression for the parameter (e.g. a global)
        """
    dataTypes = ['magnitude', 'str', 'select', 'multiselect', 'bool', 'action']
    def __init__(self, name, dataType, value, key=None, choices=None, text=None, tooltip=''):
        if dataType in self.dataTypes:
            self.name = name
            self.dataType = dataType
            self.value = value
            self.tooltip = tooltip
            self.choices = choices
            self.key = key
            self.text = text
        else:
            raise ParameterException("Unknown dataType: {0}".format(dataType))


class ParameterTableModel(QtCore.QAbstractTableModel):
    """Table for generic parameters"""
    headerDataLookup = ['Name', 'Value']
    valueChanged = QtCore.pyqtSignal(object)
    def __init__(self, parent=None, parameterDict=None):
        super(ParameterTableModel, self).__init__(parent)
        self.parameterDict = parameterDict if parameterDict else SequenceDict()
        self.column = enum('name', 'value')
        self.textBG = QtGui.QColor(QtCore.Qt.green).lighter(175)
        self.dataLookup = {
            (QtCore.Qt.DisplayRole, self.column.name): lambda param: param.name if param.dataType!='action' else None,
            (QtCore.Qt.DisplayRole, self.column.value): lambda param: (str(param.value) if param.dataType!='multiselect' else ' | '.join(param.value)) if param.dataType!='bool' else None,
            (QtCore.Qt.EditRole, self.column.value): lambda param: firstNotNone(param.text, param.value),
            (QtCore.Qt.ToolTipRole, self.column.name): lambda param: param.tooltip,
            (QtCore.Qt.ToolTipRole, self.column.value): lambda param: firstNotNone(param.text, param.tooltip),
            (QtCore.Qt.CheckStateRole, self.column.value): lambda param: (QtCore.Qt.Checked if param.value else QtCore.Qt.Unchecked) if param.dataType=='bool' else None,
            (QtCore.Qt.BackgroundColorRole, self.column.value): lambda param: self.textBG if param.text else None
        }
        self.setDataLookup =  {
            (QtCore.Qt.EditRole, self.column.value): self.setValue,
            (QtCore.Qt.UserRole, self.column.value): self.setText,
            (QtCore.Qt.CheckStateRole, self.column.value): self.setValue
        }

    def choice(self, index):
        row = index.row()
        parameter = self.parameterDict.at(row)
        return parameter.choices

    def setText(self, index, value):
        row = index.row()
        self.parameterDict.at(row).text = value
        return True

    def setValue(self, index, value):
        row = index.row()
        parameter = self.parameterDict.at(row)
        dataType = parameter.dataType
        parameter.value = value if dataType is not 'bool' else value==QtCore.Qt.Checked
        self.valueChanged.emit(parameter)
        return True

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.parameterDict)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def data(self, index, role):
        if index.isValid():
            param = self.parameterDict.at(index.row())
            return self.dataLookup.get((role, index.column()), lambda param: None)(param)

    def setData(self, index, value, role):
        return self.setDataLookup.get((role, index.column()), lambda index, value: False )(index, value)

    def flags(self, index):
        row = index.row()
        column = index.column()
        dataType = self.parameterDict.at(row).dataType
        if column == self.column.name:
            return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled
        elif column == self.column.value:
            if dataType is 'bool':
                return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
            else:
                return QtCore.Qt.ItemIsSelectable |  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self.headerDataLookup[section]

    def setParameters(self, newParameterDict):
        self.beginResetModel()
        self.parameterDict = newParameterDict
        self.endResetModel()

    def evaluate(self, globalDict):
        for parameter in list(self.parameterDict.values()):
            if parameter.text is not None:
                value = Expression().evaluateAsMagnitude(parameter.text, globalDict)
                parameter.value = value  # set saved value to match new parameter text
                modelIndex = self.createIndex(self.parameterDict.index(parameter.name), self.column.value)
                self.dataChanged.emit(modelIndex, modelIndex)
                self.valueChanged.emit(parameter)


class ParameterTable(QtWidgets.QTableView):
    valueChanged = QtCore.pyqtSignal(object)
    def setupUi(self, parameterDict=None, globalDict=None):
        model = ParameterTableModel(parameterDict=parameterDict)
        self.globalDict = globalDict
        delegate = ParameterTableDelegate(self.globalDict)
        self.setModel(model)
        self.setItemDelegate(delegate)
        header = self.verticalHeader()
        header.setDefaultSectionSize(18)
        self.model().valueChanged.connect(self.valueChanged.emit)
        self.itemDelegate().buttonClicked.connect(self.valueChanged.emit)
        self.setSpans()
        self.resizeColumnsToContents()

    def setSpans(self):
        for row in range(len(self.model().parameterDict)):
            parameter = self.model().parameterDict.at(row)
            if parameter.dataType == 'action':
                self.setSpan(row,0,1,2)
                self.resizeRowToContents(row)

    def setParameters(self, newParameterDict):
        self.clearSpans()
        self.model().setParameters(newParameterDict)
        self.setSpans()
        self.resizeColumnsToContents()

    def evaluate(self, globalName=''):
        self.model().evaluate(self.globalDict)


if __name__=='__main__':
    import sys
    from functools import partial

    globalDict = {'aa': Q(5, 'ms'), 'bb': Q(125,'us')}

    def onDataChanged(parameterDict):
        for key, param in parameterDict.items():
            print('{0}: {1}'.format(key, param.value))
        for key, param in globalDict.items():
            print('{0}: {1}'.format(key, param))


    def onButtonClicked(model, parameter):
        print("{0} was clicked".format(parameter.value))
        globalDict['aa'] += Q(1, 'us')
        model.evaluate(globalDict)
        print(globalDict['aa'])

    app = QtWidgets.QApplication(sys.argv)

    a = Parameter(name='a', dataType='magnitude', value=5, tooltip="I'm an int")
    b = Parameter(name='b', dataType='magnitude', value=15.125, tooltip="I'm a float")
    c = Parameter(name='c', dataType='magnitude', value=Q(12, 'us'), tooltip="I'm a magnitude")
    d = Parameter(name='d', dataType='str', value='qqq', tooltip="I'm a str")
    e = Parameter(name='e', dataType='select', value='Option 1', choices=['Option 1', 'Option 2', 'Option 3'], tooltip="I'm qqq")
    f = Parameter(name='f', dataType='bool', value=True, tooltip="I'm a bool")
    g = Parameter(name='g', dataType='action', value='bbb', tooltip="I'm a button")
    h = Parameter(name='h', dataType='action', value='click me!', tooltip="I'm another button")
    i = Parameter(name='i', dataType='multiselect', value=['A'], choices=['A', 'B', 'C'], tooltip="I'm a multiselect combo box")
    parameterDict = SequenceDict(
        [(a.name, a),
         (b.name, b),
         (c.name, c),
         (d.name, d),
         (e.name, e),
         (f.name, f),
         (g.name, g),
         (h.name, h),
         (i.name, i)]
    )
    table = ParameterTable()
    table.setupUi(parameterDict=parameterDict, globalDict=globalDict)
    model = table.model()
    model.valueChanged.connect(partial(onDataChanged, model.parameterDict))
    table.itemDelegate().buttonClicked.connect(partial(onButtonClicked, model))
    table.show()
    sys.exit(app.exec_())