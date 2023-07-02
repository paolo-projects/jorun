import re
from logging import LogRecord
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget, QPlainTextEdit, QLabel, QLineEdit, QSizePolicy, \
    QPushButton, QHBoxLayout, QStyle
from tinyioc import get_service

from .command_handler import TaskCommandHandler
from .utils import icon_from_standard_pixmap
from ..logger import logger
from ..messaging.message import TaskStatus, TaskCommand
from ..palette.base import BaseColorPalette

from .. import constants


class TaskPanel(QGroupBox):
    _layout: QVBoxLayout
    _actions_group_widget: QWidget
    _actions_group_layout: QVBoxLayout
    _task_header_layout: QHBoxLayout
    _task_header_widget: QWidget
    _output_stream_edit_text: QPlainTextEdit

    _output_stream: str

    _task_name: str
    _task_label: QLabel
    _task_command_btn: QPushButton

    _filter_edit_text: QLineEdit

    _current_status: TaskStatus

    def __init__(self, parent: Optional[QWidget], task_name: str):
        super(TaskPanel, self).__init__(parent)

        palette: BaseColorPalette = get_service(BaseColorPalette)

        self._task_name = task_name
        self._output_stream = ""
        self._current_status = TaskStatus.STOPPED

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)

        self.setStyleSheet(f"""
            background-color: {palette.current_line};
            border: 0;
        """)

        self._actions_group_widget = QWidget(self)
        self._actions_group_layout = QVBoxLayout(self)
        self._actions_group_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_group_widget.setLayout(self._actions_group_layout)

        self._layout.addWidget(self._actions_group_widget)

        self._task_header_widget = QWidget(self)
        self._actions_group_layout.addWidget(self._task_header_widget)
        self._task_header_layout = QHBoxLayout(self._task_header_widget)
        self._task_header_layout.setContentsMargins(0, 0, 0, 0)

        self._task_label = QLabel(self._task_header_widget)
        self._task_label.setText(self._task_name)
        self._task_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._task_label.setStyleSheet(f"""
            color: {palette.foreground};
            font-weight: bold;
        """)
        self._task_header_layout.addWidget(self._task_label)

        self._task_command_btn = QPushButton(self._task_header_widget)

        self._task_command_btn.setIcon(
            icon_from_standard_pixmap(self.style(), QStyle.StandardPixmap.SP_MediaPlay, palette.foreground))
        self._task_command_btn.setStyleSheet(f"""
            color: {palette.foreground};
            background-color: {palette.background};
            cursor: pointer;
        """)
        self._task_command_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._task_command_btn.setFixedSize(24, 24)
        self._task_command_btn.clicked.connect(self.task_state_command_click)
        self._task_header_layout.addWidget(self._task_command_btn)

        self._filter_edit_text = QLineEdit(self)
        self._filter_edit_text.setPlaceholderText("Filter")
        self._filter_edit_text.setStyleSheet(f"""
            background-color: {palette.background};
            color: {palette.foreground};
        """)
        self._filter_edit_text.textChanged.connect(self._filter_changed)
        self._actions_group_layout.addWidget(self._filter_edit_text)

        self._output_stream_edit_text = QPlainTextEdit(self)
        self._output_stream_edit_text.setReadOnly(True)
        self._output_stream_edit_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._output_stream_edit_text.setStyleSheet(f"""
            background-color: {palette.background}; 
            color: {palette.foreground}; 
            font-family: monospace;
        """)
        self._layout.addWidget(self._output_stream_edit_text, 1)

    # noinspection PyUnresolvedReferences
    def append_text(self, record: LogRecord):
        scroll_bottom = False
        previous_scrollbar_pos = self._output_stream_edit_text.verticalScrollBar().value()

        if self._output_stream_edit_text.verticalScrollBar().value() > \
                self._output_stream_edit_text.verticalScrollBar().maximum() - constants.SCROLL_TOLERANCE:
            scroll_bottom = True

        processed_message = re.sub(r'\x1b\[([0-9,A-Z]{1,2}(;[0-9]{1,2})?(;[0-9]{3})?)?[m|K]?', '', record.message)
        self._output_stream += processed_message
        self._update_output_edit_text()

        if scroll_bottom:
            self._output_stream_edit_text.verticalScrollBar().setValue(
                self._output_stream_edit_text.verticalScrollBar().maximum())
        else:
            self._output_stream_edit_text.verticalScrollBar().setValue(
                min(self._output_stream_edit_text.verticalScrollBar().maximum(),
                    max(self._output_stream_edit_text.verticalScrollBar().minimum(), previous_scrollbar_pos)))

    @Slot()
    def task_state_command_click(self):
        command_handler: TaskCommandHandler = get_service(TaskCommandHandler)
        command = TaskCommand.STOP
        if self._current_status == TaskStatus.STOPPED:
            command = TaskCommand.START

        command_handler.dispatch(self._task_name, command)

    def update_status(self, status: TaskStatus):
        logger.debug(f"task_panel.update_status: Update status for task {self._task_name}: {status}")
        palette: BaseColorPalette = get_service(BaseColorPalette)

        if status == TaskStatus.STOPPED:
            self._task_command_btn.setIcon(
                icon_from_standard_pixmap(self.style(), QStyle.StandardPixmap.SP_MediaPlay, palette.foreground))
        elif status == TaskStatus.STARTED:
            self._task_command_btn.setIcon(
                icon_from_standard_pixmap(self.style(), QStyle.StandardPixmap.SP_MediaStop, palette.foreground))

        self._task_command_btn.update()
        self._current_status = status

    def _update_output_edit_text(self):
        filter_input = self._filter_edit_text.text()

        if filter_input:
            filtered_text = ""
            for line in self._output_stream.splitlines(keepends=True):
                if filter_input in line:
                    filtered_text += line
        else:
            filtered_text = self._output_stream

        self._output_stream_edit_text.setPlainText(filtered_text)

    @Slot()
    def _filter_changed(self):
        self._update_output_edit_text()
