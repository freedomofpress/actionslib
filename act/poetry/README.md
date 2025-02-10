# freedomofpress/actionslib/act/poetry

This action can be used to setup a Poetry environment in a workflow. Poetry is installed
from a pre-compiled lockfile to avoid supply chain vulnerabilities. Once this action is
run in a workflow, the `poetry run` command can be invoked in subsequent steps to run
commands inside the Poetry environment.

See [the `action.yml` file](action.yml) for details on this action's inputs and outputs.

## Example Usage

Install only the test and lint dependency groups:

```yaml
steps:
- name: Setup Poetry
  uses: freedomofpress/actionslib/act/poetry@main
  with:
    root: false
    groups: test,lint
```

Install the root package with the `[numpy]` extra:

```yaml
steps:
- name: Setup Poetry
  uses: freedomofpress/actionslib/act/poetry@main
  with:
    extras: numpy
```
