# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os.path
import sys
import logging
from collections import OrderedDict

from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic
import yaml
from persist.DatabaseConnectionSettings import DatabaseConnectionSettings
from modules.PyqtUtility import BlockSignals, textSize
from uiModules.MagnitudeSpinBox import MagnitudeSpinBox
from functools import partial

uiPath = os.path.join(os.path.dirname(__file__), '..', 'ui/ExptConfig.ui')
Form, Base = PyQt5.uic.loadUiType(uiPath)

class ExptConfigUi(Base, Form):
    """Class for configuring an experiment"""
    updateRoles = QtCore.pyqtSignal()
    def __init__(self, project, scriptname):
        Base.__init__(self)
        Form.__init__(self)
        self.project = project
        self.exptConfig = project.exptConfig
        filename = scriptname + '_ExptConfigGuiTemplate.yml'  # template for creating GUI
        self.widgetDict = dict() #key: tuple (guiName, objName, name). val: dict, 'widget': config widget, 'subwidgetList':list of config subwidgets
        self.roleDict = dict() #key: a role (i.e. voltages, pulser, etc.). val: a list of hardware that can fulfill that role
        self.guiTemplateFilename = os.path.join(self.project.mainConfigDir, filename)
        with open(self.guiTemplateFilename, 'r') as f:
            self.guiTemplate = yaml.load(f)
        self.setupUi(self)

    def setupUi(self, parent):
        """setup the dialog box ui"""
        super(ExptConfigUi, self).setupUi(parent)
        self.infoLabel.setText(
            'Experiment configuration for project: <b>{0}</b><br><br>This dialog box overwrites the experiment configuration file:<br>{1}.'.format(
                self.project.name, self.project.exptConfigFilename))
        self.defaultCheckBox.setChecked(not self.exptConfig['showGui'])
        self.hardwareComboBox.addItems(list(self.guiTemplate['hardware'].keys()))
        self.softwareComboBox.addItems(list(self.guiTemplate['software'].keys()))
        databaseConnection = self.exptConfig['databaseConnection']
        self.userEdit.setText(databaseConnection.get('user', 'python'))
        self.passwordEdit.setText(databaseConnection.get('password', ''))
        self.hostEdit.setText(databaseConnection.get('host', 'localhost'))
        self.portEdit.setValue(databaseConnection.get('port', 5432))
        self.echoCheck.setChecked(databaseConnection.get('echo', False))
        customDatabaseName = self.exptConfig.get('useCustomDatabaseName', False)
        self.checkBoxCustomDatabase.setChecked(customDatabaseName)
        self.checkBoxCustomDatabase.stateChanged.connect(self.onCustomDatabaseNameChanged)
        self.onCustomDatabaseNameChanged(QtCore.Qt.Checked if self.exptConfig.get('useCustomDatabaseName', False) else QtCore.Qt.Unchecked)

        self.guiDict = OrderedDict((('hardware', (self.hardwareTabWidget, self.hardwareComboBox, self.hardwareTableWidget, self.hardwareNameEdit)),
                                    ('software', (self.softwareTabWidget, self.softwareComboBox, self.softwareTableWidget, self.softwareNameEdit))))
        for guiName in self.guiDict:
            for objName in self.exptConfig[guiName]:
                for name in self.exptConfig[guiName][objName]:
                    self.addObj(guiName, objName, name)

        self.addHardwareButton.clicked.connect( partial(self.onAdd, 'hardware') )
        self.removeHardwareButton.clicked.connect( partial(self.onRemove, 'hardware') )
        self.hardwareTableWidget.currentCellChanged.connect( partial(self.onSelect, 'hardware') )
        self.hardwareTableWidget.itemChanged.connect( partial(self.onItemChanged, 'hardware') )
        self.hardwareTabWidget.currentChanged.connect( partial(self.onTabWidgetChanged, 'hardware') )

        self.addSoftwareButton.clicked.connect( partial(self.onAdd, 'software') )
        self.removeSoftwareButton.clicked.connect( partial(self.onRemove, 'software') )
        self.softwareTableWidget.currentCellChanged.connect( partial(self.onSelect, 'software') )
        self.softwareTableWidget.itemChanged.connect( partial(self.onItemChanged, 'software') )
        self.softwareTabWidget.currentChanged.connect( partial(self.onTabWidgetChanged, 'software') )

        self.currentObj = {'hardware':None,'software':None}

    def onCustomDatabaseNameChanged(self, state):
        checked = state == QtCore.Qt.Checked
        self.exptConfig['useCustomDatabaseName'] = checked
        self.databaseEdit.setEnabled(checked)
        databaseConnection = self.exptConfig['databaseConnection']
        if not checked:
            databaseConnection['database'] = self.project.name.lower()
        self.databaseEdit.setText(databaseConnection.get('database', self.project.name.lower()))

    def keyPressEvent(self, ev):
        if ev.key()==QtCore.Qt.Key_Enter or ev.key()==QtCore.Qt.Key_Return:
            if str(self.hardwareNameEdit.text()):
                self.onAdd('hardware')
                return
            elif str(self.softwareNameEdit.text()):
                self.onAdd('software')
                return
        super(ExptConfigUi, self).keyPressEvent(ev)

    @property
    def hardware(self):
        """A list of hardware tuples of the form (objName, name)"""
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict['hardware']
        return [( str(tableWidget.item(row, 0).text()), str(tableWidget.item(row, 1).text()) ) for row in range(tableWidget.rowCount())]

    @property
    def software(self):
        """A list of software tuples of the form (objName, name)"""
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict['software']
        return [( str(tableWidget.item(row, 0).text()), str(tableWidget.item(row, 1).text()) ) for row in range(tableWidget.rowCount())]

    def addObj(self, guiName, objName, name):
        """Add (objName, name) to the table widget, and add the appropriate tab to the tab widget.
        Args:
            guiName (str): 'hardware' or 'software'
            objName (str): The type of hardware or software
            name (str): The name of the specific piece of hardware or software
        """
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
        logger=logging.getLogger(__name__)
        if objName not in self.guiTemplate[guiName]:
            logger.error("No GUI template entry for {0}".format(objName))
        elif (objName, name) in getattr(self, guiName):
            logger.warning( "{0} {1} already exists".format(guiName, self.project.fullName(objName, name)) )
        elif ':' in name:
            logger.error("character ':' cannot be used in a name")
        else:
            templateDict = self.guiTemplate[guiName][objName]
            description = templateDict.get('description') if templateDict else None
            with BlockSignals(tableWidget) as w:
                objItem=QtWidgets.QTableWidgetItem(objName)
                objItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable)
                nameItem=QtWidgets.QTableWidgetItem(name)
                nameItem.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable)
                newrow=w.rowCount()
                w.insertRow(newrow)
                w.setItem(newrow, 0, objItem)
                w.setItem(newrow, 1, nameItem)
                if description:
                    objItem.setToolTip(description)
                    nameItem.setToolTip(description)
                    enabled=self.exptConfig[guiName].get(objName, dict()).get(name, dict()).get('enabled', True)
                    checkState = QtCore.Qt.Checked if enabled else QtCore.Qt.Unchecked
                    objItem.setCheckState(checkState)
                w.setCurrentItem(objItem)
                w.resizeColumnsToContents()
            with BlockSignals(tabWidget) as w:
                widget=self.getWidget(guiName, objName, name)
                w.addTab(widget, self.project.fullName(objName, name))
                index=w.indexOf(widget)
                if description:
                    w.setTabToolTip(index, description)
                w.setCurrentIndex(index)

    def getWidget(self, guiName, objName, name):
        """Get the config widget associated with the given objName.
        Args:
            guiName (str): 'hardware' or 'software'
            objName (str): The type of hardware or software
            name (str): The name of the specific piece of hardware or software
        """
        templateDict = self.guiTemplate[guiName][objName]
        fields = templateDict.get('fields') if templateDict else None
        roles = templateDict.get('roles') if templateDict else None

        if (guiName, objName, name) not in self.widgetDict:
            self.widgetDict[(guiName, objName, name)]=dict()
            self.widgetDict[(guiName, objName, name)]['subwidgetList'] = []
            mainwidget = QtWidgets.QWidget()
            layout = QtWidgets.QFormLayout(mainwidget)
            if templateDict and fields:
                for fieldname, fieldtype in fields.items():
                    try:
                        oldvalue = self.exptConfig[guiName][objName][name][fieldname]
                    except KeyError:
                        oldvalue = None
                    subwidget=ConfigWidget(self, fieldtype, objName, name, oldvalue, self.widgetDict, parent=mainwidget)
                    self.widgetDict[(guiName, objName, name)]['subwidgetList'].append((fieldname, subwidget))
                    layout.addRow(fieldname, subwidget.widget)
            else:
                layout.addRow('No configuration data for this selection', None)
            self.widgetDict[(guiName, objName, name)]['widget'] = mainwidget
        if roles:
            for role in roles:
                self.roleDict.setdefault(role, []).append(self.project.fullName(objName, name)) #append fullName to list of roles, or create list with just fullName if it doesn't exist yet
            self.updateRoles.emit()
        return self.widgetDict[(guiName, objName, name)]['widget']

    def onItemChanged(self, guiName, item):
        """A new name is typed in for a table entry"""
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
        row=tableWidget.row(item)
        column=tableWidget.column(item)
        if self.currentObj[guiName]:
            _, oldName=self.currentObj[guiName]
        if column==1: #This should always be true, since column 0 is not editable
            newName=str(item.text())
            objName=str(tableWidget.item(row, 0).text())
            if newName==oldName:
                return
            elif getattr(self, guiName).count((objName, newName)) > 1:
                logging.getLogger(__name__).warning( "{0} already exists".format(self.project.fullName(objName, newName)) )
                item.setText(oldName)
                return
            elif ':' in newName:
                logging.getLogger(__name__).warning("character ':' cannot be used in a name")
                return
            subDict=self.widgetDict.pop((guiName, objName, oldName))
            self.widgetDict[(guiName, objName, newName)]=subDict
            if objName=='Opal Kelly FPGA':
                for fieldname, subwidget in subDict['subwidgetList']:
                    if fieldname=='device':
                        subwidget.widget.name=newName
                        break
            oldFullName = self.project.fullName(objName, oldName)
            newFullName = self.project.fullName(objName, newName)
            self.currentObj[guiName]=(objName, newName)
            with BlockSignals(tabWidget) as w:
                widget=subDict['widget']
                index = w.indexOf(widget)
                w.setTabText(index, newFullName)
            templateDict = self.guiTemplate[guiName][objName]
            roles = templateDict.get('roles') if templateDict else None
            if roles:
                for role in roles:
                    self.roleDict[role].remove(oldFullName)
                    self.roleDict[role].append(newFullName)
                self.updateRoles.emit()

    def onTabWidgetChanged(self, guiName, index):
        """Tab widget is clicked. Change the selection in the table widget.
        Args:
            guiName (str): 'hardware' or 'software'
            index (int): new selected index in tab widget
        """
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
        fullName = str(tabWidget.tabText(index))
        objName, name = self.project.fromFullName(fullName)
        with BlockSignals(tableWidget) as w:
            numRows = w.rowCount()
            for row in range(numRows):
                objNameItem = tableWidget.item(row, 0)
                nameItem = tableWidget.item(row, 1)
                if str(objNameItem.text())==objName and str(nameItem.text())==name:
                    w.setCurrentItem(objNameItem)
                    self.currentObj[guiName]=(objName, name)
                    break

    def onSelect(self, guiName, currentRow, currentColumn, previousRow, previousColumn):
        """Table widget is clicked. Change the current tab on the tab widget."""
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
        objName=str(tableWidget.item(currentRow, 0).text())
        name=str(tableWidget.item(currentRow, 1).text())
        widget = self.widgetDict[(guiName, objName, name)]['widget']
        index = tabWidget.indexOf(widget)
        with BlockSignals(tabWidget) as w:
            w.setCurrentIndex(index)
        self.currentObj[guiName]=(objName, name)

    def onAdd(self, guiName):
        """Add is clicked."""
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
        objName = str(comboBox.currentText())
        name = str(nameEdit.text())
        nameEdit.clear()
        self.addObj(guiName, objName, name)

    def onRemove(self, guiName):
        """Remove is clicked. Remove selection from the table widget and remove from the tab widget.
        Args:
            guiName: 'hardware' or 'software'
        """
        tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
        selectedItems = tableWidget.selectedItems()
        selectedRows = {tableWidget.row(item) for item in selectedItems}
        uniqueSelectedItems = [tableWidget.item(row, 0) for row in selectedRows]
        with BlockSignals(tableWidget):
            with BlockSignals(tabWidget):
                for item in uniqueSelectedItems:
                    row = tableWidget.row(item)
                    objName = str(tableWidget.item(row, 0).text())
                    name = str(tableWidget.item(row, 1).text())
                    tableWidget.removeRow(row)
                    widget = self.widgetDict[(guiName, objName, name)]['widget']
                    index = tabWidget.indexOf(widget)
                    tabWidget.removeTab(index)
                    templateDict = self.guiTemplate[guiName][objName]
                    roles = templateDict.get('roles') if templateDict else None
                    if roles:
                        fullName = self.project.fullName(objName, name)
                        for role in roles:
                            self.roleDict[role].remove(fullName)
                        self.updateRoles.emit()

    def accept(self):
        """Ok button is clicked. Checks database settings before proceeding."""
        dbSettings = {'user':str(self.userEdit.text()),
                      'password':str(self.passwordEdit.text()),
                      'database':str(self.databaseEdit.text()),
                      'host':str(self.hostEdit.text()),
                      'port':self.portEdit.value(),
                      'echo':self.echoCheck.isChecked()
                      }
        dbConn = DatabaseConnectionSettings(**dbSettings)
        success = self.project.attemptDatabaseConnection(dbConn)
        if not success:
            QtWidgets.QMessageBox.information(self, 'Database error', 'Invalid database settings')
        else:
            self.exptConfig.clear()
            for guiName in ['hardware', 'software']:
                self.exptConfig[guiName] = dict()
                tabWidget, comboBox, tableWidget, nameEdit = self.guiDict[guiName]
                numRows = tableWidget.rowCount()
                for row in range(numRows):
                    objNameItem = tableWidget.item(row, 0)
                    objName = str(objNameItem.text())
                    nameItem = tableWidget.item(row, 1)
                    name = str(nameItem.text())
                    enabled = objNameItem.checkState()==QtCore.Qt.Checked
                    subwidgetList=self.widgetDict[(guiName, objName, name)]['subwidgetList']
                    self.exptConfig[guiName].setdefault(objName, dict()) #'objName' is a type of hardware or software
                    self.exptConfig[guiName][objName][name] = dict() #'name' is a specific piece of hardware or software
                    for field, subwidget in subwidgetList: #'field' is the specific config field for 'name'
                        self.exptConfig[guiName][objName][name][field] = subwidget.content
                    self.exptConfig[guiName][objName][name]['enabled'] = enabled
            self.exptConfig['databaseConnection'] = dbSettings
            self.exptConfig['showGui']=not self.defaultCheckBox.isChecked()
            self.exptConfig['version']=2.0
            self.exptConfig['useCustomDatabaseName'] = self.checkBoxCustomDatabase.isChecked()
            Base.accept(self)

    def reject(self):
        """Cancel or close is clicked. Shut down the program."""
        message = "Experiment must be configured for IonControl program to run"
        logging.getLogger(__name__).error(message)
        sys.exit(message)

class ConfigWidget(object):
    """Class for arbitrary config widget"""
    def __init__(self, exptConfigUi, fieldtype, objName, name, oldvalue, widgetDict, parent=None):
        """Creates a widget of the specified fieldtype"""
        self.fieldtype = fieldtype
        self.oldvalue = oldvalue

        self.widgetCallLookup = {'bool'      : QtGui.QCheckBox,
                                 'float'     : QtGui.QDoubleSpinBox,
                                 'magnitude' : MagnitudeSpinBox,
                                 'int'       : QtGui.QSpinBox,
                                 'role'      : partial(RoleWidget, objName, exptConfigUi),
                                 'path'      : partial(PathWidget,exptConfigUi.project.baseDir),
                                 'str'       : QtGui.QLineEdit,
                                 'ok_fpga'   : partial(OK_FPGA_Widget, widgetDict, objName, name)}

        widgetCall = self.widgetCallLookup.get(self.fieldtype)
        if not widgetCall:
            self.widget = QtWidgets.QLabel('error: unknown type', parent=parent)
            self.widget.setStyleSheet("QLabel {color: red;}")
        else:
            self.widget = widgetCall(parent=parent)
            if self.fieldtype=='int' or self.fieldtype=='float':
                self.widget.setRange(-999999999, 999999999)
                if self.fieldtype=='float':
                    self.widget.setDecimals(10)

        self.widgetSetLookup = {'bool'      : getattr(self.widget, 'setChecked', None),
                                'float'     : getattr(self.widget, 'setValue', None),
                                'magnitude' : getattr(self.widget, 'setValue', None),
                                'int'       : getattr(self.widget, 'setValue', None),
                                'role'      : getattr(self.widget, 'setToText', None),
                                'path'      : getattr(self.widget, 'setText', None),
                                'str'       : getattr(self.widget, 'setText', None),
                                'ok_fpga'   : getattr(self.widget, 'setToText', None)}

        if oldvalue:
            try:
                self.widgetSetLookup.get(self.fieldtype)(oldvalue)
            except Exception:
                pass

    @property
    def content(self):
        if   self.fieldtype=='bool':      return self.widget.isChecked()
        elif self.fieldtype=='float':     return self.widget.value()
        elif self.fieldtype=='magnitude': return str(self.widget.value())
        elif self.fieldtype=='int':       return self.widget.value()
        elif self.fieldtype=='role':      return str(self.widget.currentText())
        elif self.fieldtype=='path':      return str(self.widget.lineEdit.text())
        elif self.fieldtype=='str':       return str(self.widget.text())
        elif self.fieldtype == 'ok_fpga':
            newvalue = self.widget.identifierComboBox.currentText()
            return newvalue or self.oldvalue  # we don't want to forget the last valid device name


class PathWidget(QtWidgets.QHBoxLayout):
    """Config widget for selecting files"""
    def __init__(self,baseDir,parent=None):
        super(PathWidget, self).__init__()
        self.lineEdit=QtWidgets.QLineEdit(parent)
        self.lineEdit.setReadOnly(True)
        self.openButton=QtWidgets.QPushButton(parent)
        icon = QtGui.QIcon()
        pixmap = QtGui.QPixmap(":/openicon/icons/document-open-5.png")
        icon.addPixmap(pixmap)
        self.openButton.setIcon(icon)
        self.addWidget(self.lineEdit)
        self.addWidget(self.openButton)
        self.openButton.clicked.connect(self.onOpen)
        self.baseDir=baseDir
        self.parent=parent

    @QtCore.pyqtSlot()
    def onOpen(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self.parent, 'Select File', self.baseDir, 'All files (*.*)')
        if filename:
            self.lineEdit.setText(filename)

    def setText(self, text):
        self.lineEdit.setText(text)


class RoleWidget(QtWidgets.QComboBox):
    """Combo box for selecting what hardware to use for a specific software role"""
    def __init__(self,name,exptConfigUi,parent=None):
        super(RoleWidget, self).__init__()
        self.name = name
        self.exptConfigUi = exptConfigUi
        self.onUpdate()
        self.exptConfigUi.updateRoles.connect(self.onUpdate)

    @QtCore.pyqtSlot()
    def onUpdate(self):
        """Update the list of possible hardware to use for this role"""
        currentText=self.currentText()
        self.clear()
        self.addItem('')
        hardwareList = self.exptConfigUi.roleDict.get(self.name)
        if hardwareList:
            self.addItems(hardwareList)
        self.setCurrentIndex( self.findText(currentText, QtCore.Qt.MatchExactly) )

    def setToText(self, text):
        """Set widget to particular text"""
        index=self.findText(text, QtCore.Qt.MatchExactly)
        self.setCurrentIndex(index)


class OK_FPGA_Widget(QtWidgets.QHBoxLayout):
    """Config widget for selecting an Opal Kelly FPGA"""
    def __init__(self, widgetDict, objName, name, parent=None):
        super(OK_FPGA_Widget, self).__init__()
        from pulser.OKBase import OKBase
        self.pulser = OKBase()
        self.widgetDict = widgetDict
        self.objName = objName
        self.name = name
        self.identifierComboBox = QtWidgets.QComboBox(parent)
        self.modelLineEdit = QtWidgets.QLineEdit(parent)
        self.modelLineEdit.setReadOnly(True)
        self.modelLineEdit.setFixedWidth(120)
        self.uploadButton = QtWidgets.QPushButton('Upload', parent)
        self.uploadButton.setFixedWidth(60)
        self.uploadButton.setToolTip("Upload bitfile to FPGA")
        self.uploadButton.clicked.connect(self.onUpload)
        self.scanButton = QtWidgets.QPushButton('Scan', parent)
        self.scanButton.setFixedWidth(60)
        self.scanButton.setToolTip("Scan for FPGAs")
        self.scanButton.clicked.connect(self.onScan)
        self.addWidget(self.identifierComboBox)
        self.addWidget(self.modelLineEdit)
        self.addWidget(self.uploadButton)
        self.addWidget(self.scanButton)
        self.OK_FPGA_Dict=dict()
        self.FPGAlistModel = QtCore.QStringListModel()
        self.identifierComboBox.setModel(self.FPGAlistModel)
        self.identifierComboBox.currentIndexChanged[str].connect(self.onChanged)
        self.onScan()

    @QtCore.pyqtSlot()
    def onScan(self):
        """Get list of FPGAs"""
        logger = logging.getLogger(__name__)
        currentText = self.identifierComboBox.currentText()
        self.OK_FPGA_Dict = self.pulser.listBoards()
        logger.info( "Opal Kelly Devices found: {0}".format({k:v.modelName for k, v in self.OK_FPGA_Dict.items()}) )
        self.OK_FPGA_Dict.update({'':'dummy'})
        self.FPGAlistModel.setStringList(list(self.OK_FPGA_Dict.keys()))
        self.setToText(currentText)

    @QtCore.pyqtSlot()
    def onUpload(self):
        """upload bitFile to FPGA"""
        logger = logging.getLogger(__name__)
        subwidgets = self.widgetDict[('hardware', self.objName, self.name)]['subwidgetList']
        FPGA_name = str(self.identifierComboBox.currentText())
        FPGA = self.OK_FPGA_Dict[FPGA_name]
        bitFileFound=False
        for fieldName, widget in subwidgets:
            if fieldName=='bitFile':
                bitFileFound=True
                bitFile=widget.content
                break
        if not bitFileFound:
            logger.error("No bitfile field found; unable to upload bitfile")
        elif not os.path.exists(bitFile):
            logger.error("Invalid bitfile path")
        elif not FPGA_name:
            logger.error("No FPGA selected")
        else:
            self.pulser.openBySerial(FPGA.serial)
            self.pulser.uploadBitfile(bitFile)
            self.pulser.close()
            logger.info("Uploaded file {0} to {1} (model {2})".format(bitFile, FPGA_name, FPGA.modelName))

    @QtCore.pyqtSlot(str)
    def onChanged(self, name):
        """set modelLineEdit to display FPGA model name"""
        name = str(name)
        modelName=self.OK_FPGA_Dict.get(name).modelName if name else ''
        self.modelLineEdit.setText(modelName)

    def setToText(self, text):
        """Set widget to particular device id text"""
        index=self.identifierComboBox.findText(text, QtCore.Qt.MatchExactly)
        self.currentText=text if index >=0 else ''
        self.identifierComboBox.setCurrentIndex(index)