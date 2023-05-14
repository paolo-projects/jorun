#!/usr/bin/env python
import argparse
import time
from threading import Lock
from typing import List

from .configuration import load_config
from .runner_threading import TaskRunner
from .task import build_task_tree, TaskNode
from .logger import logger, subprocess_logger

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)

running_tasks: List[TaskRunner] = []
running_tasks_lock = Lock()


def run_task(task: TaskNode):
    t = TaskRunner(task)

    with running_tasks_lock:
        running_tasks.append(t)

    def cb():
        logger.debug(f"Task {task.task['name']} completed")

        if len(task.dependencies) > 0:
            logger.debug(f"Launching task {task.task['name']} dependencies")
            for dep in task.dependencies:
                run_task(dep)

    logger.debug(f"Running task {task.task['name']}")
    t.start(cb)


def main():
    arguments = parser.parse_args()

    logger.setLevel(arguments.level)
    subprocess_logger.setLevel(arguments.level)

    logger.debug("Loading configuration file")
    config = load_config(arguments.configuration_file)

    logger.debug("Building dependencies tree")
    dep_tree = build_task_tree(config["main_task"], list(config["tasks"].values()))

    run_task(dep_tree)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        with running_tasks_lock:
            for i in reversed(range(len(running_tasks))):
                t = running_tasks[i]
                t.stop()
                running_tasks.pop(i)


if __name__ == "__main__":
    main()
