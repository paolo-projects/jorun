from collections.abc import Callable, Iterable, Mapping
from threading import Thread
from typing import List, Set, Dict
import asyncio
from tinyioc import inject
import logging
from queue import Queue
import sys
import traceback

from .types.task import TasksConfiguration, Task
from .runner import TaskRunner
from .configuration import AppConfiguration
from .logger import logger, NewlineStreamHandler


class RunnerThread(Thread):
    _config: TasksConfiguration
    _arguments: any
    _running_tasks: List[TaskRunner]
    _async_tasks: Set[asyncio.Task]

    _missing_tasks: Dict[str, Task]
    _completed_tasks: Set[str]

    _log_handler: logging.Handler
    _show_gui: bool

    def __init__(self, configuration: TasksConfiguration, arguments: any, ui_queue: Queue):
        super(RunnerThread, self).__init__()

        self._config = configuration
        self._arguments = arguments
        self._running_tasks = []
        self._async_tasks = set()
        self._missing_tasks = {}
        self._completed_tasks = set()


        gui_config = configuration.get("gui")
        self._show_gui = not arguments.no_gui and (arguments.gui or gui_config)

        if self._show_gui:
            logger.debug("Using graphical interface")
            self._log_handler = logging.handlers.QueueHandler(ui_queue)
        else:
            logger.debug("Using console output")
            self._log_handler = NewlineStreamHandler(sys.stdout)

    
    def _run_missing_tasks(self):
        tasks_to_run: List[Task] = [t for t in self._missing_tasks.values() if
                                    (not t.get("depends") or len(t["depends"]) == 0) or set(t["depends"]).issubset(
                                        self._completed_tasks)]

        for task in tasks_to_run:
            self._missing_tasks.pop(task["name"])

        for task in tasks_to_run:
            self._run_task(task)


    def _run_task(self, task: Task):
        t = TaskRunner(task, self._arguments.file_output, self._arguments.level,
                    self._log_handler)
        self._running_tasks.append(t)

        def cb():
            logger.debug(f"Task {task['name']} completed")
            self._completed_tasks.add(task["name"])

            logger.debug(f"Launching task {task['name']} dependencies")
            self._run_missing_tasks()

        logger.debug(f"Running task {task['name']}")
        async_t = asyncio.get_event_loop().create_task(t.start(cb))
        self._async_tasks.add(async_t)
        async_t.add_done_callback(self._async_tasks.discard)

    def run(self) -> None:
        missing_tasks = self._config["tasks"].copy()
        loop = asyncio.get_event_loop()

        if self._show_gui:
            def on_app_stop():
                logger.info("Main window closed")
                if loop.is_running():
                    loop.stop()

            ui_tasks = [t_name for t_name, t_val in missing_tasks.items() if t_val["type"] != "group"]

            ui_application = UiApplication(ui_tasks, on_app_stop, task_streams_queue, gui_config)
            ui_application.start_ui()

        try:
            self._run_missing_tasks()
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
        