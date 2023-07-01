import enum
from dataclasses import dataclass


class TaskStatus(enum.Enum):
    STOPPED = 1
    STARTED = 2
    COMPLETED = 3


class TaskCommand(enum.Enum):
    START = 1
    STOP = 2


@dataclass
class BaseMessage:
    type: str


@dataclass
class TaskStatusMessage:
    task: str
    status: TaskStatus
    type: str = "task-status"


@dataclass
class TaskCommandMessage:
    task: str
    command: TaskCommand
    type: str = "task-command"


