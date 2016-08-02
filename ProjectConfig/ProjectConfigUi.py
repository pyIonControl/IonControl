# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os.path
import sys
import logging
from PyQt5 import QtGui, QtCore, QtWidgets
import PyQt5.uic
from datetime import datetime

uiPath = os.path.join(os.path.dirname(__file__), '..', 'ui/ProjectConfig.ui')
Form, Base = PyQt5.uic.loadUiType(uiPath)
import yaml

class ProjectConfigUi(Base, Form):
    """Class for selecting a project"""
    def __init__(self, project, scriptname):
        Base.__init__(self)
        Form.__init__(self)
        self.scriptname = scriptname
        self.project = project
        self.projectConfig = project.projectConfig
        self.setupUi(self)
        self.configurationFile = None

    def setupUi(self, parent):
        """setup the dialog box ui"""
        super(ProjectConfigUi, self).setupUi(parent)
        self.infoLabel.setText(
            "This dialog box overwrites the configuration file {0}.".format(
                self.project.projectConfigFilename))
        self.setBaseDir()
        self.defaultCheckBox.setChecked(not self.projectConfig['showGui'])
        self.populateProjectList()
        self.changeBaseDirectory.clicked.connect(self.onChangeBaseDirectory)
        self.createButton.clicked.connect(self.onCreate)
        self.findConfigurationFile.clicked.connect(self.onFindConfigurationFile)
        self.configurationFileEdit.editingFinished.connect(self.onSetConfigurationFile)
        self.loadFromDateTimeEdit.setDateTime(datetime.now())

    def setBaseDir(self):
        """Get a valid base directory"""
        logger = logging.getLogger(__name__)
        if not os.path.exists(self.projectConfig['baseDir']):
            baseDir = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                                 'Please select a base directory for projects',
                                                                 os.path.expanduser('~')
                                                                )
            if not os.path.exists(baseDir):
                message = "Valid base directory for projects must be specified for IonControl program to run"
                logger.error(message)
                sys.exit(message)
            else:
                self.projectConfig['baseDir'] = baseDir
        self.baseDirectoryEdit.setText(self.projectConfig['baseDir'])

    def onCreate(self):
        """Create a new project folder"""
        name = self.newProjectName.text()
        if name:
            projectDir = os.path.join(self.projectConfig['baseDir'], name)
            configDir = os.path.join(projectDir, 'config')
            if not os.path.exists(configDir):
                os.makedirs(configDir)
            exptConfigFilename = os.path.join(configDir, self.scriptname + '_ExptConfig.yml')
            if not os.path.exists(exptConfigFilename):
                with open(exptConfigFilename, 'w') as f:
                    yaml.dump(self.project.exptConfig, f, default_flow_style=False)
            self.populateProjectList()
            self.newProjectName.clear()

    def populateProjectList(self):
        self.projectList.clear()
        projects = [name for name in os.listdir(self.projectConfig['baseDir'])
                    if os.path.exists(os.path.join(self.projectConfig['baseDir'], name, 'config', self.scriptname + '_ExptConfig.yml'))]
        self.projectList.addItems(projects)
        matches = self.projectList.findItems(self.projectConfig['name'], QtCore.Qt.MatchExactly)
        if matches:
            self.projectList.setCurrentItem(matches[0])
        elif projects:
            self.projectList.setCurrentRow(0)

    def onChangeBaseDirectory(self):
        baseDir = QtWidgets.QFileDialog.getExistingDirectory(self)
        if baseDir:
            self.projectConfig['baseDir'] = str(baseDir)
            self.baseDirectoryEdit.setText(baseDir)
            self.populateProjectList()

    def onFindConfigurationFile(self):
        self.configurationFile, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Configuration File", directory=self.projectConfig['baseDir'])
        self.configurationFileEdit.setText(self.configurationFile)

    def onSetConfigurationFile(self):
        self.configurationFile = self.configurationFileEdit.text()

    def accept(self):
        selectedProject = self.projectList.currentItem()
        if selectedProject: #something is selected
            self.projectConfig['showGui'] = not self.defaultCheckBox.isChecked()
            self.projectConfig['name'] = str(selectedProject.text())
            self.projectConfig['configurationFile'] = self.configurationFile
            self.projectConfig['loadFromDateTime'] = self.loadFromDateTimeEdit.dateTime().toPyDateTime() if self.loadHistoricSettingCheck.isChecked() else None
            Base.accept(self)
        else: #if nothing is selected, equivalent to clicking cancel
            Base.reject(self)

    def reject(self):
        message = "Project must be selected for IonControl program to run"
        logging.getLogger(__name__).exception(message)
        sys.exit(message)
