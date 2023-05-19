import asyncio
import time
from asyncio.subprocess import Process
from typing import Optional, Callable, List

from .handler.base import BaseTaskHandler
from .scanner import AsyncScanner
from .task import TaskNode, TaskOptions

OUTPUT_READ_INTERVAL = 0.015


class TaskRunner:
    _handlers: List[BaseTaskHandler]
    _handler: BaseTaskHandler

    _task: TaskNode
    _process: Optional[Process]
    _completion_callback: Optional[Callable]
    _scanner: AsyncScanner

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

    def stop(self):
        if self._process and self._process.returncode is None:
            self._on_stop()
            self._process.terminate()

    async def start(self, completion_callback: Callable):
        try:
            self._completion_callback = completion_callback
            t = self._task.task

            stderr_redirect = t.get('pattern_in_stderr', False)

            task_options: Optional[TaskOptions] = t.get(self._handler.task_type)

            self._process = await self._handler.execute(task_options, self._completion_callback,
                                                        stderr_redirect)
            if not self._process:
                self._running = False
                return

            run_mode = t.get("run_mode") or "await_completion"
            completion_pattern = t.get("completion_pattern")
            self._scanner = AsyncScanner(self._process, self._completion_callback, not stderr_redirect)

            if run_mode == "await_completion" and completion_pattern:
                await self._scanner.print_and_scan(completion_pattern, self._task.task['name'])
            else:
                await self._scanner.print(self._task.task['name'])
        except asyncio.CancelledError:
            pass
