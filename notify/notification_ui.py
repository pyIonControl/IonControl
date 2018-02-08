import os
from PyQt5 import QtWidgets

import PyQt5
from PyQt5 import uic

from modules.Utility import unique
from notify.notification import NotificationCenter
from notify.notificationTableModel import NotificationTableModel
from uiModules.MultiSelectDelegate import MultiSelectDelegate

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/WavemeterUi.ui')
Form, Base = uic.loadUiType(uipath)


class NotificationUi(Form, Base):
    def __init__(self, notificationCenter, parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.notificationCenter = notificationCenter

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.tableModel = NotificationTableModel(self.notificationCenter)
        self.tableView.setModel(self.tableModel)
        self.tableView.resizeColumnsToContents()
        self.tableView.setSortingEnabled(True)
        self.addButton.clicked.connect(self.tableModel.addChannel)
        self.removeButton.clicked.connect(self.onRemoveChannel)
        self.multiSelectDelegate = MultiSelectDelegate()
        self.tableView.setItemDelegateForColumn(2, self.multiSelectDelegate)

    def onRemoveChannel(self):
        for index in sorted(unique([i.row() for i in self.tableView.selectedIndexes()]), reverse=True):
            self.tableModel.removeChannel(index)



if __name__ == "__main__":
    def onLoad(context, status):
        print(context, status)


    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    nc = NotificationCenter()
    ui = NotificationUi(nc)
    #nc.register("test")
    #nc.register("test2")
    ui.setupUi(ui)
    ui.show()
    sys.exit(app.exec_())
