import multiprocessing
import sys
import typing
from collections import OrderedDict
from logging.handlers import QueueHandler
from multiprocessing.connection import Connection
from queue import Empty
from typing import List, Set, Dict, Optional
import asyncio
import logging
import traceback

from tinyioc import module, IocModule, register_instance, unregister_service

from . import constants
from .configuration import AppConfiguration
from .handler.docker import DockerTaskHandler
from .handler.group import GroupTaskHandler
from .handler.shell import ShellTaskHandler
from .messaging.message import TaskCommandMessage, TaskCommand, TaskStatusMessage, TaskStatus
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
    _running_tasks: typing.OrderedDict[str, TaskRunner]
    _async_tasks: Set[asyncio.Task]

    _missing_tasks: Dict[str, Task]
    _completed_tasks: Set[str]

    _proc_output_queue: multiprocessing.Queue
    _commands_queue: multiprocessing.Queue
    _task_updates_queue: multiprocessing.Queue

    _log_handler: logging.Handler
    _show_gui: bool

    _loop: asyncio.AbstractEventLoop

    _termination_pipe: Connection

    def __init__(self, configuration: Dict[str, Task], arguments: any, is_gui: bool,
                 output_queue: Optional[multiprocessing.Queue], commands_queue: Optional[multiprocessing.Queue],
                 task_updates_queue: Optional[multiprocessing.Queue], termination_pipe: Connection):
        super(RunnerProcess, self).__init__()

        logger.setLevel(arguments.level)

        self._show_gui = is_gui
        self._config = configuration
        self._arguments = arguments
        self._proc_output_queue = output_queue
        self._commands_queue = commands_queue
        self._task_updates_queue = task_updates_queue

        self._pipe_recv, self._pipe_emit = multiprocessing.Pipe()
        self._termination_pipe = termination_pipe

    def _run_missing_tasks(self):
        tasks_to_run: List[Task] = [t for t in self._missing_tasks.values() if
                                    (not t.get("depends") or len(t["depends"]) == 0) or set(t["depends"]).issubset(
                                        self._completed_tasks)]

        for task in tasks_to_run:
            self._missing_tasks.pop(task["name"])

        for task in tasks_to_run:
            self._run_task(task)

    def task_completed_callback(self, task_name: str, launch_deps: bool = False):
        def cb():
            logger.debug(f"Task {task_name} completed")
            self._completed_tasks.add(task_name)
            self._task_updates_queue.put(TaskStatusMessage(task=task_name, status=TaskStatus.COMPLETED))

            if launch_deps:
                logger.debug(f"Launching task {task_name} dependencies")
                self._run_missing_tasks()

        return cb

    def _run_task(self, task: Task):
        t = TaskRunner(task, self._arguments.file_output, self._arguments.level,
                       self._log_handler)
        self._running_tasks[task["name"]] = t

        logger.debug(f"Running task {task['name']}")
        async_t = self._loop.create_task(t.start(self.task_completed_callback(task['name'], launch_deps=True)))
        self._async_tasks.add(async_t)

        def async_task_done(as_t):
            self._task_updates_queue.put(TaskStatusMessage(task=task["name"], status=TaskStatus.STOPPED))
            self._async_tasks.discard(as_t)
            del self._running_tasks[task["name"]]

        async_t.add_done_callback(async_task_done)
        self._task_updates_queue.put(TaskStatusMessage(task=task["name"], status=TaskStatus.STARTED))

    def _cancel_tasks(self):
        logger.debug("Killing running tasks...")
        for k in reversed(list(self._running_tasks.keys())):
            t = self._running_tasks[k]
            logger.debug(f"Killing task {t.name}")
            try:
                t.stop()
            except:
                pass
            finally:
                del self._running_tasks[k]

    def _cancel_async_tasks(self):
        logger.debug("Killing async tasks...")
        for t in self._async_tasks.copy():
            t.cancel()

    async def _poll_commands(self):
        while True:
            try:
                c: TaskCommandMessage = self._commands_queue.get(False)
                logger.debug(f"Received command {c}")

                task = self._running_tasks.get(c.task)

                logger.debug(f"Found task {task}")

                # Task should not be running when restarting it
                if c.command == TaskCommand.START and not task:
                    logger.debug(f"Starting task {task}")
                    task_def = self._config[c.task]

                    if task_def:
                        t = TaskRunner(task_def, self._arguments.file_output, self._arguments.level,
                                       self._log_handler)
                        async_t = self._loop.create_task(t.start(None))
                        self._async_tasks.add(async_t)
                        self._running_tasks[c.task] = t

                        def async_task_done(as_t):
                            self._task_updates_queue.put(TaskStatusMessage(task=c.task, status=TaskStatus.STOPPED))
                            self._async_tasks.discard(as_t)

                            if c.task in self._running_tasks:
                                del self._running_tasks[c.task]

                        async_t.add_done_callback(async_task_done)
                        self._task_updates_queue.put(TaskStatusMessage(task=c.task, status=TaskStatus.STARTED))
                # Task should be running if we want to stop it
                elif c.command == TaskCommand.STOP and task:
                    logger.debug(f"Stopping task {task}")
                    try:
                        task.stop()
                    except:
                        traceback.print_exc()
                    finally:
                        logger.debug("Stopped. Sending new status STOPPED")
                        self._task_updates_queue.put(TaskStatusMessage(task=c.task, status=TaskStatus.STOPPED))
            except Empty:
                pass
            await asyncio.sleep(constants.COMMANDS_DEQUEUE_INTERVAL)

    def run(self) -> None:
        register_instance(AppConfiguration([
            ShellTaskHandler(),
            DockerTaskHandler(),
            GroupTaskHandler()
        ]))

        self._log_handler = QueueHandler(self._proc_output_queue) if self._show_gui else NewlineStreamHandler(
            sys.stdout)
        self._running_tasks = OrderedDict()
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

                await asyncio.sleep(constants.TERMINATION_CHECK_INTERVAL)

        try:
            self._run_missing_tasks()

            term_task = self._loop.create_task(periodic_termination_checker())
            self._async_tasks.add(term_task)
            term_task.add_done_callback(self._async_tasks.discard)

            commands_task = self._loop.create_task(self._poll_commands())
            self._async_tasks.add(commands_task)
            commands_task.add_done_callback(self._async_tasks.discard)

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
        logger.debug("Sending termination to main process")
        self._termination_pipe.send(1)

    def stop(self, timeout: Optional[float] = None):
        self._pipe_emit.send(1)
        try:
            self.join(timeout)
        except:
            logger.debug("Task executor process terminated abruptly")
        logger.debug("Tasks process terminated")
