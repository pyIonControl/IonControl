#usingClasses.py created 2015-08-11 16:27:38.143000
#
#This example is meant to show that scripts can use all of the complexity
#possible in any Python script, including classes, functions, etc.
#It also shows that the highlighting follows the script, wherever it is.
#To see this, run with slow on.

class myClass():
    def myfunc3(self):
        addGlobal('g6', 1125, 'MHz')
        addGlobal('g7', 1125, 'MHz')
    
    def myfunc2(self):
        addGlobal('g4', 2, 'V')
        addGlobal('g5', 2, 'V')
        self.myfunc3()

    def myfunc(self):
        setGlobal('g1', 3, 'Hz')
        setGlobal('g2', 3, 'Hz')
        self.myfunc2()

for i in range(10):
    setGlobal('g1', 3, 'ms')
    setGlobal('g2', 3, 'Hz')
    c = myClass()
    c.myfunc()
    setGlobal('g3', 15, "MHz")
