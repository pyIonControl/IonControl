import pyqtgraph.widgets.RemoteGraphicsView


class RemoteCustomView(pyqtgraph.widgets.RemoteGraphicsView.RemoteGraphicsView):
    def __init__(self, parent=None, *args, **kwds):
        super().__init__(parent, *args, **kwds)
        self.cp = self._proc._import('uiModules.CoordinatePlotWidget')
