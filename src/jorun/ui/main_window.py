from logging import LogRecord
from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QSplitter

from tinyioc import inject

from .data_signals import DataUpdateSignalEmitter, MainWindowSignals
from .task_panel import TaskPanel
from .. import constants
from ..palette.base import BaseColorPalette


class MainWindow(QMainWindow, DataUpdateSignalEmitter):
    _central_widget: QSplitter
    _tasks: List[str]
    _total_columns: int
    _task_widgets: Dict[str, TaskPanel]
    _splitters: List[QSplitter]

    signals = MainWindowSignals()

    @inject()
    def __init__(self, tasks: List[str], palette: BaseColorPalette, total_columns=3):
        super(MainWindow, self).__init__()

        self._tasks = tasks
        self._total_columns = total_columns
        self._task_widgets = {}
        self._splitters = []

        self.setStyleSheet(f"""
            background-color: {palette.background};
        """)
        self.setMinimumSize(300, 300)

        self.setWindowTitle(constants.APP_NAME)

        self._central_widget = QSplitter(Qt.Orientation.Vertical, self)
        self._central_widget.setStyleSheet(f"""
            background-color: {palette.background};
        """)
        self.setCentralWidget(self._central_widget)

        col = 0
        for task in self._tasks:
            if col % self._total_columns == 0:
                last_splitter = QSplitter(Qt.Orientation.Horizontal, self._central_widget)
                last_splitter.setStyleSheet(f"""
                    background-color: {palette.background};
                """)
                self._central_widget.addWidget(last_splitter)
                self._splitters.append(last_splitter)

            task_panel = TaskPanel(self._splitters[-1], task, self)
            self._splitters[-1].addWidget(task_panel)
            self._task_widgets[task] = task_panel

            col += 1

    # noinspection PyUnresolvedReferences
    def dispatch_stream_record(self, record: LogRecord):
        self.signals.data_received.emit(record)
