#!/usr/bin/env python
import argparse
import traceback
from multiprocessing import Queue
from tinyioc import register_singleton, register_instance

from jorun.palette.hacker import HackerColorPalette
from jorun.palette.kimbie_dark import KimbieDarkColorPalette
from jorun.palette.solarized_dark import SolarizedDarkColorPalette
from jorun.runner_process import RunnerProcess
from jorun.ui.command_handler import TaskCommandHandler
from .palette.base import BaseColorPalette
from .palette.darcula import DarculaColorPalette
from .palette.monokai import MonokaiColorPalette
from .ui.application import UiApplication

from .configuration import load_config
from .types.task import TasksConfiguration, GuiConfiguration
from .logger import logger

parser = argparse.ArgumentParser(prog="jorun", description="A smart task runner", add_help=True)

parser.add_argument("configuration_file", help="The yml configuration file to run")
parser.add_argument("--level", help="The log level (DEBUG, INFO, ...)", default="INFO", type=str)
parser.add_argument("--file-output", help="Log tasks output to files, one per task. "
                                          "This option lets you specify the directory of the log files", type=str)
parser.add_argument("--gui", help="Force running with the graphical interface", action='store_true')
parser.add_argument("--no-gui", help="Force running without the graphical interface", action='store_true')

program_arguments: argparse.Namespace

task_streams_queue = Queue()
task_messages_queue = Queue()
task_commands_queue = Queue()

ui_application: UiApplication

palettes = {
    DarculaColorPalette.name: DarculaColorPalette,
    MonokaiColorPalette.name: MonokaiColorPalette,
    KimbieDarkColorPalette.name: KimbieDarkColorPalette,
    SolarizedDarkColorPalette.name: SolarizedDarkColorPalette,
    HackerColorPalette.name: HackerColorPalette
}


def main():
    global program_arguments, ui_application

    program_arguments = parser.parse_args()
    logger.setLevel(program_arguments.level)

    logger.debug("Loading configuration file")
    config: TasksConfiguration = load_config(program_arguments.configuration_file)

    missing_tasks = config["tasks"].copy()

    tasks_config = config.get("tasks")

    if not tasks_config:
        raise RuntimeError("No tasks to run found")

    gui_config: GuiConfiguration = config.get("gui")

    palette = (gui_config or {}).get("palette", "darcula")
    register_singleton(palettes.get(palette, palettes["darcula"]), register_for=BaseColorPalette)

    register_instance(TaskCommandHandler(task_commands_queue))

    show_gui = not program_arguments.no_gui and (program_arguments.gui or gui_config)

    if show_gui:
        logger.debug("Using graphical interface")
    else:
        logger.debug("Using console output")

    tasks_thread = RunnerProcess(tasks_config, program_arguments, show_gui, task_streams_queue, task_commands_queue,
                                 task_messages_queue)
    tasks_thread.start()

    try:
        if show_gui:
            ui_tasks = [t_name for t_name, t_val in missing_tasks.items() if t_val["type"] != "group"]

            ui_application = UiApplication(ui_tasks, task_streams_queue, task_messages_queue, task_commands_queue,
                                           gui_config['panes'])
            ui_application.start_ui()
        else:
            tasks_thread.join()
    except KeyboardInterrupt:
        logger.debug("Requested termination")
    except Exception as e:
        logger.error("An error occurred")
        traceback.print_exception(e)
    finally:
        if show_gui:
            logger.debug("Quitting the UI")
            ui_application.stop_ui()
        logger.debug("Quitting the tasks")
        tasks_thread.stop(10)

    logger.debug("Terminated")


if __name__ == "__main__":
    main()
