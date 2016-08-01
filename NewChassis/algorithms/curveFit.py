# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
import numpy as np
from scipy.optimize import curve_fit 
from matplotlib import pyplot


class Fit(object):
    def __init__(self):
        self.popt = None
        self.pconv = None
        self.x = None
        self.y = None
        self.result = None

    def func(self):
        pass

    def curve_fit(self, x, y):
        self.x = x
        self.y = y
        self.popt, self.pconv = curve_fit(self.func, x, y)

    def plot(self):
        pyplot.plot(self.x, self.y, '.')
        pyplot.plot(self.x, self.result)
        pyplot.show()

    def max_point(self):
        maxIdx = np.argmax(self.result)
        x = self.x[maxIdx]
        y = self.result[maxIdx]
        return x, y

class GaussianFit(Fit):
    def func(self, x, a, b, c):
        y = a* np.exp(-(x-b) ** 2 / (2 * c ** 2))
        return y

    def curve_fit(self, x, y):
        super(GaussianFit, self).curve_fit(x, y)
        self.result = self.func(x,
                self.popt[0], self.popt[1], self.popt[2])
        return self.result

class LinearFit(Fit):
    def func(self, x, a, b):
        y = a * x + b
        return y

    def curve_fit(self, x, y):
        super(LinearFit, self).curve_fit(x, y)
        self.result = self.func(x,
                self.popt[0], self.popt[1])
        return self.result

if __name__ == "__main__":
    gFit = GaussianFit()
    x=np.linspace(0, 10, 100)
    y = gFit.func(x, 1, 5, 2)
    yn = y + 0.2 * np.random.normal(size=len(x))
    result = gFit.curve_fit(x, yn)
    gFit.plot()

    lFit = LinearFit()
    y = lFit.func(x, 1, 5)
    yn = y + 0.2 * np.random.normal(size=len(x))
    result = lFit.curve_fit(x, yn)
    lFit.plot()


