import time
from threading import Thread
import re
import subprocess
from typing import Optional, Callable, List

from .handler.base import BaseTaskHandler
from .logger import subprocess_logger, subprocess_logger_err
from .task import TaskNode

OUTPUT_READ_INTERVAL = 0.015


class TaskRunner:
    _handlers: List[BaseTaskHandler]
    _handler: BaseTaskHandler

    _task: TaskNode
    _process: Optional[subprocess.Popen]
    _thread: Thread
    _running: bool
    _completion_callback: Optional[Callable]

    def __init__(self, task: TaskNode, handlers: List[BaseTaskHandler]):
        self._task = task
        self._handlers = handlers
        self._process = None
        self._running = True
        self._completion_callback = None

        self._handler = next(h for h in self._handlers if h.task_type == task.task['type'])

        if not self._handler:
            raise RuntimeError(f"Task type '{task.task['type']}' unrecognized")

    def _on_stop(self):
        self._handler.on_exit(self._task.task[self._handler.task_type], self._process)

    def _stderr_reader(self):
        try:
            while self._running and self._process.poll() is None:
                line_err = self._process.stderr.readline().decode('utf-8')
                if line_err:
                    subprocess_logger_err.info(line_err, extra={"subprocess": self._task.task['name']})

                time.sleep(OUTPUT_READ_INTERVAL)

            pending_err = self._process.stderr.read().decode('utf-8')
            if pending_err:
                for line_err in pending_err.split("\n"):
                    if line_err:
                        subprocess_logger_err.info(line_err, extra={"subprocess": self._task.task['name']})
        except:
            pass

    def _await_pattern(self, pattern: str, print_stderr: bool):
        pattern = re.compile(pattern)

        try:
            while self._running and not self._process.stdout.closed:
                line = self._process.stdout.readline().decode('utf-8')
                if line:
                    subprocess_logger.info(line, extra={"subprocess": self._task.task['name']})

                line_stderr = self._process.stdout.readline().decode('utf-8')
                if line_stderr:
                    subprocess_logger_err.info(line_stderr, extra={"subprocess": self._task.task['name']})

                if pattern.match(line):
                    if self._completion_callback:
                        self._completion_callback()
                        self._completion_callback = None

                    self._await_completion(print_stderr)

                time.sleep(OUTPUT_READ_INTERVAL)
        except:
            pass

    def _await_completion(self, print_stderr: bool):
        try:
            while self._running and self._process.poll() is None:
                line = self._process.stdout.readline().decode('utf-8')
                if line:
                    subprocess_logger.info(line, extra={"subprocess": self._task.task['name']})

                if print_stderr:
                    line_err = self._process.stderr.readline().decode('utf-8')
                    if line_err:
                        subprocess_logger_err.info(line_err, extra={"subprocess": self._task.task['name']})

                time.sleep(OUTPUT_READ_INTERVAL)

            pending = self._process.stdout.read().decode('utf-8')
            if pending:
                for line in pending.split("\n"):
                    if line:
                        subprocess_logger.info(line, extra={"subprocess": self._task.task['name']})

            if print_stderr:
                pending_err = self._process.stderr.read().decode('utf-8')
                if pending_err:
                    for line_err in pending.split("\n"):
                        if line_err:
                            subprocess_logger_err.info(line_err, extra={"subprocess": self._task.task['name']})
        except:
            pass

        if self._completion_callback:
            self._completion_callback()
            self._completion_callback = None

        self._running = False

    def _print_output_stderr(self):
        try:
            while self._running and not self._process.stderr.closed:
                line = self._process.stderr.readline().decode('utf-8')
                if line:
                    subprocess_logger.error(line, extra={"subprocess": self._task.task['name']})
                time.sleep(OUTPUT_READ_INTERVAL)
        except:
            pass

    def stop(self):
        if self._process and self._process.poll() is None:
            self._on_stop()
            self._process.terminate()

        if self._running:
            self._running = False
            self._thread.join()

    def start(self, completion_callback: Callable):
        self._completion_callback = completion_callback
        self._thread = Thread(target=self._run)
        self._thread.start()

    def _run(self):
        t = self._task.task

        stderr_redirect = t.get('pattern_in_stderr', False)

        self._process = self._handler.execute(t[self._handler.task_type], self._completion_callback, stderr_redirect)
        if not self._process:
            self._running = False
            return

        run_mode = t.get("run_mode") or "await_completion"
        completion_pattern = t.get("completion_pattern")

        if run_mode == "await_completion" and completion_pattern:
            self._await_pattern(completion_pattern, not stderr_redirect)
        else:
            self._await_completion(not stderr_redirect)
