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

def filterPen(inpen, isbrush=False):
    if inpen is None:
        return None
    origColor = inpen.color().getRgb()
    newColor = tuple((origColor[i]+510)//3 if i < 3 else 255 for i in range(4))
    if isbrush:
        return mkBrush(newColor)
    return mkPen(newColor, width=inpen.width(), style=inpen.style())

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
transparentgray = (127, 127, 127, 127)

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

solidTransparentGrayPen = mkPen(transparentgray, width=penWidth, style=solid)
dashedTransparentGrayPen = mkPen(transparentgray, width=penWidth, style=dashed)

penList = [ (solidYellowPen,),
            (solidBluePen, 'd', solidBluePen, blank, blue, filterPen(solidBluePen), filterPen(blank, isbrush=True)),
            (solidRedPen, 'o', solidRedPen, blank, red, filterPen(solidRedPen), filterPen(blank, isbrush=True)),
            (solidGreenPen, 't', solidGreenPen, blank, green, filterPen(solidGreenPen), filterPen(blank, isbrush=True)),
            (solidOrangePen, 's', solidOrangePen, blank, yellow, filterPen(solidOrangePen), filterPen(blank, isbrush=True)),
            (solidCyanPen, 's', None, cyanBrush, cyan, filterPen(solidCyanPen), filterPen(cyanBrush, isbrush=True)),
            (solidMagentaPen, 'o', None, magentaBrush, magenta, filterPen(solidMagentaPen), filterPen(magentaBrush, isbrush=True)),
            (solidBlackPen, 't', None, blackBrush, black, filterPen(solidBlackPen), filterPen(blackBrush, isbrush=True)),
            (solidAquamarinePen, 's', solidAquamarinePen, blank, aquamarine, filterPen(solidAquamarinePen), filterPen(blank, isbrush=True)),
            (solidLightBluePen, 'o', solidLightBluePen, blank, lightblue, filterPen(solidLightBluePen), filterPen(blank, isbrush=True)),
            (solidPurplePen, 't', solidPurplePen, blank, purple, filterPen(solidPurplePen), filterPen(blank, isbrush=True)),
            (solidDarkPinkPen, 'd', solidDarkPinkPen, blank, darkpink, filterPen(solidDarkPinkPen), filterPen(blank, isbrush=True)),
            (dashedYellowPen, 's', dashedYellowPen, blank, yellow, filterPen(dashedYellowPen), filterPen(blank, isbrush=True)),
            (dashedRedPen, 'o', dashedRedPen, blank, red, filterPen(dashedRedPen), filterPen(blank, isbrush=True)),
            (dashedGreenPen, 't', dashedGreenPen, blank, green, filterPen(dashedGreenPen), filterPen(blank, isbrush=True)),
            (dashedBluePen, 'd', dashedBluePen, blank, blue, filterPen(dashedBluePen), filterPen(blank, isbrush=True)),
            (dashedCyanPen, 's', None, cyanBrush, cyan, filterPen(dashedCyanPen), filterPen(cyanBrush, isbrush=True)),
            (dashedMagentaPen, 'o', None, magentaBrush, magenta, filterPen(dashedMagentaPen), filterPen(magentaBrush, isbrush=True)),
            (dashedBlackPen, 't', None, blackBrush, black, filterPen(dashedBlackPen), filterPen(blackBrush, isbrush=True)) ,
            (dashedOrangePen, 's', dashedOrangePen, blank, orange, filterPen(dashedOrangePen), filterPen(blank, isbrush=True)),
            (dashedAquamarinePen, 's', dashedAquamarinePen, blank, aquamarine, filterPen(dashedAquamarinePen), filterPen(blank, isbrush=True)),
            (dashedLightBluePen, 'o', dashedLightBluePen, blank, lightblue, filterPen(dashedLightBluePen), filterPen(blank, isbrush=True)),
            (dashedPurplePen, 't', dashedPurplePen, blank, purple, filterPen(dashedPurplePen), filterPen(blank, isbrush=True)),
            (dashedDarkPinkPen, 't', dashedDarkPinkPen, blank, darkpink, filterPen(dashedDarkPinkPen), filterPen(blank, isbrush=True))]

penArgList = [{'color': yellow, 'width': penWidth, 'style': solid},
              {'color': blue, 'width': penWidth, 'style': solid},
              {'color': red, 'width': penWidth, 'style': solid},
              {'color': orange, 'width': penWidth, 'style': solid},
              {'color': cyan, 'width': penWidth, 'style': solid},
              {'color': magenta, 'width': penWidth, 'style': solid},
              {'color': black, 'width': penWidth, 'style': solid},
              {'color': aquamarine, 'width': penWidth, 'style': solid},
              {'color': lightblue, 'width': penWidth, 'style': solid},
              {'color': purple, 'width': penWidth, 'style': solid},
              {'color': darkpink, 'width': penWidth, 'style': solid},
              {'color': yellow, 'width': penWidth, 'style': dashed},
              {'color': blue, 'width': penWidth, 'style': dashed},
              {'color': red, 'width': penWidth, 'style': dashed},
              {'color': orange, 'width': penWidth, 'style': dashed},
              {'color': cyan, 'width': penWidth, 'style': dashed},
              {'color': magenta, 'width': penWidth, 'style': dashed},
              {'color': black, 'width': penWidth, 'style': dashed},
              {'color': aquamarine, 'width': penWidth, 'style': dashed},
              {'color': lightblue, 'width': penWidth, 'style': dashed},
              {'color': purple, 'width': penWidth, 'style': dashed},
              {'color': darkpink, 'width': penWidth, 'style': dashed},
              ]

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
