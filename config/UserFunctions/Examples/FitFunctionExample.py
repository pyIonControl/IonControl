#
#       Fit functions, available from the Fit tab or from Analysis Control can be defined within the User Functions
#       Editor. Fit functions must be decorated with @fitfunc and more complicated attributes, such as smart start
#       parameters or result fields, can be defined with subsequent functions.
#

import math

# For any use function, the first argument must be the dependent variable for the fit. The most basic implementation
# for a user defined fit function would work in the following way:

@fitfunc
def UserLine(x, m, b):
    return m*x + b

# For the above function, all parameters are enabled, parameter names mirror those of variable names, and the
# description string will match the return statement. A more advanced fit example is given below

@fitfunc(name='User Defined Quadratic',
         description='Amplitude*x^2 + Offset\nA basic quadratic function with no linear term',
         parameterNames=['Amplitude Coefficient', 'Offset'],
         units=['None', 'None'],
         enabledParameters=[True, False],
         parameterBounds=[[-10, 1000], [-100, 100]],
         overwriteDefaults=True)
def quad(x, a=10, o=0):
    return a*x**2+o

# The smart start function should have the following input variables
@quad.smartstart
def smartS(xdata, ydata, parameters, enabled):
    xin, yin = list(zip(*sorted(zip(xdata, ydata))))
    if xin[0] == 0 or xin[0]/xin[-1] < .1:
        offset = yin[0]
    else:
        offset = 0
    sqrtlist = []
    for ind in range(len(yin)):
        if xin[ind] != 0:
            coeffGuess = (math.sqrt(yin[ind])/xin[ind])**2
            sqrtlist.append(coeffGuess)
    return [sum(sqrtlist)/len(sqrtlist), offset]

@quad.result('sqrt','sqrt of |Amplitude|')
def res(g, b):
    return math.sqrt(abs(g))


