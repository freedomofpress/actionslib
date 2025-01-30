# actionslib

Library of reusable [Github Actions](https://docs.github.com/en/actions) workflows and
composite actions for use at FPF.

**Table of contents:**

- [Using Reusable Workflows](#using-reusable-workflows)
- [Using Composite Actions](#using-composite-actions)
- [Available Workflows](#available-workflows)
  - [lint-actions](.github/workflows/lint-actions.yaml)
- [Available Composite Actions](#available-composite-actions)
  - [example-action](act/example-action/)
- [Developer Documentation](#developer-documentation)
- [License](#license)

## Using Reusable Workflows

Reusable Workflows are complete blocks of Github Actions steps that can be imported
directly into the configuration of another repository. While reusable workflows can define
inputs and secrets, they cannot be modified or combined with other steps at runtime in the
calling repository's configuration. This makes Reusable Workflows best suited to running
complete end-to-end tests or processes that need to run in multiple repositories exactly
the same way.

The Reusable Workflows available in this repository are stored in the `.github/workflows/`
directory. To use one of these workflows in another repository, a snippet like the below
can be added to the Github Actions workflow file, replacing `<workflow>` with the workflow
filename under `.github/workflows/`:

```yaml
jobs:
  myRepoJob:
    uses: freedomofpress/actionslib/.github/workflows/<workflow>.yaml@main
```

If the Reusable Workflow defines any inputs or secrets, they can be specified using the
`with` and `secrets` keywords respectively:

```yaml
jobs:
  myRepoJob:
    uses: freedomofpress/actionslib/.github/workflows/death-star.yaml@main
    with:
      super-laser-target: alderann
      power-level: 9001
    secrets:
      activation-key: ${{ secrets.SOOPER_SEEKRET_KEY }}
```

See the documentation for each specific Reusable Workflow to see what inputs and secrets
they support.

> [!IMPORTANT]
> Workflow files prefixed with a '`_`' (for example `.github/workflows/_ci.yaml`) are part
> of this repository's internal CI/CD automation and are not intended for reuse by other
> repositories.

Related reading:

- [Github Docs: Workflow Syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [Github Docs: Reusing Workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)
- [Available Reusable Workflows](#available-reusable-workflows)

## Using Composite Actions

Composite Actions are Github Actions that combine multiple steps into one, often with
their own internal files, configurations, or scripts. They can also define their own
inputs and outputs. Unlike Reusable Workflows, Composite Actions can be run as a single
step of a larger Workflow in a repository. This makes them best suited for common
sub-tasks, such as setting up a Python environment or configuring a tool.

The Composite Actions available in this repository are stored in the `act/` directory. To
use one of these actions in another repository, a snippet like the below can be added to
the Github Actions workflow file, replacing `<action>` with the action subdirectory under
`act/`:

```yaml
jobs:
  myRepoJob:
    name: Example
    runs-on: ubuntu-latest
    steps:
    - name: Perform an Action
      uses: freedomofpress/actionslib/act/<action>@main
```

If the Composite Action specifies any inputs you can specify them using the `with`
keyword. Any outputs specified by the action can also be referenced just like any other
output from a normal action step:

```yaml
jobs:
  myRepoJob:
    name: Example
    runs-on: ubuntu-latest
    steps:
    - name: Check if Gondor Needs Help
      id: check-gondor-needs-help
      run: >-
        echo "assist-gondor=$(curl https://isgondorintrouble.com/?format=json | jq '.status')"
        >> $GITHUB_OUTPUT

    - name: Light the Beacons
      id: light-the-beacons
      if: ${{ steps.check-gondor-needs-help.outputs.assist-gondor }}
      uses: freedomofpress/actionslib/act/beacons-of-gondor@main
      with:
        beacon-state: true
        notify: theodin,aragorn,gandalf

    - name: Log the Beacons
      run: echo "Successfully lit ${{ steps.light-the-beacons.outputs.number-of-beacons }} beacons"
```

See the documentation for each specific Composite Action to see what inputs and outputs
they support.

- [Github Docs: Creating a Composite Action](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action)
- [Github Docs: Workflow Syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [Github Docs: Metadata Syntax](https://docs.github.com/en/actions/sharing-automations/creating-actions/metadata-syntax-for-github-actions#runs)
- [Available Composite Actions](#available-composite-actions)

## Available Reusable Workflows

Index of available Reusable Workflows in this repository.

| Name           | Description                                                                                                       | Docs                                          |
| -------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `lint-actions` | Use [Zizmor](https://woodruffw.github.io/zizmor/) to run static analysis checks on Github Actions workflow files. | [:link:](.github/workflows/lint-actions.yaml) |

## Available Composite Actions

Index of available Composite Actions in the repository.

| Name             | Description                                                     | Docs                          |
| ---------------- | --------------------------------------------------------------- | ----------------------------- |
| `example-action` | A nonexistent action to show what documentation will look like. | [:link:](act/example/action/) |

## Developing

System requirements:

- Python >=3.11
- [Poetry >=1.8, \<2.0](https://python-poetry.org/docs/#installation)

Helpful tools:

- `make`
- [`act`](https://nektosact.com/installation/index.html)

After installing Python and Poetry, run `make dev` to setup the local development
environment.

### Creating new Reusable Workflows

Workflows must always be located under `.github/workflows/`. This is a hardcoded
restriction of the Github Actions platform and cannot be changed. So, all Reusable
Workflows must also be stored there so that other repositories can make use of them. By
convention, workflows that are _not_ intended for reuse outside of this repository must be
prefixed with a '`_`' to differentiate them.

> [!IMPORTANT]
> There are some
> [significant limitations](https://docs.github.com/en/actions/sharing-automations/reusing-workflows#limitations)
> placed on Reusable Workflows.

Some resources to help with writing new workflows:

- [Github Docs: Reusing Workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows)
- [Github Docs: Workflow Syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [Github Docs: Accessing Context](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/accessing-contextual-information-about-workflow-runs#github-context)
- [Github Docs: Evaluating Expressions](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/evaluate-expressions-in-workflows-and-actions#literals)

### Creating new Composite Actions

By convention Composite Actions are located in a namespace directory under `act/`. Any
additional scripts, files, or resources used by a given action should be underneath it's
namespace directory there.

Some important notes:

- When writing a Composite Action it's important to be aware of the current working
  directory. By default, a Composite Action runs with the CWD of the calling workflow in
  the calling repository and _not_ the actions directory. To access resources in the
  action's directory use the `${{ github.actions_path }}` context parameter.

- Inputs and outputs of Composite Actions are passed internally from the caller to the
  action (and back again) using environment variables. This means all inputs/outputs will
  arrive at their destination as strings rather than YAML-native data types.

Some resources to help with writing new actions:

- [Github Docs: Creating a Composite Action](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action)
- [Github Docs: Accessing Context](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/accessing-contextual-information-about-workflow-runs#github-context)
- [Github Docs: Evaluating Expressions](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/evaluate-expressions-in-workflows-and-actions#literals)
- [Github Docs: Metadata Syntax](https://docs.github.com/en/actions/sharing-automations/creating-actions/metadata-syntax-for-github-actions#runs)

## License

The contents of this repository are licensed under the terms of the
[GNU Public License v3](LICENSE.txt).
