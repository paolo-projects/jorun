from typing import TypedDict, List, Literal, Optional, Union, Dict
from dataclasses import dataclass


class TaskBuildException(Exception):
    pass


class ShellTask(TypedDict):
    command: Union[str, List[str]]
    run_mode: Literal["wait_completion", "indefinite"]
    completion_pattern: Optional[str]
    pattern_in_stderr: Optional[bool]
    working_directory: Optional[str]
    environment: Optional[Dict[str, str]]


class DockerTask(TypedDict):
    container_name: str
    image: str
    docker_arguments: Optional[List[str]]
    docker_command: Optional[List[str]]
    environment: Optional[Dict[str, str]]
    working_directory: Optional[str]
    stop_at_exit: bool
    run_mode: Literal["wait_completion", "indefinite"]
    completion_pattern: Optional[str]
    pattern_in_stderr: Optional[bool]


class Task(TypedDict):
    name: str
    type: Literal["shell", "docker", "group"]
    shell: Optional[ShellTask]
    docker: Optional[DockerTask]
    depends: Optional[List[str]]


class TasksConfiguration(TypedDict):
    main_task: str
    tasks: Dict[str, Task]


@dataclass
class TaskNode:
    task: Task
    dependencies: List["TaskNode"]


def _setup_dependencies(parent_node: TaskNode, bucket: List[Task]):
    parent_node.dependencies = [
        TaskNode(task=t, dependencies=[]) for t in bucket if parent_node.task["name"] in (t.get("depends") or [])
    ]

    # remove dependencies from bucket
    for d in parent_node.dependencies:
        bucket.pop(bucket.index(d.task))

    # build dependencies for children
    for dep in parent_node.dependencies:
        _setup_dependencies(dep, bucket)


def build_task_tree(main_task_name: str, tasks: List[Task]) -> TaskNode:
    tasks_bucket = tasks.copy()

    main_task = next(t for t in tasks if t["name"] == main_task_name)

    if not main_task:
        raise TaskBuildException("No main task found")

    tasks_bucket.pop(tasks_bucket.index(main_task))

    # build deps tree
    tree = TaskNode(task=main_task, dependencies=[])
    _setup_dependencies(tree, tasks_bucket)

    return tree
