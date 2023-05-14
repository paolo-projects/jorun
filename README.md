# Jorun

Jorun is a task runner written in python, supporting windows and linux and configurable through a YML file

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