# actionslib

Library of reusable Github Actions workflows for use at FPF

Workflows intended for reuse are located in the `workflows/` directory. Workflows there
should not be confused for workflows in the `.github/workflows/` directory, which are the
CI/CD config for this repository specifically and are not intended for external usage.

To use one of these workflows in another repository, a snippet like the below can be added
to the Github Actions workflow file, replacing `<workflow>` with the workflow filename
under `workflows/`:

```yaml
jobs:
  myRepoJob:
    uses: freedomofpress/actionslib/workflows/<workflow>.yaml@main
```

For more information on writing and using reusable workflows, see
[the documentation](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)

## Developing

System requirements:

- Python >=3.11
- [Poetry >=1.8, \<2.0](https://python-poetry.org/docs/#installation)

> [!NOTE]
> While not required, it is also recommended to install
> [`act`](https://nektosact.com/installation/index.html) to run workflows locally during
> development.

After installing Python and Poetry, run `make dev` to setup the local deveopment
environment.
