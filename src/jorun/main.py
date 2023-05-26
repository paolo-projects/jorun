#!/usr/bin/env python
import argparse
import asyncio
import sys
import traceback
from logging.handlers import QueueHandler
from queue import Queue
from tinyioc import register_instance

from jorun.runner_thread import RunnerThread
from .palette.base import BaseColorPalette
from .palette.darcula import DarculaColorPalette
from .ui.application import UiApplication
from .handler.group import GroupTaskHandler
from .handler.docker import DockerTaskHandler
from .handler.shell import ShellTaskHandler

from .configuration import load_config, AppConfiguration
from .types.task import TasksConfiguration
from .logger import logger, NewlineStreamHandler

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)
parser.add_argument("--file-output", help="Log tasks output to files, one per task. "
                                          "This option lets you specify the directory of the log files", type=str)
parser.add_argument("--gui", help="Force running with the graphical interface", action='store_true')
parser.add_argument("--no-gui", help="Force running without the graphical interface", action='store_true')

program_arguments: argparse.Namespace

task_streams_queue = Queue()

ui_application: UiApplication


def main():
    global program_arguments, ui_application

    register_instance(DarculaColorPalette(), register_for=BaseColorPalette)
    register_instance(AppConfiguration([
        ShellTaskHandler(),
        DockerTaskHandler(),
        GroupTaskHandler()
    ]))

    program_arguments = parser.parse_args()
    logger.setLevel(program_arguments.level)

    logger.debug("Loading configuration file")
    config: TasksConfiguration = load_config(program_arguments.configuration_file)

    missing_tasks = config["tasks"].copy()

    tasks_config = config.get("tasks")

    if not tasks_config:
        raise RuntimeError("No tasks to run found")

    gui_config = config.get("gui")
    show_gui = not program_arguments.no_gui and (program_arguments.gui or gui_config)

    if show_gui:
        logger.debug("Using graphical interface")
        log_handler = QueueHandler(task_streams_queue)
    else:
        logger.debug("Using console output")
        log_handler = NewlineStreamHandler(sys.stdout)

    tasks_thread = RunnerThread(tasks_config, program_arguments, log_handler)
    tasks_thread.start()

    try:
        if show_gui:
            ui_tasks = [t_name for t_name, t_val in missing_tasks.items() if t_val["type"] != "group"]

            ui_application = UiApplication(ui_tasks, task_streams_queue, gui_config)
            ui_application.start_ui()
        else:
            tasks_thread.join()
    except KeyboardInterrupt:
        logger.debug("Requested termination")
    except Exception as e:
        logger.error("An error occurred")
        traceback.print_exception(e)
    finally:
        ui_application.stop_ui()
        tasks_thread.stop()


if __name__ == "__main__":
    main()
