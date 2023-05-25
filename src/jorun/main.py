#!/usr/bin/env python
import argparse
import asyncio
import logging
import sys
import traceback
from logging.handlers import QueueHandler
from queue import Queue
from typing import List, Set, Dict
from tinyioc import register_instance

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
    global missing_tasks, program_arguments, ui_application, log_handler

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
    loop = asyncio.get_event_loop()

    if show_gui:
        def on_app_stop():
            logger.info("Main window closed")
            if loop.is_running():
                loop.stop()

        ui_tasks = [t_name for t_name, t_val in missing_tasks.items() if t_val["type"] != "group"]

        ui_application = UiApplication(ui_tasks, on_app_stop, task_streams_queue, gui_config)
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
        logger.info("Terminating the async loop...")
        if loop.is_running():
            loop.stop()

        if show_gui:
            logger.info("Killing gui...")
            ui_application.stop_ui()

        logger.info("Killing async tasks...")
        for t in async_tasks:
            t.cancel()

        logger.info("Killing running tasks...")
        for i in reversed(range(len(running_tasks))):
            t = running_tasks[i]
            try:
                t.stop()
            except:
                pass
            finally:
                running_tasks.pop(i)


if __name__ == "__main__":
    main()
