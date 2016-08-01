# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import logging

from pyqtgraph.graphicsItems.AxisItem import AxisItem


class SceneToPrint:
    def __init__(self, widget, gridLinewidth=1, curveLinewidth=1):
        self.widget = widget
        self.gridLinewidth = gridLinewidth
        self.curveLinewidth = curveLinewidth

    def __enter__(self):
        self.widget._graphicsView.hideAllButtons(True)
        self.pencache = dict()
        if hasattr(self.widget, 'coordinateLabel'):
            self.widget.coordinateLabel.hide()
        if self.gridLinewidth != 1 or self.curveLinewidth != 1:
            for item in self.widget._graphicsView.scene().items():
                if hasattr(item, 'pen') and isinstance(item, AxisItem) and self.gridLinewidth != 1:
                    pen = item.pen()
                    width = pen.width()
                    if id(pen) in self.pencache:
                        logging.getLogger(__name__).info("did not expect to find item in pencache")
                    self.pencache[id(pen)] = (pen, item, width)
                    pen.setWidth(width * self.gridLinewidth)
                    item.setPen(pen)
                elif hasattr(item, 'opts') and self.curveLinewidth != 1:
                    shadowPen = item.opts.get('shadowPen')
                    pen = item.opts.get('pen')
                    if pen is not None:
                        if id(pen) in self.pencache:
                            logging.getLogger(__name__).info("did not expect to find pen in pencache")
                        else:
                            self.pencache[id(pen)] = (pen, None, pen.width())
                            pen.setWidth(pen.width() * self.curveLinewidth)
                    if shadowPen is not None:
                        if id(shadowPen) in self.pencache:
                            logging.getLogger(__name__).info("did not expect to find pen in pencache")
                        else:
                            self.pencache[id(shadowPen)] = (shadowPen, None, shadowPen.width())
                            shadowPen.setWidth(shadowPen.width() * self.curveLinewidth)
        return self.widget

    def __exit__(self, exittype, value, traceback):
        self.widget._graphicsView.hideAllButtons(False)
        if hasattr(self.widget, 'coordinateLabel'):
            self.widget.coordinateLabel.show()
        for penid, (pen, item, width) in self.pencache.items():
            if item is not None:
                pen = item.pen()
                pen.setWidth(width)
                item.setPen(pen)
            else:
                pen.setWidth(width)

            #         for item,(shadowWidth,width) in self.curveitemcache.items():

# if shadowWidth is not None:
#                 item.opts['shadowPen'].setWidth(shadowWidth)
#             if width is not None:
#                 item.opts['pen'].setWidth(width)
