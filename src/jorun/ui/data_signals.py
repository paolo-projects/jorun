from PySide6.QtCore import QObject, Signal


class MainWindowSignals(QObject):
    data_received = Signal(object)
    app_terminated = Signal()


class DataUpdateSignalEmitter:
    signals: MainWindowSignals
