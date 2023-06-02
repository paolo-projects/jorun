import multiprocessing
import queue
import sys
from logging.handlers import QueueHandler
from multiprocessing.connection import Connection
from threading import Thread
from typing import List, Set, Dict, Optional
import asyncio
import logging
import traceback

from tinyioc import module, IocModule, register_instance, unregister_service

from .configuration import AppConfiguration
from .handler.docker import DockerTaskHandler
from .handler.group import GroupTaskHandler
from .handler.shell import ShellTaskHandler
from .types.task import Task
from .runner import TaskRunner
from .logger import logger, NewlineStreamHandler


@module()
class RunnerThreadModule(IocModule):
    pass


class RunnerProcess(multiprocessing.Process):
    _running: bool
    _pipe_emit: Connection
    _pipe_recv: Connection

    _config: Dict[str, Task]
    _arguments: any
    _running_tasks: List[TaskRunner]
    _async_tasks: Set[asyncio.Task]

    _missing_tasks: Dict[str, Task]
    _completed_tasks: Set[str]

    _queue: multiprocessing.Queue
    _log_handler: logging.Handler
    _show_gui: bool

    _loop: asyncio.AbstractEventLoop

    def __init__(self, configuration: Dict[str, Task], arguments: any, is_gui: bool,
                 output_queue: Optional[multiprocessing.Queue]):
        super(RunnerProcess, self).__init__()

        self._show_gui = is_gui
        self._config = configuration
        self._arguments = arguments
        self._queue = output_queue

        self._pipe_recv, self._pipe_emit = multiprocessing.Pipe()

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
        async_t = self._loop.create_task(t.start(cb))
        self._async_tasks.add(async_t)
        async_t.add_done_callback(self._async_tasks.discard)

    def _cancel_tasks(self):
        logger.debug("Killing running tasks...")
        for i in reversed(range(len(self._running_tasks))):
            t = self._running_tasks[i]
            logger.debug(f"Killing task {t.name}")
            try:
                t.stop()
            except:
                pass
            finally:
                self._running_tasks.pop(i)

    def _cancel_async_tasks(self):
        logger.debug("Killing async tasks...")
        for t in self._async_tasks.copy():
            t.cancel()

    def run(self) -> None:
        register_instance(AppConfiguration([
            ShellTaskHandler(),
            DockerTaskHandler(),
            GroupTaskHandler()
        ]))

        self._log_handler = QueueHandler(self._queue) if self._show_gui else NewlineStreamHandler(sys.stdout)
        self._running_tasks = []
        self._async_tasks = set()
        self._missing_tasks = self._config.copy()
        self._completed_tasks = set()

        self._running = True

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        register_instance(self._loop, module=RunnerThreadModule, register_for=asyncio.AbstractEventLoop)

        async def periodic_termination_checker():
            while self._running:
                if self._pipe_recv.poll():
                    self._loop.call_soon_threadsafe(self._loop.stop)
                    break

                await asyncio.sleep(0.3)

        try:
            self._run_missing_tasks()

            term_task = self._loop.create_task(periodic_termination_checker())
            self._async_tasks.add(term_task)
            term_task.add_done_callback(self._async_tasks.discard)

            self._loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Requested termination")
        except Exception as e:
            logger.error("An error occurred")
            traceback.print_exception(e)
        finally:
            unregister_service(asyncio.AbstractEventLoop, module=RunnerThreadModule)

            self._cancel_async_tasks()
            self._cancel_tasks()

            if self._loop.is_running():
                logger.debug("Terminating the async loop...")
                self._loop.stop()

            logger.debug("Closing the async loop...")
            self._loop.close()

        self._running = False

    def stop(self, timeout: Optional[float] = None):
        self._pipe_emit.send(1)
        try:
            self.join(timeout)
        except:
            logger.debug("Task executor process terminated abruptly")
        logger.debug("Tasks process terminated")
