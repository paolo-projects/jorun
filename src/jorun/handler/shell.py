import os
import subprocess
import asyncio
from asyncio.subprocess import Process
from typing import Callable, Optional

from ..task import TaskOptions, ShellTask
from .base import BaseTaskHandler
from ..logger import logger


class ShellTaskHandler(BaseTaskHandler):
    @property
    def task_type(self) -> str:
        return "shell"

    async def execute(self, options: Optional[ShellTask], completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[Process]:
        stderr_file = subprocess.STDOUT if stderr_redirect else subprocess.PIPE

        out_cmd = options['command']
        if isinstance(out_cmd, list):
            out_cmd = " ".join(out_cmd)

        logger.debug(f"Running command: {out_cmd}")
        envs = options.get("environment")
        env_vars = None

        if envs:
            env_vars = dict(os.environ)
            env_vars.update({k: str(v) for k, v in envs.items()})

        if not isinstance(options["command"], list):
            process = await asyncio.create_subprocess_shell(
                options["command"],
                cwd=options.get("working_directory"),
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL)
        else:
            process = await asyncio.create_subprocess_exec(
                options["command"][0],
                *options["command"][1:],
                cwd=options.get("working_directory"),
                env=env_vars,
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL)

        return process

    def on_exit(self, options: TaskOptions, process: Process):
        pass
