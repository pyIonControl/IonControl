# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import functools
import inspect
import logging
import os
import sys
import weakref
from datetime import datetime

import PyQt5.uic
from PyQt5 import QtGui, QtWidgets

from modules.firstNotNone import firstNotNone

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/ExceptionMessage.ui')
ExceptionMessageForm, ExceptionMessageBase = PyQt5.uic.loadUiType(uipath)


class ExceptionMessage(ExceptionMessageForm, ExceptionMessageBase):
    def __init__(self, message, parent=None, showTime=True):
        ExceptionMessageForm.__init__(self)
        ExceptionMessageBase.__init__(self)
        self.message = str(message)
        self.count = 1
        self.time = datetime.now()
        self.showTime = showTime

    def messageText(self):
        text = ""
        if self.message:
            if self.count == 1:
                if self.time is not None and self.showTime:
                    text = "{0} {1}".format(self.time.strftime('%H:%M:%S'), self.message)
                else:
                    text = self.message
            else:
                if self.time is not None and self.showTime:
                    text = "({0}) {1} {2}".format(self.count, self.time.strftime('%H:%M:%S'), self.message)
                else:
                    text = "({0}) {1}".format(self.count, self.message)
        return text

    def setupUi(self, parent):
        ExceptionMessageForm.setupUi(self, parent)
        self.messageLabel.setText(self.messageText())

    def increaseCount(self):
        self.count += 1
        self.time = datetime.now()
        self.messageLabel.setText(self.messageText())


GlobalExceptionLogButtonSlot = None


class LogButton(QtWidgets.QToolButton):
    def __init__(self, parent=None, noMessageIcon=None, messageIcon=None, maxMessages=None, messageName=None):
        QtWidgets.QToolButton.__init__(self, parent)
        self.myMenu = QtWidgets.QMenu(self)
        self.setMenu(self.myMenu)
        self.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.exceptionsListed = 0
        self.NoExceptionsIcon = QtGui.QIcon(firstNotNone(noMessageIcon, ":/petersIcons/icons/Success-01.png"))
        self.ExceptionsIcon = QtGui.QIcon(firstNotNone(messageIcon, ":/petersIcons/icons/Error-01.png"))
        self.setIcon(self.NoExceptionsIcon)
        self.menuItemDict = dict()
        self.maxMessages = maxMessages
        self.clearAllMessage = "Clear All {0}".format(firstNotNone(messageName, "exceptions"))

    def removeAll(self):
        self.menuItemDict.clear()
        for action in self.myMenu.actions():
            self.myMenu.removeAction(action)
        self.setIcon(self.NoExceptionsIcon)
        self.exceptionsListed = 0

    def addClearAllAction(self):
        myMenuItem = ExceptionMessage(self.clearAllMessage, self.myMenu, showTime=False)
        myMenuItem.setupUi(myMenuItem)
        action = QtWidgets.QWidgetAction(self.myMenu)
        action.setDefaultWidget(myMenuItem)
        self.myMenu.addAction(action)
        myMenuItem.deleteButton.clicked.connect(self.removeAll)

    def addMessage(self, message):
        message = str(message)  # convert to string
        oldMenuItem = self.menuItemDict.get(message)
        if oldMenuItem is not None:
            oldMenuItem.increaseCount()
        else:
            myMenuItem = ExceptionMessage(message, self.myMenu)
            myMenuItem.setupUi(myMenuItem)
            action = QtWidgets.QWidgetAction(self.myMenu)
            action.setDefaultWidget(myMenuItem)
            myMenuItem.deleteButton.clicked.connect(functools.partial(self.removeMessage, weakref.ref(action)))
            self.menuItemDict[message] = myMenuItem
            if self.exceptionsListed == 0:
                self.setIcon(self.ExceptionsIcon)
                self.addClearAllAction()
            self.exceptionsListed += 1
            self.myMenu.addAction(action)

    def removeMessage(self, action):
        self.menuItemDict.pop(action().defaultWidget().message)
        self.myMenu.removeAction(action())
        self.exceptionsListed -= 1
        if self.exceptionsListed == 0:
            self.removeAll()


class ExceptionLogButton(LogButton):
    def __init__(self, parent=None):
        super(ExceptionLogButton, self).__init__(parent)
        sys.excepthook = self.myexcepthook
        global GlobalExceptionLogButtonSlot
        GlobalExceptionLogButtonSlot = self.excepthookSlot

    def excepthookSlot(self, exceptinfo):
        self.myexcepthook(*exceptinfo)

    def myexcepthook(self, excepttype, value, tback):
        logger = logging.getLogger(inspect.getmodule(tback.tb_frame).__name__ if tback is not None else "unknown")
        self.addMessage(value)
        logger.error(str(value), exc_info=(excepttype, value, tback))
        # sys.__excepthook__(excepttype, value, tback)
