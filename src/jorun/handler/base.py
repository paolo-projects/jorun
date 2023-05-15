import abc
import subprocess
from typing import Callable, Optional

from ..task import TaskOptions


class BaseTaskHandler(abc.ABC):
    @property
    @abc.abstractmethod
    def task_type(self) -> str:
        pass

    @abc.abstractmethod
    def execute(self, options: TaskOptions, completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[subprocess.Popen]:
        pass

    @abc.abstractmethod
    def on_exit(self, options: TaskOptions, process: subprocess.Popen):
        pass
