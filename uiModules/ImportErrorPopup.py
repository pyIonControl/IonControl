# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from PyQt5 import QtGui, QtWidgets
import sys

def importErrorPopup(moduleName):
    messageBox = QtWidgets.QMessageBox()
    response = messageBox.warning(messageBox,
                                  'Import Failure',
                                  '{0} module is listed as enabled in the configuration file, but the import failed. Proceed without?'.format(moduleName),
                                  QtWidgets.QMessageBox.Cancel | QtWidgets.QMessageBox.Ok)
    if response!=QtWidgets.QMessageBox.Ok:
        sys.exit('{0} import failure'.format(moduleName))

if __name__=='__main__':
    app = QtWidgets.QApplication(sys.argv)
    importErrorPopup('myModule')