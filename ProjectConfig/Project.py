# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import __main__
import sqlalchemy_utils
import os.path
import sys
import yaml
import logging
from PyQt5 import QtGui, QtCore
import PyQt5.uic
from datetime import datetime

from modules.iteratortools import path_iter_right
from persist.DatabaseConnectionSettings import DatabaseConnectionSettings
from .ProjectConfigUi import ProjectConfigUi
from .ExptConfigUi import ExptConfigUi
from sqlalchemy import create_engine
from copy import deepcopy

uiPath = os.path.join(os.path.dirname(__file__), '..', 'ui/ProjectInfo.ui')
Form, Base = PyQt5.uic.loadUiType(uiPath)

currentProject=None


class Project(object):
    def __init__(self):
        """initialize a project by loading in the project config information"""
        scriptname, _ = os.path.splitext( os.path.basename(__main__.__file__) )
        logger = logging.getLogger(__name__)
        self.mainConfigDir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'config')) #IonControl/config directory
        filename = 'ProjectConfig.yml'
        self.projectConfigFilename = os.path.realpath(os.path.join(self.mainConfigDir, filename)) #absolute path to config file
        self.projectConfig = {'baseDir':'', 'name':'', 'showGui':True}  # default values
        self.exptConfig = {'hardware': dict(), 'software': dict(), 'databaseConnection': dict(), 'showGui': True,
                           'useCustomDatabaseName': False}  # default values

        #Load in the project config information
        if os.path.exists(self.projectConfigFilename):
            with open(self.projectConfigFilename, 'r') as f:
                try:
                    yamldata = yaml.load(f)
                    self.projectConfig = yamldata
                    logger.info('Project config file {0} loaded'.format(self.projectConfigFilename))
                except yaml.scanner.ScannerError: #leave defaults if the file is improperly formatted
                    logger.warning('YAML formatting error: unable to read in project config file {0}'.format(self.projectConfigFilename))

        #If the baseDir doesn't exist or no project is specified, we have to use the GUI
        if not os.path.exists(self.projectConfig['baseDir']) or not self.projectConfig['name']:
            self.projectConfig['showGui'] = True

        if self.projectConfig['showGui']:
            ui = ProjectConfigUi(self, scriptname)
            ui.show()
            ui.exec_()
            with open(self.projectConfigFilename, 'w') as f: #save information from GUI to file
                yaml.dump(self.projectConfig, f, default_flow_style=False)
                logger.info('GUI data saved to {0}'.format(self.projectConfigFilename))

        #make project directories if they don't exist
        self.projectDir = os.path.join(self.projectConfig['baseDir'], self.projectConfig['name'])
        self.configDir = os.path.join(self.projectDir, 'config')
        self.guiConfigDir = os.path.join(self.projectDir, '.gui-config')
        self.guiConfigFile = os.path.join( self.guiConfigDir, scriptname+".config.db" )
        self.exptConfigFilename = os.path.realpath(os.path.join(self.configDir, scriptname + '_ExptConfig.yml'))

        if not os.path.exists(self.projectDir):
            os.makedirs(self.projectDir)
            logger.debug('Directory {0} created'.format(self.projectDir))

        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)
            logger.debug('Directory {0} created'.format(self.configDir))
            with open(self.exptConfigFilename, 'w') as f:
                yaml.dump(self.exptConfig, f, default_flow_style=False)
                logger.debug('File {0} created'.format(self.exptConfigFilename))

        if not os.path.exists(self.guiConfigDir):
            os.makedirs(self.guiConfigDir)

        #Load in the experiment config information
        if os.path.exists(self.exptConfigFilename):
            with open(self.exptConfigFilename, 'r') as f:
                try:
                    yamldata = yaml.load(f)
                    #check that it has the necessary keys
                    yamldata['databaseConnection']
                    yamldata['showGui']
                    yamldata['hardware']
                    yamldata['software']
                    self.exptConfig = deepcopy(yamldata)
                    for guiName in ['hardware', 'software']:
                        for objName in yamldata[guiName]:
                            for name in yamldata[guiName][objName]:
                                if name is None: #Switch 'None' names to empty string
                                    self.exptConfig[guiName][objName]['']=self.exptConfig[guiName][objName].pop(name)
                    logger.info('Experiment config file {0} loaded'.format(self.exptConfigFilename))
                except yaml.scanner.ScannerError: #leave defaults if the file is improperly formatted
                    logger.warning('YAML formatting error: unable to read in experiment config file {0}'.format(self.exptConfigFilename))
                except AttributeError:
                    logger.warning('YAML data is not a dictionary in experiment config file {0}'.format(self.exptConfigFilename))
                except KeyError as e:
                    logger.warning('YAML data is missing required element {0} in experiment config file {1}'.format(e, self.exptConfigFilename))

        #if the GUI is not shown, check the database connection. If it fails, show the GUI
        if self.exptConfig.get('databaseConnection') and not self.exptConfig.get('showGui'):
            self.dbConnection = DatabaseConnectionSettings(**self.exptConfig['databaseConnection'])
            success = self.attemptDatabaseConnection(self.dbConnection)
            if not success:
                self.exptConfig['showGui']=True

        self.updateExptConfigVersion()

        if self.exptConfig['showGui']:
            ui = ExptConfigUi(self, scriptname)
            ui.show()
            ui.exec_()
            yamldata=self.changeBlankNamesToNone()
            with open(self.exptConfigFilename, 'w') as f: #save information from GUI to file
                yaml.dump(yamldata, f, default_flow_style=False)
                logger.info('GUI data saved to {0}'.format(self.exptConfigFilename))

        self.dbConnection = DatabaseConnectionSettings(**self.exptConfig['databaseConnection'])

        self.setGlobalProject()

    @property
    def name(self):
        return self.projectConfig['name']

    @property
    def baseDir(self):
        return self.projectConfig['baseDir']

    @property
    def hardware(self):
        return self.exptConfig['hardware']

    @property
    def software(self):
        return self.exptConfig['software']

    def __str__(self):
        return self.name

    def setGlobalProject(self):
        global currentProject
        currentProject=self

    @staticmethod
    def attemptDatabaseConnection(dbConn):
        """Attempt to connect to the database"""
        logger = logging.getLogger(__name__)
        try:
            engine = create_engine(dbConn.connectionString, echo=dbConn.echo)
            engine.connect()
            engine.dispose()
            success = True
            logger.info("Database connection successful")
        # except OperationalError as e:
        #     if str(e.orig) == "":
        #         pass
        except Exception as e:
            success = False
            if hasattr(e, 'orig') and str(e.orig).startswith('FATAL:  database "{0}" does not exist'.format(dbConn.database)):
                # connect to template and create database
                try:
                    sqlalchemy_utils.functions.create_database(dbConn.connectionString, encoding='utf8', template='template1')
                    logger.info("Created database '{0}'".format(dbConn.database))
                    success = True
                except Exception as e:
                    logger.error("Creating database '{0}' failed: {1}".format(dbConn.database, str(e)))
            else:
                success = False
                logger.warning("{0}: {1}".format(e.__class__.__name__, e))
                logger.info("Database connection failed - please check settings")
        return success

    def updateExptConfigVersion(self):
        """update config file to latest version"""
        version = self.exptConfig.get('version', 1.0)
        if version < 2.0:
            logger = logging.getLogger(__name__)
            logger.info("Updating experiment config file {0} from v1.0 to v2.0".format(self.exptConfigFilename))
            hardwareCopy = deepcopy(self.exptConfig['hardware'])
            softwareCopy = deepcopy(self.exptConfig['software'])
            self.exptConfig['hardware'].clear()
            self.exptConfig['software'].clear()

            for key, val in hardwareCopy.items():
                if key=='Opal Kelly FPGA: Pulser': #For Opal Kelly FPGAs, now one device with different names
                    self.exptConfig['hardware'].setdefault('Opal Kelly FPGA', dict())
                    self.exptConfig['hardware']['Opal Kelly FPGA']['Pulser'] = val
                elif key=='Opal Kelly FPGA: DAC':
                    self.exptConfig['hardware'].setdefault('Opal Kelly FPGA', dict())
                    self.exptConfig['hardware']['Opal Kelly FPGA']['DAC'] = val
                elif key=='Opal Kelly FPGA: 32 Channel PMT':
                    self.exptConfig['hardware'].setdefault('Opal Kelly FPGA', dict())
                    self.exptConfig['hardware']['Opal Kelly FPGA']['32 Channel PMT'] = val
                elif key=='NI DAC Chassis': #For NI DAC Chassis, name is now dict key rather than field
                    name = val.pop('name')
                    self.exptConfig['hardware'][key] = dict()
                    self.exptConfig['hardware'][key][''] = val
                else: #For all other items, the default name key is set to an empty string
                    self.exptConfig['hardware'][key] = dict()
                    self.exptConfig['hardware'][key][''] = val

            for key, val in softwareCopy.items():
                self.exptConfig['software'][key] = dict()
                self.exptConfig['software'][key][''] = val

            self.exptConfig['version'] = 2.0 #A version number is now stored in the config file, to make things more future-proof
            yamldata=self.changeBlankNamesToNone()
            with open(self.exptConfigFilename, 'w') as f: #save updates to file
                yaml.dump(yamldata, f, default_flow_style=False)
                logger.info('experiment config file {0} updated to v2.0'.format(self.exptConfigFilename))

    def changeBlankNamesToNone(self):
        yamldata=deepcopy(self.exptConfig)
        for guiName in ['hardware', 'software']:
            for objName in self.exptConfig[guiName]:
                for name in self.exptConfig[guiName][objName]:
                    if name=='': #yaml doesn't work nicely with empty string keys for dicts, so we switch them to 'None' for saving only
                        yamldata[guiName][objName][None]=yamldata[guiName][objName].pop(name)
        return yamldata

    def isEnabled(self, guiName, objName):
        """Determine what objects named 'objName' are enabled (if any)
        Args:
            guiName (str): 'hardware' or 'software'
            objName (str): the name of the object in question
        Returns:
         dict of enabled objects 'objName'"""
        objDict=self.exptConfig[guiName].get(objName, dict())
        enabledObjects = {name:nameDict for name, nameDict in objDict.items() if nameDict.get('enabled')}
        return enabledObjects

    def fullName(self, objName, name):
        """return the full name to display associated with objName and name"""
        separator=': '
        return separator.join([objName, name]) if name else objName

    def fromFullName(self, fullName):
        """return the objName,name associated with the given fullName"""
        separator=': '
        return fullName.split(separator) if separator in fullName else (fullName, '')

    def findFile(self, filename):
        if filename is None:
            return None
        if os.path.exists(filename):
            return filename
        project_dir = self.projectDir
        leaf = ''
        for component in path_iter_right(filename):
            leaf = os.path.join(component, leaf) if leaf else component
            test_name = os.path.join(project_dir, leaf)
            if os.path.exists(test_name):
                filename = test_name
                break
        return filename


class ProjectInfoUi(Base, Form):
    """Class for seeing project settings in the main GUI, and setting config GUIs to show on next program start"""
    def __init__(self, project):
        Base.__init__(self)
        Form.__init__(self)
        self.project = project
        self.setupUi(self)

    def setupUi(self, parent):
        """setup the dialog box ui"""
        super(ProjectInfoUi, self).setupUi(parent)
        self.ProjectConfigTextEdit.setText( yaml.dump(self.project.projectConfig, default_flow_style=False) )
        self.ExptConfigTextEdit.setText( yaml.dump(self.project.exptConfig, default_flow_style=False) )
        self.label.setText("Currently running project: <b>{0}</b>".format(self.project))

    def accept(self):
        """update the config files based on the check boxes"""
        if self.showProjectGuiCheckbox.isChecked() and not self.project.projectConfig['showGui']:
            self.project.projectConfig.update({'showGui':True})
            with open(self.project.projectConfigFilename, 'w') as f:
                yaml.dump(self.project.projectConfig, f, default_flow_style=False)
        if self.showExptGuiCheckbox.isChecked() and not self.project.exptConfig['showGui']:
            self.project.exptConfig.update({'showGui':True})
            with open(self.project.exptConfigFilename, 'w') as f:
                yaml.dump(self.project.exptConfig, f, default_flow_style=False)
        Base.accept(self)


class ProjectException(Exception):
    pass


def getProject():
    if not currentProject:
        raise ProjectException('No project set')
    return currentProject


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    app = QtWidgets.QApplication(sys.argv)
    project = Project()
    pass