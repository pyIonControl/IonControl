# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import os
from os.path import basename, exists
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtProperty, pyqtSlot
from modules.PyqtUtility import BlockSignals
import PyQt5.uic

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/FileComboWidget.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)

class FileComboWidget(Base, Form):
    """Ui for opening files."""
    openFileSignal = QtCore.pyqtSignal(str, bool) #filename, True if file is new
    saveFileSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """initialize and setup the widget"""
        super(FileComboWidget, self).__init__(parent)
        self._defaultDir = "/" #used in file dialog for opening and saving files
        self._fileType = "All types (*.*)" #used in file dialog for opening and saving files
        self._recentFiles = [] #list of full filenames, including path
        self._currentFile = '' #full filename, including path

        super(FileComboWidget, self).setupUi(self)
        self.filenameComboBox.setValidator( QtGui.QRegExpValidator() ) #verifies that files typed into combo box can be used
        self.updateValidator()
        self.filenameComboBox.currentIndexChanged[int].connect(self.onFilenameChange)
        self.actionOpen.triggered.connect( self.onOpen )
        self.openButton.setDefaultAction( self.actionOpen )
        self.removeCurrent.clicked.connect( self.onRemoveCurrent )
        self.readOnly = False

    @pyqtProperty(str)
    def defaultDir(self):
        return self._defaultDir

    @defaultDir.setter
    def defaultDir(self, newdir):
        """Set defaultDir, if it exists and can be created"""
        if newdir and newdir != self._defaultDir:
            if not exists(newdir):
                try:
                    os.makedirs(newdir)
                except:
                    newdir = "/"
        self._defaultDir=newdir

    @pyqtProperty(str)
    def fileType(self):
        return self._fileType

    @fileType.setter
    def fileType(self, s):
        """set fileType"""
        if s != self._fileType:
            self._fileType=s

    @pyqtProperty(bool)
    def readOnly(self):
        return self._readOnly

    @readOnly.setter
    def readOnly(self, b):
        """Set readOnly. If it is False, enable and connect write buttons. Otherwise, disable and hide them."""
        if b != getattr(self, "_readOnly", None):
            self._readOnly=b
            if not b:
                self.newButton.show()
                self.saveButton.show()
                self.resetButton.show()
                self.newButton.setEnabled(True)
                self.saveButton.setEnabled(True)
                self.resetButton.setEnabled(True)
                self.actionNew.setEnabled(True)
                self.actionSave.setEnabled(True)
                self.actionReset.setEnabled(True)
                self.actionNew.triggered.connect( self.onNew )
                self.actionSave.triggered.connect( self.onSave )
                self.actionReset.triggered.connect( self.onReset )
                self.newButton.setDefaultAction( self.actionNew )
                self.saveButton.setDefaultAction( self.actionSave )
                self.resetButton.setDefaultAction( self.actionReset )
            else: #We disable new, save, and reset if the file is to be read only
                self.newButton.hide()
                self.saveButton.hide()
                self.resetButton.hide()
                self.newButton.setDisabled(True)
                self.saveButton.setDisabled(True)
                self.resetButton.setDisabled(True)
                self.actionNew.setDisabled(True)
                self.actionSave.setDisabled(True)
                self.actionReset.setDisabled(True)

    @pyqtProperty(list)
    def recentFiles(self):
        return self._recentFiles

    @recentFiles.setter
    def recentFiles(self, filenames):
        """set recentFiles. Clear the combo box, add the filenames, and update the validator."""
        filenames = [s for s in filenames if isinstance(s, str)]
        if self._recentFiles != filenames:
            self._recentFiles = filenames
            with BlockSignals(self.filenameComboBox) as w:
                w.clear()
                for filename in filenames:
                    if filename and exists(filename):
                        w.addItem(basename(filename), filename)
                self.updateValidator()

    @pyqtProperty(str)
    def currentFile(self):
        return self._currentFile

    @currentFile.setter
    def currentFile(self, filename):
        """set currentFile, if it exists and is in recentFiles. Set combo box to match."""
        filename = str(filename)
        if (filename != self._currentFile) and exists(filename) and (filename in self.recentFiles):
            self._currentFile = filename
            with BlockSignals(self.filenameComboBox) as w:
                w.setCurrentIndex( w.findText(basename(filename)) )

    def openFile(self, filename, new=False):
        """open the file 'filename.' 'new' indicates if this is a new file or not. """
        if isinstance(filename, str):
            if filename not in self.recentFiles:
                self.recentFiles = self.recentFiles + [filename] #update recentFiles, which will populate combo box
            self.currentFile = filename #update currentFile, which will update combo box index
            self.openFileSignal.emit(filename, new)

    @pyqtSlot()
    def onOpen(self):
        """The open button is clicked. Open file prompt for file."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', self.defaultDir, self.fileType)
        if filename:
            self.openFile(filename, new=False)

    @pyqtSlot()
    def onNew(self):
        """The new button is clicked. Open file prompt for new file."""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'New File Name', self.defaultDir, self.fileType)
        if filename:
            if not exists(filename):
                with open(filename, 'w'): pass #open file, don't do anything with it
                self.openFile(filename, new=True)
            else:
                self.openFile(filename, new=False)

    @pyqtSlot()
    def onSave(self):
        """save button is clicked"""
        self.saveFileSignal.emit()

    @pyqtSlot()
    def onReset(self):
        """reset button is clicked"""
        self.openFileSignal.emit(self.currentFile, False)

    @pyqtSlot()
    def onRemoveCurrent(self):
        """Remove current button is clicked. Remove file from combo box."""
        ind = self.filenameComboBox.currentIndex()
        filename = self.getFilename(ind) #get filename with path
        if filename in self.recentFiles:
            self.recentFiles = [s for s in self.recentFiles if s != filename]
            ind = self.filenameComboBox.currentIndex()
            self.openFile( self.getFilename(ind) )

    @pyqtSlot(int)
    def onFilenameChange(self, ind):
        """The combo box is changed."""
        filename = self.getFilename(ind)
        self.openFile(filename)

    def getFilename(self, ind):
        return self.filenameComboBox.itemData(ind)

    def updateValidator(self):
        """Make the validator match the recentFiles list. Uses regExp \\b(f1|f2|f3...)\\b, where fn are filenames."""
        regExp = '\\b('
        for filename in self.recentFiles:
            if filename:
                regExp += basename(filename) + '|'
        rexExp = regExp[:-1] #drop last pipe symbol
        regExp += ')\\b'
        self.filenameComboBox.validator().setRegExp(QtCore.QRegExp(regExp))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = FileComboWidget()
    ui.show()
    sys.exit(app.exec_())




