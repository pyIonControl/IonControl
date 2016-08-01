# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from functools import partial

from PyQt5 import QtWidgets, QtCore


class StashButtonControl(QtCore.QObject):
    resume = QtCore.pyqtSignal(object)

    def __init__(self, button):
        super(StashButtonControl, self).__init__()
        self.button = button
        self.myMenu = QtWidgets.QMenu()
        button.setMenu(self.myMenu)
        self.currentActions = dict()  # Stash.key -> action
        self.indexLookup = dict()  # Stash.key -> index

    def onStashChanged(self, stash):
        self.indexLookup = dict(((s.key, index) for index, s in enumerate(stash)))
        newset = set(self.indexLookup.keys())
        oldset = set(self.currentActions.keys())
        deletedkeys = oldset - newset
        for key in deletedkeys:
            self.myMenu.removeAction(self.currentActions.pop(key))
        newkeys = newset - oldset
        for key in newkeys:
            action = QtWidgets.QAction(str(stash[self.indexLookup[key]]), self.myMenu)
            action.triggered.connect(partial(self.onTrigger, key))
            self.currentActions[key] = action
            self.myMenu.addAction(action)

    def onTrigger(self, key):
        self.resume.emit(self.indexLookup[key])
