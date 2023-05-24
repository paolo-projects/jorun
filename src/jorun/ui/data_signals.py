from PyQt6.QtCore import QObject, pyqtSignal


class MainWindowSignals(QObject):
    data_received = pyqtSignal(object)
    app_terminated = pyqtSignal()


class DataUpdateSignalEmitter:
    signals: MainWindowSignals
