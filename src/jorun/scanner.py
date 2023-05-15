import asyncio
import re
from asyncio.subprocess import Process
from typing import Callable, Optional

from .logger import subprocess_logger, subprocess_logger_err


class AsyncScanner:
    _read_timeout = 1
    _process: Process
    _completion_callback: Optional[Callable]
    _stderr_print: bool

    def __init__(self, process: Process, completion_callback: Callable, print_stderr: bool = False):
        self._process = process
        self._completion_callback = completion_callback
        self._stderr_print = print_stderr

    @staticmethod
    async def _readline(stream: asyncio.StreamReader, timeout: float):
        try:
            return await asyncio.wait_for(stream.readline(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def print_and_scan(self, pattern: str, task_name: str = "unknown"):
        if self._stderr_print:
            return await asyncio.gather(self._print_and_scan_stdout(pattern, task_name), self._print_stderr(task_name))
        else:
            return await self._print_and_scan_stdout(pattern, task_name)

    async def print(self, task_name: str = "unknown"):
        if self._stderr_print:
            return await asyncio.gather(self._print_stdout(task_name), self._print_stderr(task_name))
        else:
            return await self._print_stdout(task_name)

    async def _print_and_scan_stdout(self, pattern: str, task_name: str):
        reg = re.compile(pattern)

        while self._process.returncode is None:
            line_b = await self._readline(self._process.stdout, self._read_timeout)

            if line_b is not None:
                line = line_b.decode('utf-8')
                subprocess_logger.info(line, extra={'subprocess': task_name})
                if reg.match(line) and self._completion_callback:
                    self._completion_callback()
                    self._completion_callback = None
                    return await self._print_stdout(task_name)

    async def _print_stdout(self, task_name: str):
        while self._process.returncode is None:
            line_b = await self._readline(self._process.stdout, self._read_timeout)

            if line_b is not None:
                subprocess_logger.info(line_b.decode('utf-8'), extra={'subprocess': task_name})

        if self._completion_callback:
            self._completion_callback()
            self._completion_callback = None

    async def _print_stderr(self, task_name: str):
        while self._process.returncode is None:
            line_b = await self._readline(self._process.stderr, self._read_timeout)

            if line_b is not None:
                subprocess_logger_err.info(line_b.decode('utf-8'), extra={'subprocess': task_name})
