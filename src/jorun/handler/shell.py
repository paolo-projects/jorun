import subprocess
from typing import Callable, Optional

from ..task import TaskOptions, ShellTask
from .base import BaseTaskHandler
from ..logger import logger


class ShellTaskHandler(BaseTaskHandler):
    @property
    def task_type(self) -> str:
        return "shell"

    def execute(self, options: ShellTask, completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[subprocess.Popen]:
        stderr_file = subprocess.STDOUT if stderr_redirect else subprocess.PIPE

        out_cmd = options['command']
        if isinstance(out_cmd, list):
            out_cmd = " ".join(out_cmd)

        logger.debug(f"Running command: {out_cmd}")
        envs = options.get("environment")
        env_vars = {k: str(v) for k, v in envs.items()} if envs else None

        process = subprocess.Popen(
            options["command"],
            cwd=options.get("working_directory"),
            env=env_vars,
            shell=(not isinstance(options["command"], list)),
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            stdin=subprocess.DEVNULL)

        return process

    def on_exit(self, options: TaskOptions, process: subprocess.Popen):
        pass
