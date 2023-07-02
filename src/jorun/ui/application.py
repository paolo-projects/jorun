import sys
import time
from multiprocessing.connection import Connection
from queue import Queue, Empty
from threading import Thread
from typing import List, Callable, Optional, Dict

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from ..logger import logger
from ..messaging.message import TaskStatusMessage
from ..types.task import PaneConfiguration


class UiApplication:
    _app: QApplication
    _window: Optional[MainWindow]
    _config: Optional[Dict[str, PaneConfiguration]]

    _task_list: List[str]
    # Input
    _streams_queue: Queue
    # Input
    _task_status_queue: Queue
    # Output
    _task_commands_queue: Queue
    _close_handler: Callable

    _stream_dequeue_thread: Thread
    _task_status_dequeue_thread: Thread
    _dequeue_running: bool

    _trigger_close_handler: bool
    _termination_pipe: Connection

    _termination_listener_trd: Thread

    def __init__(self, tasks: List[str], task_streams_queue: Queue, task_status_queue: Queue,
                 task_commands_queue: Queue, config: Optional[Dict[str, PaneConfiguration]],
                 termination_pipe: Connection):
        self._window = None
        self._trigger_close_handler = True
        self._config = config
        self._task_list = tasks
        self._streams_queue = task_streams_queue
        self._task_status_queue = task_status_queue
        self._task_commands_queue = task_commands_queue
        self._termination_pipe = termination_pipe
        self._termination_listener_running = True

    def _app_quitting(self):
        self._dequeue_running = False
        self._stream_dequeue_thread.join()

    def _termination_listen(self):
        logger.debug("Started termination listener to watch for runner process termination")
        try:
            self._termination_pipe.recv()
            logger.info("App terminated from runner process")
            self._window.signals.app_terminated.emit()
        except EOFError:
            pass

    def start_ui(self):
        self._dequeue_running = True

        self._stream_dequeue_thread = Thread(target=self._dequeue_stream)
        self._stream_dequeue_thread.start()

        self._task_status_dequeue_thread = Thread(target=self._dequeue_task_statuses)
        self._task_status_dequeue_thread.start()

        self._termination_listener_trd = Thread(target=self._termination_listen)
        self._termination_listener_trd.start()

        self._run_ui_thread()

    def _dequeue_task_statuses(self):
        while self._dequeue_running:
            if self._window:
                try:
                    status: TaskStatusMessage = self._task_status_queue.get(block=True, timeout=0.5)
                    logger.debug(f"Task status dequeued: {status}")
                    self._window.dispatch_task_status(status)
                except Empty:
                    pass
            else:
                time.sleep(.1)

    def _dequeue_stream(self):
        while self._dequeue_running:
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
        if self._dequeue_running:
            self._dequeue_running = False
            self._stream_dequeue_thread.join()

        self._app.quit()
