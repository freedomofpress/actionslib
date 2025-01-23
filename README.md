# actionslib

Library of reusable Github Actions workflows for use at FPF

Workflows intended for reuse are located in the `workflows/` directory. Workflows
there should not be confused for workflows in the `.github/workflows/` directory,
which are the CI/CD config for this repository specifically and are not intended
for external usage.

To use one of these workflows in another repository, a snippet like the below can
be added to the Github Actions workflow file, replacing `<workflow>` with the workflow
filename under `workflows/`:

```yaml
jobs:
  myRepoJob:
    uses: freedomofpress/actionslib/workflows/<workflow>.yaml@main
```

For more information on writing and using reusable workflows, see
[the documentation](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)
