from PyQt6.QtCore import QObject, pyqtSignal


class MainWindowSignals(QObject):
    data_received = pyqtSignal(object)


class DataUpdateSignalEmitter:
    signals: MainWindowSignals
