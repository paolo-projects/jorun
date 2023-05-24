from logging import LogRecord
from typing import Optional

from PyQt6.QtWidgets import QGroupBox, QPlainTextEdit, QVBoxLayout, QSizePolicy, QHBoxLayout, QWidget, \
    QLabel
from tinyioc import inject

from .data_signals import DataUpdateSignalEmitter
from ..palette.base import BaseColorPalette


class TaskPanel(QGroupBox):
    SCROLL_TOLERANCE = 15

    _layout: QVBoxLayout
    _actions_group_widget: QWidget
    _actions_group_layout: QHBoxLayout
    _output_stream_text: QPlainTextEdit

    _task_name: str
    _task_label: QLabel

    @inject()
    def __init__(self, parent: Optional[QWidget], task_name: str, signal_emitter: DataUpdateSignalEmitter,
                 palette: BaseColorPalette):
        super(TaskPanel, self).__init__(parent)

        signal_emitter.signals.data_received.connect(self.append_text)

        self._task_name = task_name

        self._layout = QVBoxLayout(self)
        self.setLayout(self._layout)

        self.setStyleSheet(f"""
            background-color: {palette.current_line};
        """)

        self._actions_group_widget = QWidget(self)
        self._actions_group_layout = QHBoxLayout(self)
        self._actions_group_widget.setLayout(self._actions_group_layout)

        self._layout.addWidget(self._actions_group_widget)

        self._task_label = QLabel(self)
        self._task_label.setText(self._task_name)
        self._task_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._task_label.setStyleSheet(f"""
            color: {palette.foreground};
        """)
        self._actions_group_layout.addWidget(self._task_label)

        self._output_stream_text = QPlainTextEdit(self)
        self._output_stream_text.setReadOnly(True)
        self._output_stream_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._output_stream_text.setStyleSheet(f"""
            background-color: {palette.background}; 
            color: {palette.foreground}; 
            font-family: monospace;
        """)
        self._layout.addWidget(self._output_stream_text, 1)

    # noinspection PyUnresolvedReferences
    def append_text(self, record: LogRecord):
        if record.subprocess == self._task_name:
            scroll_bottom = False

            if self._output_stream_text.verticalScrollBar().value() > \
                    self._output_stream_text.verticalScrollBar().maximum() - self.SCROLL_TOLERANCE:
                scroll_bottom = True

            self._output_stream_text.insertPlainText(record.message)

            if scroll_bottom:
                self._output_stream_text.verticalScrollBar().setValue(
                    self._output_stream_text.verticalScrollBar().maximum())
