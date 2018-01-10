# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************


from pyqtgraphAddons.DateAxisItem import DateAxisItem
from uiModules.CoordinatePlotWidget import CoordinatePlotWidget
import math
from modules.round import roundToNDigits
from datetime import datetime

class DateTimePlotWidget(CoordinatePlotWidget):
    """This is the main widget for plotting data. It consists of a plot, a
       coordinate display, and custom buttons."""
    def __init__(self, parent=None, name=None):
        self.dateAxisItem = DateAxisItem('bottom')
        super(DateTimePlotWidget, self).__init__(parent, axisItems={'bottom': self.dateAxisItem}, name=name)

    def onMouseMoved(self, pos):
        """Execute when mouse is moved. If mouse is over plot, show cursor
           coordinates on coordinateLabel."""
        if self._graphicsView.sceneBoundingRect().contains(pos):
            try:
                self.mousePoint = self._graphicsView.vb.mapSceneToView(pos)
                logY = self._graphicsView.ctrl.logYCheck.isChecked()
                y = self.mousePoint.y() if not logY else pow(10, self.mousePoint.y())
                vR = self._graphicsView.vb.viewRange()
                deltaY = vR[1][1]-vR[1][0] if not logY else pow(10, vR[1][1])-pow(10, vR[1][0]) #Calculate x and y display ranges
                precy = int( math.ceil( math.log10(abs(y/deltaY)) ) + 3 ) if y!=0 and deltaY>0 else 1
                roundedy = roundToNDigits(y, precy )
                currentDateTime = datetime.fromtimestamp(self.mousePoint.x()) 
                self.coordinateLabel.setText( self.template.format( str(currentDateTime), repr(roundedy) ))
            except (ValueError, OSError):
                pass


if __name__ == '__main__':
    from PyQt5 import QtGui, QtWidgets
    from uiModules import CoordinatePlotWidget as cw
    
    cw.icons_dir = '../ui/icons/'
    cw.range_icon_file = cw.icons_dir + 'unity-range'
    cw.holdZero_icon_file = cw.icons_dir + 'hold-zero'
    import sys    
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    myPlotWidget = DateTimePlotWidget()
    MainWindow.setCentralWidget(myPlotWidget)
    pi = myPlotWidget.getItem(0, 0)
    pi.plot(x = [0, 3600, 7200, 10800], y = [9, 16, 25, 36])

    MainWindow.show()
    sys.exit(app.exec_())
    
