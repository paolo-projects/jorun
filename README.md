# Jorun

Jorun is a task runner written in python, supporting windows and linux and configurable through a YML file

## Install and run

```shell
pip install jorun
```

Usage

```shell
# usage: jorun [-h] [--level LEVEL] [--file-output FILE_OUTPUT] configuration_file
# 
# A smart task runner
# 
# positional arguments:
#   configuration_file    The yml configuration file to run
# 
# options:
#  -h, --help            show this help message and exit
#  --level LEVEL         The log level (DEBUG, INFO, ...)
#  --file-output FILE_OUTPUT
#                        Log tasks output to files, one per task. This option lets you specify the directory of the log files
#  --gui                 Force running with the graphical interface
#  --no-gui              Force running without the graphical interface

jorun ./conf.yml
```

## Configuration

```yml
gui:
  services:
    tasks:
      - db
      - redis
  terminals:
    tasks:
      - test_1
      - test_2
      - test_3
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

Tasks are chained through dependencies. 
The first tasks to run are the ones without dependencies.
If you declare one or more dependencies, the task will not run until all the dependencies are either:

- *completed* (i.e. the task finished executing), by default
- _the completion pattern is matched_ (the regex pattern matched a line of the task output), if you set a **completion_pattern**
- _launched_, if you set the **run_mode** to `indefinite`

## GUI

If you run **Jorun** with the `--gui` command line option, or if you specify the **gui** option
in the yaml configuration you can start the tool with a graphical interface.
The GUI is still a prototype, but will let you keep track of the task logs individually and
even filter the log rows.

The **gui** section in the YML configuration is where you can specify the panes you want displayed,
and for each pane you can set the tasks that belong to it and the maximum number of columns visible in the pane.

## Reference

The options in **bold** are mandatory, while the others can be omitted.

### YAML Configuration file
| Option               | Description                                                                    |
|----------------------|--------------------------------------------------------------------------------|
| **tasks** _(object)_ | a mapping between task names and the [task configuration](#task_configuration) |
| **gui** _(object)_   | a mapping between pane names and the [pane configuration](#pane_configuration) |

#### <a name="pane_configuration"></a> Pane configuration

| Option                  | Description                                          |
|-------------------------|------------------------------------------------------|
| **tasks** _(array)_     | the tasks that will be displayed in this pane        |
| **columns** _(integer)_ | the number of columns you want the pane divided into |

#### <a name="task_configuration"></a> Task configuration

| Option                        | Description                                                                                                                                   |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **type** _(string)_           | the task type (`shell`, `docker` or `group`)                                                                                                  |
| **shell** _(object)_          | if **type** is `shell`, the [shell configuration](#shell_configuration)                                                                       |
| **docker** _(object)_         | if **type** is `docker`, the [docker configuration](#docker_configuration)                                                                    |
| depends _(array)_             | an optional list of task names this task depends on                                                                                           |
| run_mode _(string)_           | `wait_completion` (default) will wait for the task to finish before launching the next one, `indefinite` will launch the next one immediately |
| completion_pattern _(string)_ | if the **run_mode** is `wait_completion`, a regex pattern that if matched with a line will start the next dependent task(s)                   |
| pattern_in_stderr _(boolean)_ | if `completion_pattern` is specified, whether to search for the pattern in the error output                                                   |

#### <a name="shell_configuration"></a> Shell configuration

| Option                          | Description                                                           |
|---------------------------------|-----------------------------------------------------------------------|
| **command** _(string or array)_ | the command to run, can be a string or a list of command arguments    |
| working_directory _(string)_    | the working directory of the command                                  |
| environment _(object)_          | a mapping describing the environment variables to pass to the command |

#### <a name="docker_configuration"></a> Docker configuration

| Option                        | Description                                                                                 |
|-------------------------------|---------------------------------------------------------------------------------------------|
| **container_name** _(string)_ | the name to give to the container                                                           |
| **image** _(string)_          | the docker image to run                                                                     |
| docker_arguments _(array)_    | any additional arguments for the *docker run* command, to be inserted before the image name |
| docker_command _(array)_      | any arguments to be appended after the image name                                           |
| environment _(object)_        | env variables to be passed to the docker container                                          |
| working_directory _(string)_  | a working directory for the docker command to be run from                                   |
| stop_at_exit _(boolean)_      | will stop the container when the task is closed                                             |
