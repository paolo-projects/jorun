import asyncio
import logging
import os.path
import sys
from asyncio.subprocess import Process
from datetime import datetime
from logging import Logger
from typing import Optional, Callable, List, Union

from .handler.base import BaseTaskHandler
from .logger import NewlineStreamHandler
from .scanner import AsyncScanner
from .task import TaskOptions, Task

OUTPUT_READ_INTERVAL = 0.015


class TaskRunner:
    _handlers: List[BaseTaskHandler]
    _handler: BaseTaskHandler

    _task: Task
    _process: Optional[Process]
    _completion_callback: Optional[Callable]
    _scanner: AsyncScanner

    _logger: Logger
    _err_logger: Logger

    def __init__(self, task: Task, handlers: List[BaseTaskHandler], file_output_dir: Optional[str],
                 log_level: Union[int, str]):
        self._task = task
        self._handlers = handlers
        self._process = None
        self._running = True
        self._completion_callback = None

        self._handler = next(h for h in self._handlers if h.task_type == task['type'])

        if not self._handler:
            raise RuntimeError(f"Task type '{task['type']}' unrecognized")

        self._logger = logging.Logger(task["name"])
        self._logger.setLevel(log_level)
        self._err_logger = logging.Logger(task["name"])
        self._err_logger.setLevel(log_level)

        console_handler = NewlineStreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("[%(subprocess)s]: %(message)s"))

        self._logger.addHandler(console_handler)

        console_handler_err = NewlineStreamHandler(sys.stderr)
        console_handler.setFormatter(logging.Formatter("[%(subprocess)s]: %(message)s"))

        self._err_logger.addHandler(console_handler_err)

        if file_output_dir and os.path.isdir(file_output_dir):
            now_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            output_file = os.path.join(file_output_dir, f"{task['name']}_{now_time}.log")
            file_handler = logging.FileHandler(output_file)
            file_handler.terminator = ''

            self._logger.addHandler(file_handler)
            self._err_logger.addHandler(file_handler)

    def _on_stop(self):
        self._handler.on_exit(self._task[self._handler.task_type], self._process)

    def stop(self):
        if self._process and self._process.returncode is None:
            self._on_stop()
            self._process.terminate()

    async def start(self, completion_callback: Callable):
        try:
            self._completion_callback = completion_callback
            t = self._task

            stderr_redirect = t.get('pattern_in_stderr', False)

            task_options: Optional[TaskOptions] = t.get(self._handler.task_type)

            self._process = await self._handler.execute(task_options, self._completion_callback,
                                                        stderr_redirect)
            if not self._process:
                self._running = False
                return

            run_mode = t.get("run_mode") or "await_completion"
            completion_pattern = t.get("completion_pattern")
            self._scanner = AsyncScanner(self._logger, self._err_logger, self._process, self._completion_callback,
                                         not stderr_redirect)

            if run_mode == "await_completion" and completion_pattern:
                await self._scanner.print_and_scan(completion_pattern, self._task['name'])
            else:
                await self._scanner.print(self._task['name'])
        except asyncio.CancelledError:
            pass
