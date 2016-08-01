# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

from PyQt5 import QtCore, QtGui, QtWidgets


class RedBlackComboBox( QtWidgets.QComboBox ):
    def __init__(self,parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.unselectableItems = set()
        self.currentIndexChanged[str].connect(self.onCurrentIndexChanged)
        
    def addUnselectableItems(self, itemlist):
        for item in itemlist:
            if item not in self.unselectableItems:
                self.unselectableItems.add(item)
                self.addItem(item)
                index = self.model().index( self.findText(item), self.modelColumn(), self.rootModelIndex() )
                item = self.model().itemFromIndex( index )
                item.setSelectable(False)
                item.setForeground( QtGui.QBrush( QtCore.Qt.red ))
        self.highlightCurrentAsUnselectable( str(self.currentText()) in self.unselectableItems )
                
    def highlightCurrentAsUnselectable(self, unselectable=True):
        if unselectable:
            self.setStyleSheet("QComboBox {color:red; }")
        else:
            self.setStyleSheet("")
                
    def onCurrentIndexChanged(self, item):
        self.highlightCurrentAsUnselectable( str(item) in self.unselectableItems )
            
    def findText(self, text, flags = QtCore.Qt.MatchCaseSensitive | QtCore.Qt.MatchExactly ):
        """Add searched item as unselectable item if it is not available in the regular items"""
        index = super(RedBlackComboBox, self).findText(text, flags)
        if index<0:
            self.addUnselectableItems([text])
            index = super(RedBlackComboBox, self).findText(text, flags)
        return index
    
    def clear(self):
        super(RedBlackComboBox, self).clear()
        self.unselectableItems = set()
        self.highlightCurrentAsUnselectable(False)

if __name__=="__main__":
    import PyQt5.uic
    Form, Base = PyQt5.uic.loadUiType(r'ui\SingleComboBox.ui')

    class TestUi(Form, Base ):
        def __init__(self,parent=None):
            Form.__init__(self)
            Base.__init__(self, parent)
 
        def setupUi(self, parent):
            Form.setupUi(self, parent)
            self.comboBox.addUnselectableItems(["Unselectable"])
            self.comboBox.addItems(["One", "Two"])

   
    import sys
    config = dict()
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = TestUi()
    ui.setupUi(ui)
    MainWindow.setCentralWidget(ui)
    MainWindow.show()
    sys.exit(app.exec_())
        