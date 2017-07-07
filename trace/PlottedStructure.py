

class QubitPlotSettings:
    def __init__(self):
        self.gateSet = None
        self.


class PlottedStructure:
    def __init__(self, traceCollection, qubitData, plaquettes, windowName):
        self.qubitData = qubitData
        self.plaquettes = plaquettes
        self.traceCollection = traceCollection
        self.curvePen = 0
        self.name = 'Qubit'
        self.windowName = windowName

    def plot(self, penindex=-1, style=None):
        pass

    def replot(self):
        pass