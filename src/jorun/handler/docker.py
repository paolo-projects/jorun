import asyncio
import subprocess
from asyncio.subprocess import Process
from typing import Callable, Optional, Dict, List

from ..handler.base import BaseTaskHandler
from ..logger import logger
from ..types.options import TaskOptions


class DockerTask(TaskOptions):
    container_name: str
    image: str
    docker_arguments: Optional[List[str]]
    docker_command: Optional[List[str]]
    environment: Optional[Dict[str, str]]
    working_directory: Optional[str]
    stop_at_exit: bool


class DockerTaskHandler(BaseTaskHandler):
    _stop_on_exit: bool

    def __init__(self):
        self._stop_on_exit = False

    @property
    def task_type(self) -> str:
        return "docker"

    async def execute(self, options: Optional[DockerTask], completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[Process]:
        command = ["docker", "run", "--name", options["container_name"],
                   *(options.get("docker_arguments") or [])]

        for env_key, env_value in (options.get("environment") or {}).items():
            env_value_s = str(env_value).replace('"', '\\"')
            command.append("-e")
            command.append(f'{env_key}={env_value_s}')

        command.append(options["image"])
        command.extend(options.get("docker_command") or [])

        stderr_file = subprocess.STDOUT if stderr_redirect else subprocess.PIPE

        logger.debug(f"Running command: {' '.join(command)}")

        process = await asyncio.create_subprocess_exec(
            command[0],
            *command[1:],
            cwd=options.get("working_directory"),
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            stdin=subprocess.DEVNULL)

        self._stop_on_exit = options.get("stop_at_exit", False)
        return process

    def on_exit(self, options: DockerTask, process: Process):
        if self._stop_on_exit:
            subprocess.run([
                "docker",
                "stop",
                options['container_name']
            ])
