from logging import LogRecord
from typing import Optional, List, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from tinyioc import get_service

from ..logger import logger
from ..messaging.message import TaskStatusMessage
from ..palette.base import BaseColorPalette
from .task_panel import TaskPanel


class TasksPane(QWidget):
    _layout: QVBoxLayout
    _central_widget: QSplitter
    _tasks: List[str]
    _total_columns: int
    _task_widgets: Dict[str, TaskPanel]
    _splitters: List[QSplitter]

    def __init__(self, parent: Optional[QWidget], tasks: List[str], columns: int = 3):
        super(TasksPane, self).__init__(parent)

        palette: BaseColorPalette = get_service(BaseColorPalette)

        self._tasks = tasks
        self._total_columns = columns
        self._task_widgets = {}
        self._splitters = []

        self._central_widget = QSplitter(Qt.Orientation.Vertical, self)
        self._central_widget.setStyleSheet(f"""
            background-color: {palette.background};
        """)

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)
        self.setContentsMargins(4, 4, 4, 4)

        self._layout.addWidget(self._central_widget)

        col = 0
        for task in self._tasks:
            if col % self._total_columns == 0:
                last_splitter = QSplitter(Qt.Orientation.Horizontal, self._central_widget)
                last_splitter.setStyleSheet(f"""
                    background-color: {palette.background};
                """)
                self._central_widget.addWidget(last_splitter)
                self._splitters.append(last_splitter)

            task_panel = TaskPanel(self._splitters[-1], task)
            self._splitters[-1].addWidget(task_panel)
            self._task_widgets[task] = task_panel

            col += 1

    # noinspection PyUnresolvedReferences
    def dispatch_log_record(self, record: LogRecord):
        if record.subprocess in self._task_widgets:
            self._task_widgets[record.subprocess].append_text(record)

    def dispatch_task_status(self, status: TaskStatusMessage):
        if status.task in self._task_widgets:
            self._task_widgets[status.task].update_status(status.status)
