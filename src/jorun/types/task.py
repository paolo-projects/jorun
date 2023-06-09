from typing import TypedDict, List, Literal, Optional, Dict
from dataclasses import dataclass

from ..handler.docker import DockerTask
from ..handler.shell import ShellTask


class Task(TypedDict):
    name: str
    type: Literal["shell", "docker", "group"]
    shell: Optional[ShellTask]
    docker: Optional[DockerTask]
    run_mode: Literal["wait_completion", "indefinite"]
    completion_pattern: Optional[str]
    pattern_in_stderr: Optional[bool]
    depends: Optional[List[str]]


class PaneConfiguration(TypedDict):
    columns: int
    tasks: List[str]


class GuiConfiguration(TypedDict):
    panes: Optional[Dict[str, PaneConfiguration]]
    palette: Optional[str]


class TasksConfiguration(TypedDict):
    tasks: Dict[str, Task]
    gui: Optional[GuiConfiguration]


@dataclass
class TaskNode:
    task: Task
    dependencies: List["TaskNode"]

