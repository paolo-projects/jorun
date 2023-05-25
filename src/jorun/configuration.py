import yaml
from typing import List

from .types.task import TasksConfiguration
from .handler.base import BaseTaskHandler


def load_config(file_name: str) -> TasksConfiguration:
    with open(file_name, "r") as yamlf:
        config: TasksConfiguration = yaml.safe_load(yamlf)
        for t_name, t_task in config['tasks'].items():
            t_task['name'] = t_name

        return config


class AppConfiguration:
    handlers: List[BaseTaskHandler]

    def __init__(self, handlers: List[BaseTaskHandler]) -> None:
        self.handlers = handlers