#!/usr/bin/env python
import argparse
import asyncio
import sys
from typing import List, Set, Dict

from .handler.group import GroupTaskHandler
from .handler.docker import DockerTaskHandler
from .handler.shell import ShellTaskHandler

from .configuration import load_config
from .runner import TaskRunner
from .task import Task
from .logger import logger, subprocess_logger

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)

running_tasks: List[TaskRunner] = []
async_tasks: Set[asyncio.Task] = set()

missing_tasks: Dict[str, Task] = {}
completed_tasks: Set[str] = set()

task_handlers = [
    ShellTaskHandler(),
    DockerTaskHandler(),
    GroupTaskHandler()
]


def run_missing_tasks():
    tasks_to_run: List[Task] = [t for t in missing_tasks.values() if set(t["depends"]).issubset(completed_tasks)]

    for task in tasks_to_run:
        missing_tasks.pop(task["name"])

    for task in tasks_to_run:
        run_task(task)


def run_task(task: Task):
    t = TaskRunner(task, task_handlers)
    running_tasks.append(t)

    def cb():
        logger.debug(f"Task {task['name']} completed")
        completed_tasks.add(task["name"])

        logger.debug(f"Launching task {task['name']} dependencies")
        run_missing_tasks()

    logger.debug(f"Running task {task['name']}")
    async_t = asyncio.get_event_loop().create_task(t.start(cb))
    async_tasks.add(async_t)
    async_t.add_done_callback(async_tasks.discard)


def main():
    global missing_tasks

    arguments = parser.parse_args()

    logger.setLevel(arguments.level)
    subprocess_logger.setLevel(arguments.level)

    logger.debug("Loading configuration file")
    config = load_config(arguments.configuration_file)

    logger.debug("Building dependencies tree")
    # no dependency tree. we now support multiple dependencies
    # dep_tree = build_task_tree(config["main_task"], list(config["tasks"].values()))

    missing_tasks = config["tasks"].copy()

    main_task = missing_tasks.get(config["main_task"])

    if not main_task:
        print("Main task not found", file=sys.stderr)
        exit(1)

    loop = asyncio.get_event_loop()

    try:
        missing_tasks.pop(main_task["name"])
        run_task(main_task)
        loop.run_forever()
    except KeyboardInterrupt:
        for i in reversed(range(len(running_tasks))):
            for t in async_tasks:
                t.cancel()

            t = running_tasks[i]
            t.stop()
            running_tasks.pop(i)

            loop.stop()


if __name__ == "__main__":
    main()
