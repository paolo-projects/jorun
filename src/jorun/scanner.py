import asyncio
import re
from asyncio.subprocess import Process
from typing import Callable

from .logger import subprocess_logger, subprocess_logger_err


class AsyncScanner:
    _read_timeout = 1
    _process: Process
    _completion_callback: Callable
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

    async def print_and_scan(self, pattern: str):
        if self._stderr_print:
            return await asyncio.gather(self._print_and_scan_stdout(pattern), self._print_stderr())
        else:
            return await self._print_and_scan_stdout(pattern)

    async def print(self):
        if self._stderr_print:
            return await asyncio.gather(self._print_stdout(), self._print_stderr())
        else:
            return await self._print_stdout()

    async def _print_and_scan_stdout(self, pattern: str):
        reg = re.compile(pattern)

        while self._process.returncode is None:
            line = await self._readline(self._process.stdout, self._read_timeout)

            if line is not None:
                if reg.match(line):
                    self._completion_callback()
                    return await self._print_stdout()

    async def _print_stdout(self):
        while self._process.returncode is None:
            line = await self._readline(self._process.stdout, self._read_timeout)

            if line is not None:
                subprocess_logger.info(line)

    async def _print_stderr(self):
        while self._process.returncode is None:
            line = await self._readline(self._process.stderr, self._read_timeout)

            if line is not None:
                subprocess_logger_err.info(line)
