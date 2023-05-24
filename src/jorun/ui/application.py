import sys
import time
from queue import Queue, Empty
from threading import Thread
from typing import List, Callable, Optional

from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow


class UiApplication:
    _ui_thread: Thread
    _running: bool

    _app: QApplication
    _window: Optional[MainWindow]

    _task_list: List[str]
    _streams_queue: Queue
    _close_handler: Callable

    _stream_dequeue_thread: Thread
    _stream_dequeue_running: bool

    def __init__(self, tasks: List[str], close_handler: Callable, task_streams_queue: Queue):
        self._window = None
        self._task_list = tasks
        self._close_handler = close_handler
        self._streams_queue = task_streams_queue

    def _app_quitting(self):
        self._stream_dequeue_running = False
        self._stream_dequeue_thread.join()

        self._close_handler()

    def start_ui(self):
        self._stream_dequeue_running = True
        self._stream_dequeue_thread = Thread(target=self._dequeue_stream)
        self._stream_dequeue_thread.start()

        self._running = True
        self._ui_thread = Thread(target=self._run_ui_thread)
        self._ui_thread.start()

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

        self._window = MainWindow(self._task_list)
        self._window.show()

        self._app.exec()
        self._running = False
        self._app_quitting()

    def stop_ui(self):
        if self._running:
            self._app.quit()
            self._ui_thread.join()
            self._running = False
