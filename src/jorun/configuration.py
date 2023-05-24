import yaml
from .types.task import TasksConfiguration


def load_config(file_name: str) -> TasksConfiguration:
    with open(file_name, "r") as yamlf:
        config: TasksConfiguration = yaml.safe_load(yamlf)
        for t_name, t_task in config['tasks'].items():
            t_task['name'] = t_name

        return config
