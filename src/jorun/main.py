#!/usr/bin/env python
import argparse
import time
from typing import List

from .configuration import load_config
from .runner_threading import TaskRunner
from .task import build_task_tree, TaskNode
from .logger import logger, subprocess_logger

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)

running_tasks: List[TaskRunner] = []


def run_task(task: TaskNode):
    t = TaskRunner(task)
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
        for t in running_tasks:
            t.stop()


if __name__ == "__main__":
    main()
