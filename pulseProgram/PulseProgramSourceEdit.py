# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import functools

from PyQt5 import QtCore, QtGui, QtWidgets

from .PulseProgramEditUi import Ui_Form as Form
from _functools import partial
Base = QtWidgets.QWidget

class PulseProgramSourceEdit(Form, Base):
    def __init__(self,mode='pp',parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.highlighted = QtGui.QTextCharFormat()
        self.highlighted.setBackground( QtGui.QBrush(QtCore.Qt.cyan))
        self.selections = list()
        self.findWordOnly = False
        self.findCaseSensitive = False
        self.findText = ''
        self.errorFormat = QtGui.QTextCharFormat()
        self.errorFormat.setBackground(QtCore.Qt.red)
        self.defaultFormat = QtGui.QTextCharFormat()
        self.defaultFormat.setBackground(QtCore.Qt.white)
        self.errorCursor = None
        self.cursorStack = list()
        self.mode = mode
        
    def setupUi(self,parent,extraKeywords1=[], extraKeywords2=[]):
        Form.setupUi(self, parent, extraKeywords1=extraKeywords1, extraKeywords2=extraKeywords2)
        self.findLineEdit.textChanged.connect( self.onFindTextChanged )
        self.findCloseButton.clicked.connect( self.onFindClose )
        self.findMatchCaseCheckBox.stateChanged.connect( partial( self.onFindFlagsChanged, 'findCaseSensitive') )
        self.findWholeWordsCheckBox.stateChanged.connect( partial(self.onFindFlagsChanged, 'findWordOnly') )
        self.findNextButton.clicked.connect( self.onFind )
        self.findPreviousButton.clicked.connect( functools.partial(self.onFind, True))
        self.errorDisplay.hide()
        self.findWidgetFrame.hide()
        self.closeErrorButton.clicked.connect( self.clearHighlightError )
        self.addAction(self.actionFind)
        self.addAction(self.actionFindNext)
        
    def setReadOnly(self, enabled):
        self.textEdit.setReadOnly(enabled)
        
    def onFindFlagsChanged(self, attr, state):
        setattr( self, attr, state==QtCore.Qt.Checked)
        
    def onFindClose(self):
        self.findWidgetFrame.hide()

    def setPlainText(self, text):
        self.textEdit.setPlainText(text)

    def toPlainText(self):
        return self.textEdit.toPlainText()
        
    def onFind(self,backward=False, inPlace=False):
        if inPlace or backward:
            line, index, _, _ = self.textEdit.getSelection()
        else:
            _, _, line, index = self.textEdit.getSelection()
        if line<0:
            line, index = self.textEdit.cursorPosition()
        self.textEdit.findFirst(self.findText, False, self.findCaseSensitive, 
                                self.findWordOnly, True, not backward, line, index)
        
    def onFindTextChanged(self, text):
        self.findText = str(text)
        self.onFind(inPlace=True)
        
    def keyReleaseEvent(self, event):
        if event.matches(QtGui.QKeySequence.Find):
            self.showFindDialog()
        elif event.matches(QtGui.QKeySequence.FindNext):
            self.findWidgetFrame.show()
        elif event.matches(QtGui.QKeySequence.FindPrevious):
            self.findWidgetFrame.show()
        else:
            Base.keyReleaseEvent(self, event)
            
    def highlightError(self, message, line, text=None, col=None):
        self.errorLabel.setText( message )
        self.errorDisplay.show()
        self.textEdit.highlightError(line, col, line, -1)
       
    def clearHighlightError(self):
        self.errorDisplay.hide()
        self.textEdit.clearError()
        
    def highlightTimingViolation(self, linelist ):
        self.textEdit.highlightTimingViolation(linelist)
                            
         
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ui = PulseProgramSourceEdit()
    ui.setupUi(ui)
    ui.show()
    sys.exit(app.exec_())
