# freedomofpress/actionslib/act/signed-commit

This action allows changes to a single file to be committed to a repository with a GPG
signed commit using the Github API. This method of creating a commit is much simpler than
setting up a GPG key as a secret for every repository but has some substantial drawbacks:

- :warning: This action can only commit changes to a single file at a time. If changes to
  multiple files must be committed then they must be done in separate commits using
  separate invocations of this action.
- :warning: The branch that the commit is being added to must exist before this action is
  created. Branches will not be created automatically.
- :warning: While the commit is created in the upstream, it will _not_ be reflected in the
  local clone of the repository.
- :warning: Because this uses the Github REST API rather than the git interface, behavior
  may become unstable with large files (users have reported problems with files >50MB).
  Your milage may vary.
- :warning: This action only works on _changes_ to a file, not the addition of a new file.

See [the `action.yml` file](action.yml) for details on this action's inputs and outputs.

## Example Usage

Make a change to a file and commit the changes to a new branch:

```yaml
steps:
- name: Checkout
  uses: actions/checkout@v4

- name: Create a new branch and make That change
  run: |
    git checkout -B that-new-branch
    git push --set-upstream origin that-new-branch

    sed -i 's/This/That' README.md

- name: Commit That change
  uses: freedomofpress/actionslib/act/signed-commit@main
  with:
    file: README.md
    branch: that-new-branch
    message: |
      This is a cool new commit that will fix all the problems

      For more info on this change see the docs here: https://xkcd.com/1597/
    github-token: ${{ secrets.GITHUB_TOKEN }}
```
