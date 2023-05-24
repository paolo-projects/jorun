#!/usr/bin/env python
import argparse
import asyncio
import traceback
from logging.handlers import QueueHandler
from queue import Queue
from typing import List, Set, Dict
from tinyioc import register_instance

from jorun.palette.base import BaseColorPalette
from jorun.palette.darcula import DarculaColorPalette
from .ui.application import UiApplication
from .handler.group import GroupTaskHandler
from .handler.docker import DockerTaskHandler
from .handler.shell import ShellTaskHandler

from .configuration import load_config
from .runner import TaskRunner
from .task import Task
from .logger import logger

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)
parser.add_argument("--file-output", help="Log tasks output to files, one per task. "
                                          "This option lets you specify the directory of the log files", type=str)

running_tasks: List[TaskRunner] = []
async_tasks: Set[asyncio.Task] = set()

missing_tasks: Dict[str, Task] = {}
completed_tasks: Set[str] = set()

program_arguments: argparse.Namespace

task_handlers = [
    ShellTaskHandler(),
    DockerTaskHandler(),
    GroupTaskHandler()
]

task_streams_queue = Queue()
task_streams_queue_handler = QueueHandler(task_streams_queue)

ui_application: UiApplication


def run_missing_tasks():
    tasks_to_run: List[Task] = [t for t in missing_tasks.values() if
                                (not t.get("depends") or len(t["depends"]) == 0) or set(t["depends"]).issubset(
                                    completed_tasks)]

    for task in tasks_to_run:
        missing_tasks.pop(task["name"])

    for task in tasks_to_run:
        run_task(task)


def run_task(task: Task):
    t = TaskRunner(task, task_handlers, program_arguments.file_output, program_arguments.level, task_streams_queue_handler)
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
    global missing_tasks, program_arguments, ui_application

    register_instance(DarculaColorPalette(), register_for=BaseColorPalette)

    program_arguments = parser.parse_args()

    logger.setLevel(program_arguments.level)

    logger.debug("Loading configuration file")
    config = load_config(program_arguments.configuration_file)

    logger.debug("Building dependencies tree")
    # no dependency tree. we now support multiple dependencies
    # dep_tree = build_task_tree(config["main_task"], list(config["tasks"].values()))

    missing_tasks = config["tasks"].copy()

    loop = asyncio.get_event_loop()

    def on_app_stop():
        logger.info("Main window closed")
        loop.stop()

    ui_tasks = [t_name for t_name, t_val in missing_tasks.items() if t_val["type"] != "group"]

    ui_application = UiApplication(ui_tasks, on_app_stop, task_streams_queue)
    ui_application.start_ui()

    try:
        run_missing_tasks()
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Requested termination")
    except Exception as e:
        logger.error("An error occurred")
        traceback.print_exception(e)
    finally:
        logger.info("Killing running tasks...")
        ui_application.stop_ui()

        for t in async_tasks:
            t.cancel()

        for i in reversed(range(len(running_tasks))):
            t = running_tasks[i]
            t.stop()
            running_tasks.pop(i)

        if loop.is_running():
            loop.stop()


if __name__ == "__main__":
    main()
