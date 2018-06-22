# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtCore, QtWidgets
import PyQt5.uic

from .GlobalVariablesModel import GlobalVariablesModel, MagnitudeSpinBoxGridDelegate, GridDelegate
from .GlobalVariable import GlobalVariable, GlobalVariablesLookup
from modules.GuiAppearance import restoreGuiState, saveGuiState   #@UnresolvedImport
from functools import partial
import logging
import os
from copy import copy

uipath = os.path.join(os.path.dirname(__file__), '..', r'ui/GlobalVariables.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class GlobalVariablesUi(Form, Base):
    """Class for displaying, adding, and modifying global variables"""
    def __init__(self, config, parent=None):
        Form.__init__(self)
        Base.__init__(self, parent)
        self.config = config
        self.configName = 'GlobalVariables'
        try:
            storedGlobals = dict(self.config.items_startswith(self.configName + ".dict."))
            if not storedGlobals:
                storedGlobals = self.config.get(self.configName, dict())
                if storedGlobals.__class__==list: #port over globals stored as a list
                    storedGlobals = {g.name:g for g in storedGlobals}
                if type(storedGlobals) is not dict:
                    storedGlobals = dict(storedGlobals)
                # make sure that GlobalVariable type is the newest type
                for key in storedGlobals.keys():
                    if not hasattr(storedGlobals[key], '_name'):
                        oldCategories = storedGlobals[key].__dict__.get('categories', None)
                        storedGlobals[key] = GlobalVariable(key, storedGlobals[key].value, oldCategories)
        except:
            storedGlobals = dict()
        self._globalDict_ = storedGlobals
        # make sure the internal name matches the key
        for key, value in self._globalDict_.items():
            value._name = key
        self.globalDict = GlobalVariablesLookup(self._globalDict_)

    @property
    def valueChanged(self):
        return self.model.valueChanged

    def keys(self):
        return list(self.globalDict.keys())

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.model = GlobalVariablesModel(self.config, self._globalDict_)
        self.model.showGrid = self.config.get(self.configName+".showGrid", True)
        self.showGridButton.setChecked( self.model.showGrid )

        self.view.setModel(self.model)
        self.nameDelegate = GridDelegate()
        self.valueDelegate = MagnitudeSpinBoxGridDelegate()
        self.view.setItemDelegateForColumn(self.model.column.name, self.nameDelegate)
        self.view.setItemDelegateForColumn(self.model.column.value, self.valueDelegate)
        restoreGuiState( self, self.config.get(self.configName+".guiState") )
        try:
            self.view.restoreTreeMarkup(self.config.get(self.configName + '.treeMarkup', None))
            self.view.restoreTreeColumnWidth(self.config.get(self.configName + '.treeColumnWidth', None))
        except Exception as e:
            logging.getLogger(__name__).error("unable to restore tree state in {0}: {1}".format(self.configName, e))

        #signals
        self.newNameEdit.returnPressed.connect( self.onAddVariable )
        self.addButton.clicked.connect( self.onAddVariable )
        self.dropButton.clicked.connect( self.view.onDelete )
        self.collapseAllButton.clicked.connect( self.view.collapseAll )
        self.expandAllButton.clicked.connect( self.view.expandAll )
        self.model.globalRemoved.connect( self.refreshCategories )
        self.showGridButton.clicked.connect( self.onShowGrid )

        #Categorize Context Menu
        self.setContextMenuPolicy( QtCore.Qt.ActionsContextMenu )
        categorizeAction = QtWidgets.QAction("Categorize", self)
        self.categorizeMenu = QtWidgets.QMenu(self)
        categorizeAction.setMenu(self.categorizeMenu)
        self.addAction(categorizeAction)
        self.categoriesListModel = QtCore.QStringListModel()
        self.categoriesListComboBox.setModel(self.categoriesListModel)
        self.refreshCategories()

        #background color context menu
        backgroundColorAction = QtWidgets.QAction("Background Color", self)
        backgroundColorMenu = QtWidgets.QMenu(self)
        backgroundColorAction.setMenu(backgroundColorMenu)
        self.addAction(backgroundColorAction)
        setBackgroundColorAction = QtWidgets.QAction("Set Background Color", self)
        setBackgroundColorAction.triggered.connect(self.view.onSetBackgroundColor)
        backgroundColorMenu.addAction(setBackgroundColorAction)
        removeBackgroundColorAction = QtWidgets.QAction("Remove Background Color", self)
        removeBackgroundColorAction.triggered.connect(self.view.onRemoveBackgroundColor)
        backgroundColorMenu.addAction(removeBackgroundColorAction)

        #sort context action
        sortAction = QtWidgets.QAction("Sort", self)
        self.addAction(sortAction)
        sortAction.triggered.connect(partial(self.view.sortByColumn, self.model.column.name, QtCore.Qt.DescendingOrder))

    def onShowGrid(self, showGrid):
        state = self.view.treeState()
        self.model.beginResetModel()
        self.model.showGrid = showGrid
        self.model.endResetModel()
        self.view.restoreTreeState(state)

    def refreshCategories(self):
        """Set up the categories context menu and combo box"""
        self.categorizeMenu.clear()
        newCategoryAction = QtWidgets.QAction("New category", self)
        self.categorizeMenu.addAction(newCategoryAction)
        newCategoryAction.triggered.connect(self.onNewCategory)
        noCategoryAction = QtWidgets.QAction("No category", self)
        noCategoryAction.triggered.connect(partial(self.onCategorize, None))
        self.categorizeMenu.addAction(noCategoryAction)
        self.categoriesList = ['']
        self.categoriesListModel.setStringList(self.categoriesList)
        for var in list(self._globalDict_.values()):
            categories = copy(var.categories)
            if categories:
                categories = [categories] if categories.__class__!=list else categories # make a list of one if it's not a list
                categories = list(map(str, categories)) #make sure it's a list of strings
                categories = '.'.join(categories)
                self.addCategories(categories)

    def addCategories(self, categories):
        """add the specified categories to the context menu and combo box
        Args:
            categories (str): a single category, or a dotted string containing a list of categories (a.b.c)
            """
        if categories not in self.categoriesList:
            self.categoriesList.append(categories)
            self.categoriesListModel.setStringList(self.categoriesList)
            action = QtWidgets.QAction(categories, self)
            self.categorizeMenu.addAction(action)
            action.triggered.connect(partial(self.onCategorize, categories))

    def onNewCategory(self):
        """new category action selected from context menu"""
        categories, ok = QtWidgets.QInputDialog.getText(self, 'New category', 'Please enter new category(ies) (dot sub-categories: cat1.cat2.cat3): ')
        if ok:
            categories = str(categories).strip('.')
            self.addCategories(categories)
            self.onCategorize(categories)

    def onCategorize(self, categories):
        """categorize the selected nodes under 'categories'
        Args:
            categories (str): a single category, or a dotted string containing a list of categories (a.b.c)
            """
        if categories:
            categories = categories.split('.')
        nodes = self.view.selectedNodes()
        for node in nodes:
            self.model.changeCategory(node, categories)
            self.view.expandToNode(node)
        self.refreshCategories()

    def onAddVariable(self):
        """A new variable is added via the UI, either by typing in a name and pressing enter, or by clicking add."""
        name = str(self.newNameEdit.text())
        categories = str(self.categoriesListComboBox.currentText())
        categories = categories.strip('.')
        node = self.model.addVariable(name, categories.split('.'))
        if node:
            self.view.expandToNode(node)
        self.newNameEdit.setText("")
        self.addCategories(categories)
        blankInd = self.categoriesListComboBox.findText('', QtCore.Qt.MatchExactly)
        self.categoriesListComboBox.setCurrentIndex(blankInd)

    def saveConfig(self):
        """save gui configuration state and _globalDict_"""
        self.config.set_string_dict(self.configName + ".dict", self._globalDict_)
        self.config[self.configName+".guiState"] = saveGuiState(self)
        self.config[self.configName+".showGrid"] = self.model.showGrid
        try:
            self.config[self.configName + '.treeMarkup'] = self.view.treeMarkup()
            self.config[self.configName + '.treeColumnWidth'] = self.view.treeColumnWidth()
        except Exception as e:
            logging.getLogger(__name__).error("unable to save tree state in {0}: {1}".format(self.configName, e))

    def update(self, updlist):
        """Update list of globals"""
        self.model.update(updlist)


if __name__=="__main__":
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = GlobalVariableUi(config)
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
