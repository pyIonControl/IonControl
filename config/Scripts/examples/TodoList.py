#TodoList.py created 2015-08-06 13:03:52.233000
#
#Reimplementation of todo list
#This script duplicates the functionality of the to do list.
#It runs 'scan1' with evaluation 'ev1,' analysis 'an1,' and 'myGlobal' set to 1 us.
#then it proceeds with 'scan2', 'ev2', etc.

scan = ['myScan1', 'myScan2', 'myScan3']
evaluation = ['myEval1', 'myEval2', 'myEval3']
analysis = ['myAnalysis1', 'myAnalysis2', 'myAnalysis3']
myGlobalVal = [1, 2, 3]

for i in range(len(scan)):
    setGlobal('myGlobal', myGlobalVal[i], 'us')
    setScan( scan[i] )
    setEvaluation( evaluation[i] )
    setAnalysis( analysis[i] )
    startScan()