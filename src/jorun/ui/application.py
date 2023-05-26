import sys
import time
from queue import Queue, Empty
from threading import Thread
from typing import List, Callable, Optional, Dict

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from ..logger import logger
from ..types.task import PaneConfiguration


class UiApplication:
    _app: QApplication
    _window: Optional[MainWindow]
    _config: Optional[Dict[str, PaneConfiguration]]

    _task_list: List[str]
    _streams_queue: Queue
    _close_handler: Callable

    _stream_dequeue_thread: Thread
    _stream_dequeue_running: bool

    _trigger_close_handler: bool

    def __init__(self, tasks: List[str], task_streams_queue: Queue,
                 config: Optional[Dict[str, PaneConfiguration]]):
        self._window = None
        self._trigger_close_handler = True
        self._config = config
        self._task_list = tasks
        self._streams_queue = task_streams_queue

    def _app_quitting(self):
        self._stream_dequeue_running = False
        self._stream_dequeue_thread.join()

    def start_ui(self):
        self._stream_dequeue_running = True
        self._stream_dequeue_thread = Thread(target=self._dequeue_stream)
        self._stream_dequeue_thread.start()

        self._run_ui_thread()

    def _dequeue_stream(self):
        while self._stream_dequeue_running:
            if self._window:
                try:
                    stream_record = self._streams_queue.get(block=True, timeout=0.5)
                    self._window.dispatch_stream_record(stream_record)
                except Empty:
                    pass
            else:
                time.sleep(.1)

    def _run_ui_thread(self):
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(True)

        self._window = MainWindow(self._task_list, gui_config=self._config)
        self._window.show()

        self._app.exec()
        self._running = False
        self._app_quitting()

    def stop_ui(self):
        if self._stream_dequeue_running:
            self._stream_dequeue_running = False
            self._stream_dequeue_thread.join()
