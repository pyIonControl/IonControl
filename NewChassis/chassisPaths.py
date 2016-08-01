# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from sys import path

class chassisPaths(object):
    def __init__(self):
        pass

    @staticmethod
    def addPaths():
        myPaths = ['C:\\Workspace\\Chassis.git',
                'C:\\Workspace\\Chassis.git\\tests',
                'C:\\Workspace\\Chassis.git\\examples']
        for myPath in myPaths:
            for pyPath in path:
                exists = False
                print(pyPath, myPath)
                if pyPath == myPath:
                    exists = True
                    break

            if not exists:
                path.insert(1, myPath)

