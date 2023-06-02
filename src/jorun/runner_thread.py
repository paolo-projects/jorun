from threading import Thread
from typing import List, Set, Dict, Optional
import asyncio
import logging
import traceback

from tinyioc import module, IocModule, register_instance, unregister_service

from .types.task import Task
from .runner import TaskRunner
from .logger import logger


@module()
class RunnerThreadModule(IocModule):
    pass


class RunnerThread(Thread):
    _running: bool

    _config: Dict[str, Task]
    _arguments: any
    _running_tasks: List[TaskRunner]
    _async_tasks: Set[asyncio.Task]

    _missing_tasks: Dict[str, Task]
    _completed_tasks: Set[str]

    _log_handler: logging.Handler
    _show_gui: bool

    _loop: asyncio.AbstractEventLoop

    def __init__(self, configuration: Dict[str, Task], arguments: any, log_handler: logging.Handler):
        super(RunnerThread, self).__init__()

        self._config = configuration
        self._arguments = arguments
        self._log_handler = log_handler
        self._running_tasks = []
        self._async_tasks = set()
        self._missing_tasks = configuration.copy()
        self._completed_tasks = set()

        self._loop = asyncio.new_event_loop()

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
        self._running = True
        asyncio.set_event_loop(self._loop)

        register_instance(self._loop, module=RunnerThreadModule, register_for=asyncio.AbstractEventLoop)

        try:
            self._run_missing_tasks()
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
        if self._running:
            #self._cancel_async_tasks()
            #self._cancel_tasks()
            self._loop.call_soon_threadsafe(self._loop.stop)
            self.join(timeout)
            logger.debug("Tasks thread terminated")
