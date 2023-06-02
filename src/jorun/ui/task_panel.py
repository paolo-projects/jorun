import re
from logging import LogRecord
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget, QPlainTextEdit, QLabel, QLineEdit, QSizePolicy
from tinyioc import inject

from ..palette.base import BaseColorPalette

from .. import constants


class TaskPanel(QGroupBox):
    _layout: QVBoxLayout
    _actions_group_widget: QWidget
    _actions_group_layout: QVBoxLayout
    _output_stream_edit_text: QPlainTextEdit

    _output_stream: str

    _task_name: str
    _task_label: QLabel

    _filter_edit_text: QLineEdit
    _escape_pattern: re.Pattern

    @inject()
    def __init__(self, parent: Optional[QWidget], task_name: str, palette: BaseColorPalette):
        super(TaskPanel, self).__init__(parent)

        self._escape_pattern = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        self._task_name = task_name
        self._output_stream = ""

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

        self._task_label = QLabel(self)
        self._task_label.setText(self._task_name)
        self._task_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._task_label.setMaximumWidth(80)
        self._task_label.setStyleSheet(f"""
            color: {palette.foreground};
            font-weight: bold;
        """)
        self._actions_group_layout.addWidget(self._task_label)

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
        previous_scroll = self._output_stream_edit_text.verticalScrollBar().value()

        if self._output_stream_edit_text.verticalScrollBar().value() > \
                self._output_stream_edit_text.verticalScrollBar().maximum() - constants.SCROLL_TOLERANCE:
            scroll_bottom = True

        message = self._escape_pattern.sub('', record.message)

        self._output_stream += message
        self._update_output_edit_text()

        if scroll_bottom:
            self._output_stream_edit_text.verticalScrollBar().setValue(
                self._output_stream_edit_text.verticalScrollBar().maximum())
        else:
            self._output_stream_edit_text.verticalScrollBar().setValue(
                min(max(previous_scroll, self._output_stream_edit_text.verticalScrollBar().maximum()),
                    self._output_stream_edit_text.verticalScrollBar().minimum())
            )

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
