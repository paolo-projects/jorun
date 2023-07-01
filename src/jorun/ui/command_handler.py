from multiprocessing import Queue

from jorun.messaging.message import TaskCommand, TaskCommandMessage


class TaskCommandHandler:
    _commands_queue: Queue

    def __init__(self, queue: Queue):
        self._commands_queue = queue

    def dispatch(self, task_name: str, command: TaskCommand):
        self._commands_queue.put(TaskCommandMessage(task=task_name, command=command))