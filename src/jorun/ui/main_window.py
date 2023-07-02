from logging import LogRecord
from typing import Dict, List, Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMainWindow, QTabWidget
from tinyioc import get_service

from .data_signals import DataUpdateSignalEmitter, MainWindowSignals
from .pane import TasksPane
from .. import constants
from ..messaging.message import TaskStatusMessage
from ..palette.base import BaseColorPalette
from ..types.task import PaneConfiguration


class MainWindow(QMainWindow, DataUpdateSignalEmitter):
    _tab_widget: QTabWidget
    _panes: List[TasksPane]
    signals = MainWindowSignals()

    def __init__(self, tasks: List[str], gui_config: Optional[Dict[str, PaneConfiguration]]):
        super(MainWindow, self).__init__()

        palette: BaseColorPalette = get_service(BaseColorPalette)

        self.signals.app_terminated.connect(self.close)
        self._panes = []

        self.setStyleSheet(f"""
            background-color: {palette.background};
        """)
        self.setMinimumSize(300, 300)

        self.setWindowTitle(constants.APP_NAME)

        self._tab_widget = QTabWidget(self)
        self._tab_widget.setStyleSheet(f"""
            QTabWidget::pane
            {{
                background: {palette.selection};
            }}
            
            QTabBar::tab {{
                background: {palette.selection};
                color: {palette.foreground};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 6px;
                margin: 0 1px 0 1px;
            }}
            
            QTabBar::tab:selected {{
                font-weight: bold;
            }}
        """)

        self.setCentralWidget(self._tab_widget)

        tasks_bucket = set(tasks)

        if gui_config:
            for pane_name, pane_options in gui_config.items():
                pane = TasksPane(None, pane_options.get("tasks"), columns=pane_options.get("columns") or 3)
                pane.setAutoFillBackground(True)
                self._tab_widget.addTab(pane, pane_name)
                self._panes.append(pane)

                for t in pane_options["tasks"]:
                    tasks_bucket.discard(t)

        if len(tasks_bucket) > 0:
            extra_pane = TasksPane(None, list(tasks_bucket))
            extra_pane.setAutoFillBackground(True)
            self._tab_widget.addTab(extra_pane, "-")
            self._panes.append(extra_pane)

        self.signals.data_received.connect(self._handle_stream_record)
        self.signals.task_status_received.connect(self._handle_task_status)

    @Slot(LogRecord)
    def _handle_stream_record(self, record: LogRecord):
        for p in self._panes:
            p.dispatch_log_record(record)

    @Slot(TaskStatusMessage)
    def _handle_task_status(self, status: TaskStatusMessage):
        for p in self._panes:
            p.dispatch_task_status(status)

    # noinspection PyUnresolvedReferences
    def dispatch_stream_record(self, record: LogRecord):
        self.signals.data_received.emit(record)

    def dispatch_task_status(self, status: TaskStatusMessage):
        self.signals.task_status_received.emit(status)

    def dispatch_app_termination(self):
        self.signals.app_terminated.emit()
