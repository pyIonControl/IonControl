

class PlottedStructure:
    def __init__(self, traceCollection, key):
        self.key = key
        self.traceCollection = traceCollection
        self.curvePen = 0
        self.name = ''
        self.windowName = ''

    def plot(self, penindex=-1, style=None):
        pass

    def replot(self):
        pass