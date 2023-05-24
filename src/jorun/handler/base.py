import abc
from asyncio.subprocess import Process
from typing import Callable, Optional

from ..types.options import TaskOptions


class BaseTaskHandler(abc.ABC):
    @property
    @abc.abstractmethod
    def task_type(self) -> str:
        pass

    @abc.abstractmethod
    async def execute(self, options: Optional[TaskOptions], completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[Process]:
        pass

    @abc.abstractmethod
    def on_exit(self, options: TaskOptions, process: Process):
        pass
