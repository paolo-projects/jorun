#!/usr/bin/env python
import argparse
import asyncio
from typing import List, Set

from .handler.group import GroupTaskHandler
from .handler.docker import DockerTaskHandler
from .handler.shell import ShellTaskHandler

from .configuration import load_config
from .runner import TaskRunner
from .task import build_task_tree, TaskNode
from .logger import logger, subprocess_logger

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)

running_tasks: List[TaskRunner] = []
async_tasks: Set[asyncio.Task] = set()

task_handlers = [
    ShellTaskHandler(),
    DockerTaskHandler(),
    GroupTaskHandler()
]


async def run_task(task: TaskNode):
    t = TaskRunner(task, task_handlers)
    running_tasks.append(t)

    def cb():
        logger.debug(f"Task {task.task['name']} completed")

        if len(task.dependencies) > 0:
            logger.debug(f"Launching task {task.task['name']} dependencies")
            for dep in task.dependencies:
                async_t_inner = asyncio.create_task(run_task(dep))
                async_tasks.add(async_t_inner)
                async_t_inner.add_done_callback(async_tasks.discard)

    logger.debug(f"Running task {task.task['name']}")
    async_t = asyncio.create_task(t.start(cb))
    async_tasks.add(async_t)
    async_t.add_done_callback(async_tasks.discard)


def main():
    arguments = parser.parse_args()

    logger.setLevel(arguments.level)
    subprocess_logger.setLevel(arguments.level)

    logger.debug("Loading configuration file")
    config = load_config(arguments.configuration_file)

    logger.debug("Building dependencies tree")
    dep_tree = build_task_tree(config["main_task"], list(config["tasks"].values()))

    main_task = None
    loop = asyncio.new_event_loop()

    try:
        main_task = loop.create_task(run_task(dep_tree))
        loop.run_forever()
    except KeyboardInterrupt:
        for i in reversed(range(len(running_tasks))):
            if main_task:
                main_task.cancel()
            for t in async_tasks:
                t.cancel()

            t = running_tasks[i]
            t.stop()
            running_tasks.pop(i)

            loop.stop()


if __name__ == "__main__":
    main()
