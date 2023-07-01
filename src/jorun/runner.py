import asyncio
import logging
import os.path
import platform
import signal
import time
from asyncio.subprocess import Process
from datetime import datetime
from logging import Logger
from typing import Optional, Callable, List, Union

import psutil
from tinyioc import get_service

from . import constants
from .handler.base import BaseTaskHandler
from .logger import logger
from .scanner import AsyncScanner
from .types.options import TaskOptions
from .types.task import Task
from .configuration import AppConfiguration


class TaskRunner:
    _handlers: List[BaseTaskHandler]
    _handler: BaseTaskHandler

    _task: Task
    _process: Optional[Process]
    _completion_callback: Optional[Callable]
    _scanner: AsyncScanner
    _log_handler: logging.Handler

    _logger: Logger
    _err_logger: Logger

    def __init__(self, task: Task, file_output_dir: Optional[str], log_level: Union[int, str],
                 log_handler: logging.Handler):
        configuration: AppConfiguration = get_service(AppConfiguration)

        self._task = task
        self._handlers = configuration.handlers
        self._process = None
        self._running = True
        self._completion_callback = None
        self._log_handler = log_handler

        self._handler = next(h for h in self._handlers if h.task_type == task['type'])

        if not self._handler:
            raise RuntimeError(f"Task type '{task['type']}' unrecognized")

        self._logger = logging.Logger(task["name"])
        self._logger.setLevel(log_level)
        self._err_logger = logging.Logger(task["name"])
        self._err_logger.setLevel(log_level)

        self._logger.addHandler(log_handler)
        self._err_logger.addHandler(log_handler)

        if file_output_dir and os.path.isdir(file_output_dir):
            now_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            output_file = os.path.join(file_output_dir, f"{task['name']}_{now_time}.log")
            file_handler = logging.FileHandler(output_file)
            file_handler.terminator = ''

            self._logger.addHandler(file_handler)
            self._err_logger.addHandler(file_handler)

    @property
    def name(self):
        return self._task["name"]

    def _on_stop(self):
        # noinspection PyTypedDict
        self._handler.on_exit(self._task[self._handler.task_type], self._process)

    def stop(self, timeout=1):
        if self._process and self._process.returncode is None:
            logger.debug(f"Process {self.name} is alive. Killing it")

            self._on_stop()
            pid = self._process.pid

            if platform.system() == "Windows":
                os.kill(pid, signal.CTRL_C_EVENT)
            else:
                os.kill(pid, signal.SIGTERM)

            init_time = time.time()
            while psutil.pid_exists(pid) and time.time() < init_time + timeout:
                time.sleep(constants.PROCESS_KILL_POLLING_INTERVAL)

            if psutil.pid_exists(pid):
                logger.debug(f"Process {self.name} still alive after {timeout}s timeout. Sending SIGKILL")
                if platform.system() == "Windows":
                    os.kill(pid, signal.CTRL_BREAK_EVENT)
                else:
                    os.kill(pid, signal.SIGKILL)

    async def start(self, completion_callback: Optional[Callable]):
        try:
            self._completion_callback = completion_callback
            t = self._task

            stderr_redirect = t.get('pattern_in_stderr', False)

            # noinspection PyTypedDict
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
