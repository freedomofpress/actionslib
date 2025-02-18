# freedomofpress/actionslib/act/poetry

This action can be used to setup a Poetry environment in a workflow. Poetry is installed
from a pre-compiled lockfile to avoid supply chain vulnerabilities.

## Options

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
