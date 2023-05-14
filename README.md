# Jorun

Jorun is a task runner written in python, supporting windows and linux and configurable through a YML file

## Install and run

```shell
pip install jorun
```

Usage

```shell
# usage: jorun [-h] [--level LEVEL] configuration_file
#
# A smart task runner
#
# positional arguments:
#   configuration_file  The yml configuration file to run
#
# options:
#   -h, --help          show this help message and exit
#   --level LEVEL       The log level (DEBUG, INFO, ...)

jorun ./conf.yml
```

## Configuration

```yml
main_task: db
tasks:
  db:
    type: docker
    docker:
      container_name: test
      image: postgres
      docker_arguments:
        - "--rm"
      stop_at_exit: true
      environment:
        POSTGRES_PASSWORD: test
      completion_pattern: .*database system is ready to accept connections.*
      pattern_in_stderr: true
  redis:
    type: docker
    docker:
      container_name: rds
      image: redis
      docker_arguments:
        - "--rm"
      stop_at_exit: true
      completion_pattern: .*Ready to accept connections.*
      pattern_in_stderr: true
    depends:
      - db
  test:
    type: group
    depends:
      - redis
  test_1:
    type: shell
    shell:
      command: echo TEST 1
    depends:
      - test
  test_2:
    type: shell
    shell:
      command: echo TEST 2
    depends:
      - test
  test_3:
    type: shell
    shell:
      command: echo TEST 3
    depends:
      - test
```

This sample YML file shows two task types you can run:

- **Shell**: a task launching a shell command
- **Docker**: a task optimized for docker containers
- **Group**: a task that groups other tasks (for parallel execution)

The task runner supports searching for a pattern in the task output to
signal its completion. This way you can start a dependent task after the pattern
shows up in the task output.

Tasks are chained through dependencies. If you declare a task dependency on another task,
it will wait for the first task to complete before launching the second task

## Reference

### YAML Configuration file**

- `main_task: str`: the name of the task to be executed  
- `tasks: Dict[str, Task]`: a mapping between task names and the [task configuration](#task_configuration)

#### <a name="task_configuration"></a> Task configuration

- `type: Literal["shell", "docker", "group"]`: the task type
- `shell: Optional[ShellTask]`: if *type* is **shell**, the [shell configuration](#shell_configuration)
- `docker: Optional[DockerTask]`: if *type* is **docker**, the [docker configuration](#docker_configuration)
- `depends: Optional[List[str]]`: an optional list of task names this task depends upon

#### <a name="shell_configuration"></a> Shell configuration

- `command: Union[str, List[str]]`: the command to run, can be a string or a list of command arguments 
- `run_mode: Literal["wait_completion", "indefinite"]`: **wait_completion** will wait for the task to finish before launching the next one, **indefinite** will launch the next one immediately
- `completion_pattern: Optional[str]`: if the *run_mode* is **wait_completion**, a pattern that if matched with a line will start the next dependent task(s)  
- `pattern_in_stderr: Optional[bool]`: whether to search for the pattern in the error output
- `working_directory: Optional[str]`: the working directory of the command
- `environment: Optional[Dict[str, str]]`: a mapping with the environment variables to pass to the command

#### <a name="docker_configuration"></a> Docker configuration

- `container_name: str`: the name to give to the container
- `image: str`: the docker image to run
- `docker_arguments: Optional[List[str]]`: any additional arguments for the *docker run* command, to be inserted before the image name
- `docker_command: Optional[List[str]]`: any arguments to be appended after the image name 
- `environment: Optional[Dict[str, str]]`: env variables to be passed to the docker container
- `working_directory: Optional[str]`: a working directory for the docker command to be run from
- `stop_at_exit: bool`: will stop the container when the task is closed
- `run_mode: Literal["wait_completion", "indefinite"]`: **wait_completion** will wait for the task to finish before launching the next one, **indefinite** will launch the next one immediately
- `completion_pattern: Optional[str]`: if the *run_mode* is **wait_completion**, a pattern that if matched with a line will start the next dependent task(s)
- `pattern_in_stderr: Optional[bool]`: whether to search for the pattern in the error output