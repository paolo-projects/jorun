import subprocess
from typing import Callable, Optional

from ..handler.base import BaseTaskHandler
from ..task import TaskOptions


class GroupTaskHandler(BaseTaskHandler):
    @property
    def task_type(self) -> str:
        return "group"

    def execute(self, options: TaskOptions, completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[subprocess.Popen]:
        completion_callback()
        return None

    def on_exit(self, options: TaskOptions, process: subprocess.Popen):
        pass
