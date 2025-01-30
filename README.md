# actionslib

Library of reusable Github Actions workflows for use at FPF

Workflow files are available in the `.github/workflows/` directory. To use 
one of these workflows in another repository, a snippet like the below can be 
added to the Github Actions workflow file, replacing `<workflow>` with the workflow
filename under `workflows/`:

```yaml
jobs:
  myRepoJob:
    uses: freedomofpress/actionslib/.github/workflows/<workflow>.yaml@main
```

> [!IMPORTANT]
> Workflows prefixed with a `_` (for example `_ci.yaml`) are part of this repository's
> internal CI/CD automation and are not intended for reuse by other repositories.

> [!NOTE]
> See also: [Github Docs: Reusing Workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)


## Available Workflows

Index of available reusable workflows in this repository and more information on 
their usage.

### lint-actions

A workflow that uses [Zizmor](https://woodruffw.github.io/zizmor/) to
run static analysis checks on Github Actions Workflow files.

> [!NOTE]
> See also: [Zizmor configuration](https://woodruffw.github.io/zizmor/configuration/)
> for configuring repository specific settings.

See [the workflow file](.github/workflows/lint-actions.yaml) for usage details.