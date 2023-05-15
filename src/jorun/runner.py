import asyncio
import dataclasses
import subprocess
import re
from typing import Optional

from .logger import subprocess_logger
from .task import TaskNode, DockerTask, ShellTask

OUTPUT_READ_INTERVAL = 0.015


@dataclasses.dataclass
class OnStopConfig:
    stop_container: bool
    container_name: str


class TaskRunner:
    _task: TaskNode
    _process: Optional[subprocess.Popen]
    _awaiting_process_output: bool
    _on_stop_config: Optional[OnStopConfig]

    def __init__(self, task: TaskNode):
        self._task = task
        self._process = None
        self._awaiting_process_output = False

    def _on_stop(self):
        if self._on_stop_config:
            if self._on_stop_config.stop_container:
                subprocess.run([
                    "docker",
                    "stop",
                    self._on_stop_config.container_name
                ])

    async def _await_pattern(self, pattern: str) -> bool:
        pattern = re.compile(pattern)

        try:
            while not self._process.stdout.closed:
                line = self._process.stdout.readline().decode('utf-8')
                if line:
                    subprocess_logger.info(line, extra={"subprocess": self._task.task['name']})
                if pattern.match(line):
                    asyncio.get_event_loop().create_task(self._await_completion())
                    return True

                await asyncio.sleep(OUTPUT_READ_INTERVAL)
        except:
            pass

        return False

    async def _await_completion(self):
        try:
            while not self._process.stdout.closed:
                line = self._process.stdout.readline().decode('utf-8')
                if line:
                    subprocess_logger.info(line, extra={"subprocess": self._task.task['name']})
                await asyncio.sleep(OUTPUT_READ_INTERVAL)
        except:
            pass

    async def _print_output_stderr(self):
        try:
            while not self._process.stderr.closed:
                line = self._process.stderr.readline().decode('utf-8')
                if line:
                    subprocess_logger.error(line, extra={"subprocess": self._task.task['name']})
                await asyncio.sleep(OUTPUT_READ_INTERVAL)
        except:
            pass

    def stop(self):
        if self._process and self._process.poll() is None:
            self._on_stop()
            self._process.terminate()

    async def run(self):
        t = self._task.task
        run_mode = None
        completion_pattern = None
        stderr_redirect = False

        if t['type'] == "shell":
            shell_opts: ShellTask = t["shell"]
            stderr_file = subprocess.STDOUT if shell_opts.get('pattern_in_stderr') else subprocess.PIPE
            stderr_redirect = shell_opts.get('pattern_in_stderr', False)

            self._process = subprocess.Popen(
                shell_opts["command"],
                cwd=shell_opts.get("working_directory"),
                env=shell_opts.get("environment"),
                shell=(not isinstance(shell_opts["command"], list)),
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL)

            run_mode = shell_opts.get("run_mode") or "await_completion"
            completion_pattern = shell_opts.get("completion_pattern")
        elif t['type'] == "docker":
            docker_opts: DockerTask = t["docker"]
            command = ["docker", "run", "--name", docker_opts["container_name"],
                       *(docker_opts.get("docker_arguments") or [])]

            for env_key, env_value in (docker_opts.get("environment") or {}).items():
                env_value_s = str(env_value).replace('"', '\\"')
                command.append("-e")
                command.append(f'{env_key}="{env_value_s}"')

            command.append(docker_opts["image"])
            command.extend(docker_opts.get("docker_command") or [])

            stderr_file = subprocess.STDOUT if docker_opts.get('pattern_in_stderr') else subprocess.PIPE
            stderr_redirect = docker_opts.get('pattern_in_stderr', False)

            self._process = subprocess.Popen(
                command,
                cwd=docker_opts.get("working_directory"),
                shell=False,
                stdout=subprocess.PIPE,
                stderr=stderr_file,
                stdin=subprocess.DEVNULL)

            if docker_opts.get("stop_at_exit", False):
                self._on_stop_config = OnStopConfig(
                    stop_container=True,
                    container_name=docker_opts["container_name"]
                )

            run_mode = docker_opts.get("run_mode") or "await_completion"
            completion_pattern = docker_opts.get("completion_pattern")
        elif t['type'] == "group":
            return

        if not stderr_redirect:
            asyncio.get_event_loop().create_task(self._print_output_stderr())

        if run_mode == "await_completion" and completion_pattern:
            await self._await_pattern(completion_pattern)
        else:
            asyncio.get_event_loop().create_task(self._await_completion())
