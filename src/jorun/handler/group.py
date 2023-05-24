from asyncio.subprocess import Process
from typing import Callable, Optional

from ..handler.base import BaseTaskHandler
from ..types.options import TaskOptions


class GroupTaskHandler(BaseTaskHandler):
    @property
    def task_type(self) -> str:
        return "group"

    async def execute(self, options: Optional[TaskOptions], completion_callback: Callable, stderr_redirect: bool) \
            -> Optional[Process]:
        completion_callback()
        return None

    def on_exit(self, options: TaskOptions, process: Process):
        pass
