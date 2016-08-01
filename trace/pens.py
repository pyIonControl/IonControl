# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

"""
penList is a list of 4-tuples. It is used to define how to plot a trace.
The first element of the tuple is the pen to use for drawing solid curves. The
second element is the symbol to use for plotting datapoints. The third element
is the pen to use for the symbol. The fourth element is the brush to use to
fill in the symbol.

Symbol letters are:
    's': square
    'o': circle
    't': triangle
    'd': diamond
"""

from PyQt5 import QtCore, QtGui
from pyqtgraph import mkPen, mkBrush

from ui import Experiment_rc #@UnusedImport


yellow = (180, 180, 0, 255)
orange = (247, 153, 0)
green = (0, 180, 0, 255)
blue = (0, 0, 255, 255)
red = (255, 0, 0, 255)
cyan = (0, 200, 200, 255)
magenta = (255, 0, 255, 255)
black = (0, 0, 0, 255)
white = (255, 255, 255, 255)
aquamarine = (0, 200, 145, 255)
lightblue = (0, 191, 255, 255)
purple = (144, 0, 255, 255)
darkpink = (255, 0, 157, 255)

blank = None
penWidth = 2
solid = QtCore.Qt.SolidLine
dashed = QtCore.Qt.DashLine

solidYellowPen = mkPen(yellow, width=penWidth, style=solid)
dashedYellowPen = mkPen(yellow, width=penWidth, style=dashed)

solidOrangePen = mkPen(orange, width=penWidth, style=solid)
dashedOrangePen = mkPen(orange, width=penWidth, style=dashed)

solidRedPen = mkPen(red, width=penWidth, style=solid)
dashedRedPen = mkPen(red, width=penWidth, style=dashed) 

solidGreenPen = mkPen(green, width=penWidth, style=solid)
dashedGreenPen = mkPen(green, width=penWidth, style=dashed)

solidBluePen = mkPen(blue, width=penWidth, style=solid)
dashedBluePen = mkPen(blue, width=penWidth, style=dashed)

solidCyanPen = mkPen(cyan, width=penWidth, style=solid)
dashedCyanPen = mkPen(cyan, width=penWidth, style=dashed)
cyanBrush = mkBrush(cyan)

solidMagentaPen = mkPen(magenta, width=penWidth, style=solid)
dashedMagentaPen = mkPen(magenta, width=penWidth, style=dashed)
magentaBrush = mkBrush(magenta)

solidBlackPen = mkPen(black, width=penWidth, style=solid)
dashedBlackPen = mkPen(black, width=penWidth, style=dashed)
blackBrush = mkBrush(black)

solidAquamarinePen = mkPen(aquamarine, width=penWidth, style=solid)
dashedAquamarinePen = mkPen(aquamarine, width=penWidth, style=dashed)

solidLightBluePen = mkPen(lightblue, width=penWidth, style=solid)
dashedLightBluePen = mkPen(lightblue, width=penWidth, style=dashed)

solidPurplePen = mkPen(purple, width=penWidth, style=solid)
dashedPurplePen = mkPen(purple, width=penWidth, style=dashed)

solidDarkPinkPen = mkPen(darkpink, width=penWidth, style=solid)
dashedDarkPinkPen = mkPen(darkpink, width=penWidth, style=dashed)

penList = [ (solidYellowPen,),
            (solidBluePen, 'd', solidBluePen, blank, blue),
            (solidRedPen, 'o', solidRedPen, blank, red),
            (solidGreenPen, 't', solidGreenPen, blank, green),
            (solidOrangePen, 's', solidOrangePen, blank, yellow),
            (solidCyanPen, 's', None, cyanBrush, cyan),
            (solidMagentaPen, 'o', None, magentaBrush, magenta),
            (solidBlackPen, 't', None, blackBrush, black),
            (solidAquamarinePen, 's', solidAquamarinePen, blank, aquamarine),
            (solidLightBluePen, 'o', solidLightBluePen, blank, lightblue),
            (solidPurplePen, 't', solidPurplePen, blank, purple),
            (solidDarkPinkPen, 'd', solidDarkPinkPen, blank, darkpink),
            (dashedYellowPen, 's', dashedYellowPen, blank, yellow),
            (dashedRedPen, 'o', dashedRedPen, blank, red),
            (dashedGreenPen, 't', dashedGreenPen, blank, green),
            (dashedBluePen, 'd', dashedBluePen, blank, blue),
            (dashedCyanPen, 's', None, cyanBrush, cyan),
            (dashedMagentaPen, 'o', None, magentaBrush, magenta),
            (dashedBlackPen, 't', None, blackBrush, black) ,
            (dashedOrangePen, 's', dashedOrangePen, blank, orange),
            (dashedAquamarinePen, 's', dashedAquamarinePen, blank, aquamarine),
            (dashedLightBluePen, 'o', dashedLightBluePen, blank, lightblue),
            (dashedPurplePen, 't', dashedPurplePen, blank, purple),
            (dashedDarkPinkPen, 't', dashedDarkPinkPen, blank, darkpink)]

class penicons:
    def penicons(self):
        if not hasattr(self, 'icons'):
            self.loadicons()
        return self.icons
        
    def loadicons(self):
        self.icons = [ QtGui.QIcon(), 
            QtGui.QIcon(":/penicon/icons/blue.png"),
            QtGui.QIcon(":/penicon/icons/red.png"),
            QtGui.QIcon(":/penicon/icons/green.png"),
            QtGui.QIcon(":/penicon/icons/247-153-0.png"),
            QtGui.QIcon(":/penicon/icons/cyan.png"),
            QtGui.QIcon(":/penicon/icons/magenta.png"),
            QtGui.QIcon(":/penicon/icons/white.png"),
            QtGui.QIcon(":/penicon/icons/0-255-200.png"),
            QtGui.QIcon(":/penicon/icons/0-191-255.png"),
            QtGui.QIcon(":/penicon/icons/144-0-255.png"),
            QtGui.QIcon(":/penicon/icons/255-0-157.png"),
            QtGui.QIcon(":/penicon/icons/yellow-dash.png"),
            QtGui.QIcon(":/penicon/icons/red-dash.png"),
            QtGui.QIcon(":/penicon/icons/green-dash.png"),
            QtGui.QIcon(":/penicon/icons/blue-dash.png"),
            QtGui.QIcon(":/penicon/icons/cyan-dash.png"),
            QtGui.QIcon(":/penicon/icons/magenta-dash.png"),
            QtGui.QIcon(":/penicon/icons/white-dash.png"),
            QtGui.QIcon(":/penicon/icons/orange-dash.png"),
            QtGui.QIcon(":/penicon/icons/aquamarine-dash.png"),
            QtGui.QIcon(":/penicon/icons/light-blue-dash.png"),
            QtGui.QIcon(":/penicon/icons/purple-dash.png"),
            QtGui.QIcon(":/penicon/icons/dark-pink-dash.png")]
