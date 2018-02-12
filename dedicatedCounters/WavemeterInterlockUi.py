import os
from PyQt5 import QtWidgets

import PyQt5

from dedicatedCounters.WavemeterInterlock import Interlock, InterlockChannel
from dedicatedCounters.WavemeterInterlockTableModel import WavemeterInterlockTableModel
from modules.Utility import unique
from modules.quantity import Q
from uiModules.ComboBoxDelegate import ComboBoxDelegate
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from uiModules.MultiSelectDelegate import MultiSelectDelegate

uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/WavemeterUi.ui')
Form, Base = PyQt5.uic.loadUiType(uipath)


class WavemeterInterlockUi(Form, Base):
    def __init__(self, wavemeterNames, channels, contexts=set(), parent=None):
        Base.__init__(self, parent)
        Form.__init__(self)
        self.wavemeterNames = wavemeterNames
        self.channels = channels
        self.contexts = contexts

    def setupUi(self, parent):
        Form.setupUi(self, parent)
        self.tableModel = WavemeterInterlockTableModel(self.channels,self.wavemeterNames, self.contexts)
        # self.tableModel.edited.connect(self.autoSave)
        self.delegate = MagnitudeSpinBoxDelegate()
        self.tableView.setItemDelegateForColumn(5, self.delegate)
        self.tableView.setItemDelegateForColumn(4, self.delegate)
        self.tableView.setModel(self.tableModel)
        self.tableView.resizeColumnsToContents()
        self.tableView.setSortingEnabled(True)
        self.addButton.clicked.connect(self.tableModel.addChannel)
        self.removeButton.clicked.connect(self.onRemoveChannel)
        self.comboBoxDelegate = ComboBoxDelegate()
        self.tableView.setItemDelegateForColumn(1, self.comboBoxDelegate)
        self.multiSelectDelegate = MultiSelectDelegate()
        self.tableView.setItemDelegateForColumn(7, self.multiSelectDelegate)

    def onRemoveChannel(self):
        for index in sorted(unique([i.row() for i in self.tableView.selectedIndexes()]), reverse=True):
            self.tableModel.removeChannel(index)



if __name__ == "__main__":
    def onLoad(context, status):
        print(context, status)


    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    wavemeters = {'1236': "http://S973587:8082"}
    config = {"InterlockChannels": [InterlockChannel(wavemeter='1236', channel=4, minimum=Q(751527, 'GHz'), maximum=Q(751528, 'GHz'), useServerInterlock=False, contextSet=set(['load', 'exp']))]}
    il = Interlock(wavemeters=wavemeters, config=config)
    il.subscribe(onLoad, "load")
    ui = WavemeterInterlockUi(wavemeterNames=list(wavemeters.keys()), channels=il.channels, contexts=il.contexts)
    ui.setupUi(ui)
    ui.show()
    sys.exit(app.exec_())
