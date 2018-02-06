from PyQt5.QtCore import QCoreApplication

from dedicatedCounters.WavemeterInterlock import WavemeterPoll


def onData(data=None):
    print(data)

if __name__ == "__main__":
    app = QCoreApplication([])
    p = WavemeterPoll(name="1236", url="http://S973587:8082")
    p.subscribe(onData)
    app.exec()
